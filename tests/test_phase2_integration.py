from __future__ import annotations

import os
import json
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover - live dependency is optional locally
    psycopg = None

from control_kernel.domain import ReasonCode, TaskState
from control_kernel.errors import InvalidTransition, PolicyDenied, StaleLease
from control_kernel.kernel import PostgresControlPlane
from control_kernel.phase2 import (
    AuthoritativeCIFailure,
    BaseDriftDetected,
    IndependentReviewer,
    TwoWorkerScheduler,
    deterministic_branch,
    detect_hotspot_conflict,
)
from control_kernel.postgres import PostgresConnection
from control_kernel.runtime import RuntimePin
from control_kernel.worker import AppServerWorkerSession, SessionBinding


@unittest.skipIf(psycopg is None, "psycopg is required for Phase 2 live integration tests")
class Phase2PostgresIntegrationTests(unittest.TestCase):
    dsn = "host=/tmp port=5432 dbname=aicc_phase1 user=mengyaocong"

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="aicc-phase2-pilot-"))
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self._git("init", "-b", "main")
        self._git("config", "user.name", "Phase 2 Pilot")
        self._git("config", "user.email", "phase2-pilot@example.invalid")
        (self.repo / "README.md").write_text("Phase 2 disposable pilot\n", encoding="utf-8")
        self._git("add", "README.md")
        self._git("commit", "-m", "pilot: seed disposable repository")
        self.base_sha = self._git("rev-parse", "HEAD")
        self.database = PostgresConnection(self.dsn)
        self.control = PostgresControlPlane(self.database)
        self.scheduler = TwoWorkerScheduler(
            database=self.database,
            repository=self.repo,
            worktree_root=self.root / "worktrees",
            runtime_root=self.root / "runtime",
            runtime_pin=RuntimePin.from_json(Path("runtime/codex-app-server-pin.json")),
            project_id="phase2-disposable-pilot",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_two_real_worker_processes_overlap_and_are_isolated(self) -> None:
        task_a = self._ready_task("parallel-a")
        task_b = self._ready_task("parallel-b")
        assignment_a = self.scheduler.claim(task_id=task_a, worker_slot="worker_slot_1", worker_id="worker-a")
        assignment_b = self.scheduler.claim(task_id=task_b, worker_slot="worker_slot_2", worker_id="worker-b")
        with self.assertRaises(InvalidTransition):
            self.scheduler.claim(task_id=task_a, worker_slot="worker_slot_1", worker_id="worker-a-duplicate")
        worker_session = AppServerWorkerSession(
            binding=SessionBinding(task_id=task_a, attempt_id=assignment_a.attempt_id, lease_epoch=assignment_a.lease_epoch),
            worktree=assignment_a.worktree,
            workspace_parent=assignment_a.worktree.parent,
            runtime_pin=self.scheduler.runtime_pin,
        )
        with self.assertRaises(PolicyDenied):
            worker_session.authorize_write(assignment_b.worktree / "cross-task.txt")
        with self.assertRaises(PolicyDenied):
            worker_session.authorize_write(assignment_a.worktree / ".github/workflows/blocked.yml")
        command_a = self._worker_command("worker_a.txt", "A")
        command_b = self._worker_command("worker_b.txt", "B")
        results: dict[str, object] = {}

        def run(name: str, assignment: object, command: list[str]) -> None:
            results[name] = self.scheduler.run_command(assignment, command)

        threads = [
            threading.Thread(target=run, args=("a", assignment_a, command_a)),
            threading.Thread(target=run, args=("b", assignment_b, command_b)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        run_a = results["a"]
        run_b = results["b"]
        self.assertEqual(run_a.exit_code, 0)
        self.assertEqual(run_b.exit_code, 0)
        self.assertLess(max(run_a.overlap_start_ns, run_b.overlap_start_ns), min(run_a.overlap_end_ns, run_b.overlap_end_ns))
        self.assertNotEqual(run_a.assignment.worktree, run_b.assignment.worktree)
        self.assertTrue((run_a.assignment.worktree / "worker_a.txt").is_file())
        self.assertTrue((run_b.assignment.worktree / "worker_b.txt").is_file())
        self.assertFalse((run_a.assignment.worktree / "worker_b.txt").exists())
        self.assertFalse((run_b.assignment.worktree / "worker_a.txt").exists())
        self.assertNotEqual(run_a.commit_sha, run_b.commit_sha)
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*), count(DISTINCT worker_slot) FROM control_kernel.phase2_worker_runs WHERE task_id IN (%s, %s) AND status = 'SUCCEEDED'", (task_a, task_b))
                self.assertEqual(cursor.fetchone(), (2, 2))
        print("PHASE2_EVIDENCE_PARALLEL " + json.dumps({
            "tasks": [task_a, task_b],
            "workers": [
                {"slot": run_a.assignment.worker_slot, "worker_id": run_a.assignment.worker_id, "task_id": run_a.assignment.task_id, "attempt_id": run_a.assignment.attempt_id, "lease_epoch": run_a.assignment.lease_epoch, "branch": run_a.assignment.branch, "worktree": str(run_a.assignment.worktree), "base_sha": run_a.assignment.base_sha, "commit_sha": run_a.commit_sha, "started_at": run_a.started_at.isoformat(), "ended_at": run_a.ended_at.isoformat()},
                {"slot": run_b.assignment.worker_slot, "worker_id": run_b.assignment.worker_id, "task_id": run_b.assignment.task_id, "attempt_id": run_b.assignment.attempt_id, "lease_epoch": run_b.assignment.lease_epoch, "branch": run_b.assignment.branch, "worktree": str(run_b.assignment.worktree), "base_sha": run_b.assignment.base_sha, "commit_sha": run_b.commit_sha, "started_at": run_b.started_at.isoformat(), "ended_at": run_b.ended_at.isoformat()},
            ],
            "overlap": True,
            "max_concurrency": 2,
        }, sort_keys=True))

    def test_review_reject_rework_fresh_lease_and_controlled_integration(self) -> None:
        task_id = self._ready_task("review-loop")
        first = self.scheduler.claim(task_id=task_id, worker_slot="worker_slot_1", worker_id="worker-first")
        first_run = self.scheduler.run_command(first, self._worker_command("first.txt", "first"))
        verification = self.scheduler.record_authoritative_ci(
            assignment=first,
            repository="phase2-disposable",
            branch=first.branch,
            commit_sha=first_run.commit_sha,
            pull_request_number=1,
            run_id="fixture-authoritative-run-1",
            check_name="authoritative-ci",
            conclusion="success",
            runner_environment="github-hosted",
            artifact_digest="sha256:fixture-1",
        )
        reviewer = IndependentReviewer()
        rejected = reviewer.review(
            worker_id=first.worker_id,
            machine_evidence={"authoritative_ci_conclusion": "success", "run_id": verification.run_id},
            frozen_acceptance={"checks": ["authoritative-ci"]},
            diff_bytes=b"fixture-rejected-diff",
            forced_decision="REJECT",
        )
        self.scheduler.record_review(
            assignment=first,
            verification=verification,
            decision=rejected,
            machine_evidence={"authoritative_ci_conclusion": "success", "run_id": verification.run_id},
        )
        snapshot = self._snapshot(task_id)
        self.assertEqual(snapshot["state"], "READY")
        self.assertEqual((snapshot["current_attempt_id"], snapshot["lease_epoch"]), (2, 2))
        with self.assertRaises(StaleLease):
            self.control.transition(
                task_id=task_id,
                attempt_id=first.attempt_id,
                lease_epoch=first.lease_epoch,
                expected_state_version=4,
                target=TaskState.VERIFYING,
                reason_code=ReasonCode.VERIFICATION_PENDING,
                idempotency_key="stale-after-review-reject",
            )
        second = self.scheduler.claim(task_id=task_id, worker_slot="worker_slot_2", worker_id="worker-second")
        self.assertEqual((second.attempt_id, second.lease_epoch), (2, 3))
        second_run = self.scheduler.run_command(second, self._worker_command("second.txt", "second"))
        second_verification = self.scheduler.record_authoritative_ci(
            assignment=second,
            repository="phase2-disposable",
            branch=second.branch,
            commit_sha=second_run.commit_sha,
            pull_request_number=2,
            run_id="fixture-authoritative-run-2",
            check_name="authoritative-ci",
            conclusion="success",
            runner_environment="github-hosted",
            artifact_digest="sha256:fixture-2",
        )
        accepted = reviewer.review(
            worker_id=second.worker_id,
            machine_evidence={"authoritative_ci_conclusion": "success", "run_id": second_verification.run_id},
            frozen_acceptance={"checks": ["authoritative-ci"]},
            diff_bytes=b"fixture-accepted-diff",
            forced_decision="ACCEPT",
        )
        self.scheduler.record_review(
            assignment=second,
            verification=second_verification,
            decision=accepted,
            machine_evidence={"authoritative_ci_conclusion": "success", "run_id": second_verification.run_id},
        )
        integration = self.scheduler.integrate_accepted(
            assignment=second,
            source_commit_sha=second_run.commit_sha,
            verified_commit_sha=second_run.commit_sha,
            integration_root=self.root / "integration-worktree",
        )
        self.assertEqual(self._snapshot(task_id)["state"], "CLOSED")
        self.assertEqual(integration.integration_branch, "phase2/integration")
        self.assertEqual(integration.integration_commit_sha, self._git("rev-parse", integration.integration_branch))
        print("PHASE2_EVIDENCE_REWORK " + json.dumps({
            "task_id": task_id,
            "rejected_attempt": first.attempt_id,
            "rejected_lease_epoch": first.lease_epoch,
            "rejected_worker_commit": first_run.commit_sha,
            "rejected_ci_run_id": verification.run_id,
            "rejected_reviewer_decision": rejected.decision,
            "fresh_attempt": second.attempt_id,
            "fresh_lease_epoch": second.lease_epoch,
            "fresh_worker_commit": second_run.commit_sha,
            "fresh_ci_run_id": second_verification.run_id,
            "fresh_reviewer_decision": accepted.decision,
            "integration_branch": integration.integration_branch,
            "integration_commit_sha": integration.integration_commit_sha,
        }, sort_keys=True))

    def test_human_gate_conflict_base_drift_and_expired_recovery(self) -> None:
        task_id = self._ready_task("human-and-recovery")
        assignment = self.scheduler.claim(task_id=task_id, worker_slot="worker_slot_1", worker_id="worker-crash", lease_seconds=1)
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"], cwd=assignment.worktree, start_new_session=True)
        time.sleep(1.2)
        recovery = self.scheduler.recover_expired(assignment)
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
        self.assertEqual((recovery.next_attempt_id, recovery.next_lease_epoch), (2, 2))
        self.assertIsNotNone(recovery.quarantine_path)
        self.assertEqual(self._snapshot(task_id)["state"], "READY")

        drift_task = self._ready_task("base-drift")
        drift_assignment = self.scheduler.claim(task_id=drift_task, worker_slot="worker_slot_2", worker_id="worker-drift")
        self._git("switch", "main")
        (self.repo / "base-change.txt").write_text("base moved\n", encoding="utf-8")
        self._git("add", "base-change.txt")
        self._git("commit", "-m", "pilot: move integration base")
        current_base = self._git("rev-parse", "HEAD")
        with self.assertRaises(BaseDriftDetected):
            self.scheduler.integrate_accepted(
                assignment=drift_assignment,
                source_commit_sha=current_base,
                verified_commit_sha=current_base,
                integration_root=self.root / "drift-integration",
            )
        self.assertEqual(self._snapshot(drift_task)["state"], "BLOCKED")

        human_task = self._ready_task("human-gate")
        human_assignment = self.scheduler.claim(task_id=human_task, worker_slot="worker_slot_1", worker_id="worker-human-gated")
        human_run = self.scheduler.run_command(human_assignment, self._worker_command("human.txt", "human"))
        human_verification = self.scheduler.record_authoritative_ci(
            assignment=human_assignment,
            repository="phase2-disposable",
            branch=human_assignment.branch,
            commit_sha=human_run.commit_sha,
            pull_request_number=3,
            run_id="fixture-authoritative-run-human",
            check_name="authoritative-ci",
            conclusion="success",
            runner_environment="github-hosted",
            artifact_digest="sha256:fixture-human",
        )
        human_reviewer_decision = IndependentReviewer().review(
            worker_id=human_assignment.worker_id,
            machine_evidence={"authoritative_ci_conclusion": "success", "run_id": human_verification.run_id},
            frozen_acceptance={"checks": ["authoritative-ci"]},
            diff_bytes=b"fixture-human-gate",
            forced_decision="HUMAN_REQUIRED",
        )
        self.scheduler.record_review(
            assignment=human_assignment,
            verification=human_verification,
            decision=human_reviewer_decision,
            machine_evidence={"authoritative_ci_conclusion": "success", "run_id": human_verification.run_id},
        )
        human_snapshot = self._snapshot(human_task)
        self.assertEqual(human_snapshot["state"], "AWAITING_HUMAN")
        with self.assertRaises(PolicyDenied):
            self.control.transition(
                task_id=human_task,
                attempt_id=human_assignment.attempt_id,
                lease_epoch=human_assignment.lease_epoch,
                expected_state_version=human_snapshot["state_version"],
                target=TaskState.INTEGRATING,
                reason_code=ReasonCode.NONE,
                idempotency_key="phase2-human-bypass",
            )
        self.control.transition(
            task_id=human_task,
            attempt_id=human_assignment.attempt_id,
            lease_epoch=human_assignment.lease_epoch,
            expected_state_version=human_snapshot["state_version"],
            target=TaskState.INTEGRATING,
            reason_code=ReasonCode.NONE,
            idempotency_key="phase2-human-approval",
            actor_role="human",
            approval_id="human-decision-fixture-1",
        )
        self.assertEqual(self._snapshot(human_task)["state"], "INTEGRATING")
        print("PHASE2_EVIDENCE_RECOVERY_GATE " + json.dumps({
            "crashed_task_id": task_id,
            "expired_lease_epoch": assignment.lease_epoch,
            "recovered_attempt_id": recovery.next_attempt_id,
            "recovered_lease_epoch": recovery.next_lease_epoch,
            "quarantine_path": str(recovery.quarantine_path),
            "base_drift_task_id": drift_task,
            "base_drift_state": self._snapshot(drift_task)["state"],
            "base_drift_current_base_sha": current_base,
            "human_gate_task_id": human_task,
            "human_gate_state_after_reviewer": "AWAITING_HUMAN",
            "human_gate_state_after_explicit_approval": self._snapshot(human_task)["state"],
        }, sort_keys=True))

    def test_real_hotspot_pilot_detects_same_changed_path_without_overwrite(self) -> None:
        task_a = self._ready_task("hotspot-a")
        task_b = self._ready_task("hotspot-b")
        assignment_a = self.scheduler.claim(task_id=task_a, worker_slot="worker_slot_1", worker_id="worker-hotspot-a")
        assignment_b = self.scheduler.claim(task_id=task_b, worker_slot="worker_slot_2", worker_id="worker-hotspot-b")
        results: list[object] = []

        def run(assignment: object, value: str) -> None:
            results.append(self.scheduler.run_command(assignment, self._worker_command("hotspot.txt", value)))

        threads = [
            threading.Thread(target=run, args=(assignment_a, "A")),
            threading.Thread(target=run, args=(assignment_b, "B")),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertEqual(len(results), 2)
        paths = []
        for result in results:
            changed = self._git_in(result.assignment.worktree, "diff", f"{result.assignment.base_sha}..{result.commit_sha}", "--name-only")
            paths.append(changed.splitlines())
        conflict = detect_hotspot_conflict(left_paths=paths[0], right_paths=paths[1])
        self.assertTrue(conflict["conflict"])
        self.assertEqual(conflict["reason_code"], "GIT_CONFLICT")
        self.assertEqual(conflict["action"], "BLOCK_OR_SERIALIZE")
        self.assertEqual(self._git("rev-parse", "HEAD"), self.base_sha)
        print("PHASE2_EVIDENCE_HOTSPOT " + json.dumps({
            "tasks": [task_a, task_b],
            "commits": [result.commit_sha for result in results],
            "changed_paths": paths,
            "reason_code": conflict["reason_code"],
            "action": conflict["action"],
            "protected_main_sha_unchanged": True,
        }, sort_keys=True))

    def test_failed_authoritative_ci_is_classified_and_blocks_review(self) -> None:
        task_id = self._ready_task("ci-failure")
        assignment = self.scheduler.claim(task_id=task_id, worker_slot="worker_slot_1", worker_id="worker-ci-failure")
        run = self.scheduler.run_command(assignment, self._worker_command("ci-failure.txt", "ci-failure"))
        verification = self.scheduler.record_authoritative_ci(
            assignment=assignment,
            repository="phase2-disposable",
            branch=assignment.branch,
            commit_sha=run.commit_sha,
            pull_request_number=4,
            run_id="fixture-authoritative-run-failure",
            check_name="authoritative-ci",
            conclusion="failure",
            runner_environment="github-hosted",
            artifact_digest="sha256:fixture-failure",
            job_name="lint",
            output="lint failure",
        )
        self.assertEqual(verification.failure_class, "LINT_FAILURE")
        self.assertEqual(self._snapshot(task_id)["state"], "READY")
        with self.assertRaises(AuthoritativeCIFailure):
            self.scheduler.record_review(
                assignment=assignment,
                verification=verification,
                decision=IndependentReviewer().review(
                    worker_id=assignment.worker_id,
                    machine_evidence={"authoritative_ci_conclusion": "failure"},
                    frozen_acceptance={"checks": ["authoritative-ci"]},
                    diff_bytes=b"failed-ci",
                    forced_decision="ACCEPT",
                ),
                machine_evidence={"authoritative_ci_conclusion": "failure"},
            )
        print("PHASE2_EVIDENCE_CI_FAILURE " + json.dumps({
            "task_id": task_id,
            "commit_sha": run.commit_sha,
            "run_id": verification.run_id,
            "check_name": verification.check_name,
            "conclusion": verification.conclusion,
            "failure_class": verification.failure_class,
            "state_after_failure": self._snapshot(task_id)["state"],
            "review_blocked": True,
        }, sort_keys=True))

    def _ready_task(self, suffix: str) -> str:
        task_id = f"phase2-{suffix}-{int(time.time_ns())}"
        self.control.create_task(
            project_id="phase2-disposable-pilot",
            task_id=task_id,
            acceptance_contract={"checks": ["authoritative-ci"]},
            branch=deterministic_branch(task_id, 1),
        )
        self.control.transition(
            task_id=task_id,
            attempt_id=0,
            lease_epoch=0,
            expected_state_version=0,
            target=TaskState.READY,
            reason_code=ReasonCode.AWAITING_ASSIGNMENT,
            idempotency_key=f"ready-{task_id}",
        )
        return task_id

    def _worker_command(self, filename: str, value: str) -> list[str]:
        script = (
            "from pathlib import Path; import os, subprocess, time; "
            f"Path('{filename}').write_text('{value}\\n'); time.sleep(0.7); "
            f"subprocess.run(['git','add','{filename}'], check=True); "
            f"subprocess.run(['git','commit','-m','pilot: {value}\\n\\nAICC-Task: '+os.environ['AICC_TASK_ID']+'\\nAICC-Worker-Slot: '+os.environ['AICC_WORKER_SLOT']+'\\nAICC-Attempt: '+os.environ['AICC_ATTEMPT_ID']+'\\nAICC-Lease-Epoch: '+os.environ['AICC_LEASE_EPOCH']], check=True)"
        )
        return [sys.executable, "-c", script]

    def _git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()

    def _git_in(self, worktree: Path, *args: str) -> str:
        return subprocess.run(["git", "-C", str(worktree), *args], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()

    def _snapshot(self, task_id: str) -> dict[str, object]:
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT state, current_attempt_id, lease_epoch, state_version FROM control_kernel.tasks WHERE task_id = %s", (task_id,))
                state, attempt, epoch, version = cursor.fetchone()
                return {"state": state, "current_attempt_id": int(attempt), "lease_epoch": int(epoch), "state_version": int(version)}


if __name__ == "__main__":
    unittest.main()
