"""Minimal two-Worker Phase 2 pilot primitives.

This module deliberately stops at a bounded pilot. It owns no UI, no public
API, no protected-main merge path, and no dynamic worker scaling. PostgreSQL
remains authoritative for scheduler metadata and task state; Git remains the
authority for worktree contents.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import signal
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .domain import ReasonCode, TaskState
from .errors import PolicyDenied, StaleLease, UnsupportedRuntime
from .kernel import Lease, PostgresControlPlane
from .postgres import PostgresConnection
from .runtime import EXPECTED_CODEX_VERSION, RuntimePin
from .verification import VerificationHandoff, build_verification_handoff


WORKER_SLOTS = ("worker_slot_1", "worker_slot_2")
MAX_WORKERS = 2
CI_FAILURE_CLASSES = frozenset(
    {
        "TEST_FAILURE",
        "BUILD_FAILURE",
        "LINT_FAILURE",
        "POLICY_FAILURE",
        "INFRA_FAILURE",
        "TIMEOUT",
        "CANCELLED",
    }
)
CI_SUCCESS = "success"


class Phase2PilotError(RuntimeError):
    """Base error for deterministic Phase 2 pilot failures."""


class SlotBusy(Phase2PilotError):
    pass


class BaseDriftDetected(Phase2PilotError):
    pass


class AuthoritativeCIFailure(Phase2PilotError):
    pass


class ReviewerProtocolError(Phase2PilotError):
    pass


def detect_hotspot_conflict(*, left_paths: Iterable[str], right_paths: Iterable[str]) -> dict[str, Any]:
    """Detect only explicit path-key overlap; semantic lock inference is forbidden."""
    left = {Path(path).as_posix().lstrip("./") for path in left_paths}
    right = {Path(path).as_posix().lstrip("./") for path in right_paths}
    overlap = sorted(left & right)
    return {
        "conflict": bool(overlap),
        "hotspot_paths": overlap,
        "reason_code": "GIT_CONFLICT" if overlap else None,
        "action": "BLOCK_OR_SERIALIZE" if overlap else "CONTINUE",
    }


@dataclass(frozen=True)
class WorkerAssignment:
    project_id: str
    task_id: str
    attempt_id: int
    lease_epoch: int
    worker_slot: str
    worker_id: str
    branch: str
    worktree: Path
    runtime_dir: Path
    base_sha: str
    lease: Lease


@dataclass(frozen=True)
class WorkerRunEvidence:
    run_id: str
    assignment: WorkerAssignment
    started_at: datetime
    ended_at: datetime
    exit_code: int
    commit_sha: str | None
    overlap_start_ns: int
    overlap_end_ns: int
    handoff: VerificationHandoff | None


@dataclass(frozen=True)
class VerificationRecord:
    verification_id: str
    task_id: str
    attempt_id: int
    lease_epoch: int
    repository: str
    branch: str
    commit_sha: str
    pull_request_number: int | None
    run_id: str
    check_name: str
    conclusion: str
    failure_class: str | None
    runner_environment: str
    artifact_digest: str | None


@dataclass(frozen=True)
class ReviewDecision:
    decision: str
    reason_codes: tuple[str, ...]
    reviewer_id: str
    reviewer_model: str
    reviewer_context_id: str
    input_digest: str
    reviewed_diff_hash: str


@dataclass(frozen=True)
class IntegrationEvidence:
    integration_id: str
    task_id: str
    integration_branch: str
    base_sha: str
    source_task_commit_sha: str
    verified_commit_sha: str
    integration_commit_sha: str


@dataclass(frozen=True)
class RecoveryEvidence:
    task_id: str
    attempt_id: int
    expired_lease_epoch: int
    next_attempt_id: int
    next_lease_epoch: int
    worktree: Path
    quarantine_path: Path | None


@dataclass(frozen=True)
class AppServerTurnEvidence:
    runtime_version: str
    thread_id: str
    turn_id: str | None
    started_at: float
    ended_at: float
    usage_event_count: int
    raw_usage_events: tuple[Mapping[str, Any], ...]


class AppServerWorkerClient:
    """Fail-closed Codex App Server v2 client for one bound Worker session."""

    def __init__(self, *, runtime_pin: RuntimePin, worktree: Path, binding: tuple[str, int, int], runtime_dir: Path):
        self.runtime_pin = runtime_pin
        self.worktree = worktree.resolve(strict=True)
        self.binding = binding
        self.runtime_dir = runtime_dir.resolve(strict=False)
        self.process: subprocess.Popen[str] | None = None

    def run_turn(self, prompt: str, *, timeout_seconds: float = 120.0, model: str | None = None) -> AppServerTurnEvidence:
        if not prompt:
            raise ValueError("prompt is required")
        executable = self.runtime_pin.executable_path
        version_output = subprocess.run([str(executable), "--version"], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
        runtime_version = version_output.strip().splitlines()[-1].strip()
        if runtime_version.startswith("codex-cli "):
            runtime_version = runtime_version.removeprefix("codex-cli ")
        self.runtime_pin.validate(runtime_version, executable)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        process = subprocess.Popen(
            [str(executable), "app-server", "--stdio"],
            cwd=self.worktree,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
            bufsize=1,
        )
        self.process = process
        started = time.time()
        usage_events: list[Mapping[str, Any]] = []
        try:
            self._send(process, {"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "aicc-phase2-worker", "version": "0.1.0"}}})
            self._send(process, {"method": "initialized", "params": {}})
            initialize = self._read_response(process, request_id=1, deadline=started + timeout_seconds)
            if "error" in initialize:
                raise Phase2PilotError(f"App Server initialize failed: {initialize['error']}")
            start_params: dict[str, Any] = {
                "cwd": str(self.worktree),
                "ephemeral": True,
                "sandbox": "workspace-write",
                "approvalPolicy": "never",
                "runtimeWorkspaceRoots": [str(self.worktree)],
            }
            if model is not None:
                start_params["model"] = model
            self._send(process, {"id": 2, "method": "thread/start", "params": start_params})
            thread_response = self._read_response(process, request_id=2, deadline=started + timeout_seconds)
            if "error" in thread_response:
                raise Phase2PilotError(f"App Server thread/start failed: {thread_response['error']}")
            thread = thread_response.get("result", {}).get("thread", {})
            thread_id = thread.get("id")
            if not thread_id:
                raise Phase2PilotError("App Server thread/start returned no thread id")
            turn_params: dict[str, Any] = {
                "threadId": thread_id,
                "input": [{"type": "text", "text": prompt}],
            }
            self._send(process, {"id": 3, "method": "turn/start", "params": turn_params})
            turn_id: str | None = None
            while time.time() < started + timeout_seconds:
                event = self._read_one(process, deadline=started + timeout_seconds)
                if event is None:
                    continue
                if event.get("method") == "thread/tokenUsage/updated":
                    params = event.get("params", {})
                    if isinstance(params, Mapping):
                        usage_events.append(dict(params))
                if event.get("id") == 3 and "error" in event:
                    raise Phase2PilotError(f"App Server turn/start failed: {event['error']}")
                if event.get("id") == 3 and "result" in event:
                    turn_id = event.get("result", {}).get("turn", {}).get("id")
                if event.get("method") == "turn/completed":
                    turn_id = turn_id or event.get("params", {}).get("turn", {}).get("id")
                    return AppServerTurnEvidence(runtime_version, thread_id, turn_id, started, time.time(), len(usage_events), tuple(usage_events))
            raise Phase2PilotError("App Server turn exceeded bounded timeout")
        finally:
            self._terminate()

    @staticmethod
    def _send(process: subprocess.Popen[str], message: Mapping[str, Any]) -> None:
        if process.stdin is None:
            raise Phase2PilotError("App Server stdin is unavailable")
        process.stdin.write(_canonical_json(message) + "\n")
        process.stdin.flush()

    def _read_response(self, process: subprocess.Popen[str], *, request_id: int, deadline: float) -> Mapping[str, Any]:
        while time.time() < deadline:
            event = self._read_one(process, deadline=deadline)
            if event is not None and event.get("id") == request_id:
                return event
        raise Phase2PilotError("App Server response exceeded bounded timeout")

    @staticmethod
    def _read_one(process: subprocess.Popen[str], *, deadline: float) -> Mapping[str, Any] | None:
        if process.stdout is None:
            raise Phase2PilotError("App Server stdout is unavailable")
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            events = selector.select(max(0.0, min(1.0, deadline - time.time())))
            if not events:
                return None
            line = process.stdout.readline()
        finally:
            selector.close()
        if not line:
            if process.poll() is not None:
                raise Phase2PilotError(f"App Server exited before completing request: {process.returncode}")
            return None
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Phase2PilotError("App Server emitted invalid JSONL") from exc
        return value if isinstance(value, Mapping) else None

    def _terminate(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
            self.process.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            if self.process.poll() is None:
                self.process.kill()


def deterministic_branch(task_id: str, attempt_id: int) -> str:
    _validate_identifier(task_id, "task_id")
    if attempt_id < 1:
        raise ValueError("attempt_id must be positive")
    return f"task/{task_id}/attempt-{attempt_id}"


def deterministic_worktree(root: Path, worker_slot: str, task_id: str, attempt_id: int) -> Path:
    _validate_slot(worker_slot)
    branch = deterministic_branch(task_id, attempt_id)
    return root.resolve(strict=False) / worker_slot / task_id / f"attempt-{attempt_id}"


def deterministic_runtime_dir(root: Path, worker_slot: str, task_id: str, attempt_id: int) -> Path:
    _validate_slot(worker_slot)
    _validate_identifier(task_id, "task_id")
    return root.resolve(strict=False) / worker_slot / task_id / f"attempt-{attempt_id}"


def classify_ci_failure(*, conclusion: str, job_name: str = "", output: str = "") -> str | None:
    """Classify only from deterministic CI metadata, never from an LLM."""

    if conclusion.lower() in {"success", "neutral", "skipped"}:
        return None
    haystack = f"{job_name}\n{output}".lower()
    if "cancel" in haystack:
        return "CANCELLED"
    if "timeout" in haystack or "timed out" in haystack:
        return "TIMEOUT"
    if "policy" in haystack or "protected" in haystack:
        return "POLICY_FAILURE"
    if "lint" in haystack or "ruff" in haystack or "eslint" in haystack:
        return "LINT_FAILURE"
    if "build" in haystack or "compile" in haystack:
        return "BUILD_FAILURE"
    if "infra" in haystack or "runner" in haystack or "network" in haystack:
        return "INFRA_FAILURE"
    return "TEST_FAILURE"


def detect_base_drift(*, expected_base_sha: str, current_base_sha: str) -> dict[str, Any]:
    if not expected_base_sha or not current_base_sha:
        raise ValueError("both expected and current base SHA are required")
    drifted = expected_base_sha != current_base_sha
    return {
        "drifted": drifted,
        "old_base_sha": expected_base_sha,
        "current_base_sha": current_base_sha,
        "action": "REVERIFY_OR_REBASE" if drifted else "CONTINUE",
        "reason_code": "BASE_DRIFT" if drifted else None,
    }


class WorktreeManager:
    """Create and quarantine deterministic per-task Git worktrees."""

    def __init__(self, *, repository: Path, worktree_root: Path):
        self.repository = repository.resolve(strict=True)
        self.worktree_root = worktree_root.resolve(strict=False)
        self.worktree_root.mkdir(parents=True, exist_ok=True)

    def create(self, *, branch: str, path: Path, base_sha: str) -> Path:
        path = path.resolve(strict=False)
        self._contained(path)
        if path.exists():
            raise Phase2PilotError(f"worktree path already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        _run_git(self.repository, "worktree", "add", "-b", branch, str(path), base_sha)
        return path

    def remove(self, path: Path) -> None:
        path = path.resolve(strict=False)
        self._contained(path)
        if path.exists():
            _run_git(self.repository, "worktree", "remove", "--force", str(path))

    def quarantine(self, path: Path) -> Path | None:
        path = path.resolve(strict=False)
        self._contained(path)
        if not path.exists():
            return None
        quarantine = path.with_name(f"{path.name}.quarantine-{uuid.uuid4().hex[:12]}")
        path.rename(quarantine)
        return quarantine

    def _contained(self, path: Path) -> None:
        try:
            path.relative_to(self.worktree_root)
        except ValueError as exc:
            raise PolicyDenied("worktree path is outside the configured Phase 2 root") from exc


class IndependentReviewer:
    """One fresh, structured Reviewer context.

    The default pilot implementation is deterministic and intentionally
    marked as a fixture reviewer. Production acceptance must provide the
    approved Sol runtime identity; an unapproved substitute fails closed.
    """

    def __init__(self, *, reviewer_id: str = "sol-reviewer", reviewer_model: str = "Sol", approved_model: str = "Sol"):
        self.reviewer_id = reviewer_id
        self.reviewer_model = reviewer_model
        self.approved_model = approved_model

    def review(
        self,
        *,
        worker_id: str,
        machine_evidence: Mapping[str, Any],
        frozen_acceptance: Mapping[str, Any],
        diff_bytes: bytes,
        forced_decision: str | None = None,
    ) -> ReviewDecision:
        if worker_id == self.reviewer_id:
            raise ReviewerProtocolError("Reviewer identity must differ from Worker identity")
        if self.reviewer_model != self.approved_model:
            raise UnsupportedRuntime("approved Sol Reviewer runtime is unavailable; refusing substitution")
        if not machine_evidence or not frozen_acceptance:
            raise ReviewerProtocolError("Reviewer requires machine evidence and frozen acceptance criteria")
        if "worker_natural_language" in machine_evidence or "worker_self_assessment" in machine_evidence:
            raise ReviewerProtocolError("Worker natural-language self-assessment is not Reviewer authority")
        context_id = f"review-context-{uuid.uuid4().hex}"
        input_payload = {
            "frozen_acceptance": dict(frozen_acceptance),
            "machine_evidence": dict(machine_evidence),
            "diff_sha256": hashlib.sha256(diff_bytes).hexdigest(),
        }
        input_digest = hashlib.sha256(_canonical_json(input_payload).encode()).hexdigest()
        reviewed_diff_hash = hashlib.sha256(diff_bytes).hexdigest()
        if forced_decision is not None:
            decision = forced_decision
        else:
            decision = "ACCEPT" if machine_evidence.get("authoritative_ci_conclusion") == CI_SUCCESS else "REJECT"
        if decision not in {"ACCEPT", "REJECT", "HUMAN_REQUIRED"}:
            raise ReviewerProtocolError(f"invalid Reviewer decision: {decision}")
        reasons = ("REVIEW_ACCEPTED",) if decision == "ACCEPT" else ("REVIEW_REJECTED",)
        return ReviewDecision(
            decision=decision,
            reason_codes=reasons,
            reviewer_id=self.reviewer_id,
            reviewer_model=self.reviewer_model,
            reviewer_context_id=context_id,
            input_digest=input_digest,
            reviewed_diff_hash=reviewed_diff_hash,
        )


class TwoWorkerScheduler:
    """Bounded scheduler for exactly two PostgreSQL-backed Worker slots."""

    def __init__(
        self,
        *,
        database: PostgresConnection,
        repository: Path,
        worktree_root: Path,
        runtime_root: Path,
        runtime_pin: RuntimePin,
        project_id: str,
    ):
        self.database = database
        self.control = PostgresControlPlane(database)
        self.repository = repository.resolve(strict=True)
        self.project_id = project_id
        self.worktrees = WorktreeManager(repository=self.repository, worktree_root=worktree_root)
        self.runtime_root = runtime_root.resolve(strict=False)
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.runtime_pin = runtime_pin

    def validate_dispatch(self, *, available_disk_bytes: int, required_disk_bytes: int = 1) -> None:
        if available_disk_bytes < required_disk_bytes:
            raise Phase2PilotError("insufficient disk space; task remains READY")
        self.runtime_pin.validate(EXPECTED_CODEX_VERSION)
        self._db_probe()

    def claim(self, *, task_id: str, worker_slot: str, worker_id: str, lease_seconds: int = 60) -> WorkerAssignment:
        _validate_slot(worker_slot)
        branch_base = self._git("rev-parse", "HEAD")
        lease = self.control.claim_task(task_id=task_id, worker_id=worker_id, lease_seconds=lease_seconds)
        branch = deterministic_branch(task_id, lease.attempt_id)
        worktree = deterministic_worktree(self.worktrees.worktree_root, worker_slot, task_id, lease.attempt_id)
        runtime_dir = deterministic_runtime_dir(self.runtime_root, worker_slot, task_id, lease.attempt_id)
        try:
            self._acquire_slot(worker_slot, task_id, lease, branch, worktree, runtime_dir)
            self.worktrees.create(branch=branch, path=worktree, base_sha=branch_base)
            runtime_dir.mkdir(parents=True, exist_ok=False)
            run_id = str(uuid.uuid4())
            self._insert_worker_run(
                run_id=run_id,
                assignment=(task_id, lease, worker_slot, worker_id, branch, worktree, runtime_dir, branch_base),
            )
        except Exception:
            self._release_slot(worker_slot)
            raise
        return WorkerAssignment(
            project_id=self.project_id,
            task_id=task_id,
            attempt_id=lease.attempt_id,
            lease_epoch=lease.lease_epoch,
            worker_slot=worker_slot,
            worker_id=worker_id,
            branch=branch,
            worktree=worktree,
            runtime_dir=runtime_dir,
            base_sha=branch_base,
            lease=lease,
        )

    def run_command(self, assignment: WorkerAssignment, command: Sequence[str], *, heartbeat_seconds: float = 0.25) -> WorkerRunEvidence:
        run_id = self._run_id(assignment)
        started_at = self._db_now()
        start_ns = time.monotonic_ns()
        stop_heartbeat = threading.Event()
        heartbeat_errors: list[BaseException] = []

        def heartbeat_loop() -> None:
            while not stop_heartbeat.wait(heartbeat_seconds):
                try:
                    self.control.heartbeat(assignment.lease, lease_seconds=60)
                except BaseException as exc:  # pragma: no cover - depends on crash timing
                    heartbeat_errors.append(exc)
                    return

        heartbeat = threading.Thread(target=heartbeat_loop, name=f"heartbeat-{assignment.worker_slot}", daemon=True)
        heartbeat.start()
        environment = os.environ.copy()
        environment.update(
            {
                "AICC_WORKER_SLOT": assignment.worker_slot,
                "AICC_TASK_ID": assignment.task_id,
                "AICC_ATTEMPT_ID": str(assignment.attempt_id),
                "AICC_LEASE_EPOCH": str(assignment.lease_epoch),
                "AICC_WORKTREE": str(assignment.worktree),
                "AICC_RUNTIME_DIR": str(assignment.runtime_dir),
            }
        )
        process = subprocess.Popen(
            list(command),
            cwd=assignment.worktree,
            env=environment,
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        while process.poll() is None:
            if heartbeat_errors:
                self._terminate_process_group(process)
                break
            time.sleep(0.05)
        output, _ = process.communicate()
        stop_heartbeat.set()
        heartbeat.join(timeout=2)
        ended_at = self._db_now()
        end_ns = time.monotonic_ns()
        if heartbeat_errors:
            self._recover_after_heartbeat_failure(assignment, process)
            raise StaleLease("Worker heartbeat failed; execution fenced") from heartbeat_errors[0]
        commit_sha = self._git_in_worktree(assignment.worktree, "rev-parse", "HEAD").strip() if process.returncode == 0 else None
        if process.returncode == 0:
            state_version = self._task_snapshot(assignment.task_id)["state_version"]
            handoff = build_verification_handoff(
                project_id=assignment.project_id,
                task_id=assignment.task_id,
                attempt_id=assignment.attempt_id,
                lease_epoch=assignment.lease_epoch,
                branch=assignment.branch,
                base_sha=assignment.base_sha,
                commit_sha=commit_sha,
                diff_bytes=self._git_in_worktree(assignment.worktree, "diff", f"{assignment.base_sha}..{commit_sha}", "--binary").encode(),
                acceptance_contract={"phase": "phase2-pilot"},
            )
            self.control.transition(
                task_id=assignment.task_id,
                attempt_id=assignment.attempt_id,
                lease_epoch=assignment.lease_epoch,
                expected_state_version=state_version,
                target=TaskState.VERIFYING,
                reason_code=ReasonCode.VERIFICATION_PENDING,
                idempotency_key=f"phase2-verifying-{run_id}",
            )
            status = "SUCCEEDED"
        else:
            state_version = self._task_snapshot(assignment.task_id)["state_version"]
            self.control.transition(
                task_id=assignment.task_id,
                attempt_id=assignment.attempt_id,
                lease_epoch=assignment.lease_epoch,
                expected_state_version=state_version,
                target=TaskState.READY,
                reason_code=ReasonCode.TEST_FAILURE,
                idempotency_key=f"phase2-worker-failure-{run_id}",
            )
            handoff = None
            status = "FAILED"
        self._finish_worker_run(run_id, ended_at, process.returncode, commit_sha, status)
        self._release_slot(assignment.worker_slot)
        return WorkerRunEvidence(run_id, assignment, started_at, ended_at, process.returncode, commit_sha, start_ns, end_ns, handoff)

    def record_authoritative_ci(
        self,
        *,
        assignment: WorkerAssignment,
        repository: str,
        branch: str,
        commit_sha: str,
        pull_request_number: int | None,
        run_id: str,
        check_name: str,
        conclusion: str,
        runner_environment: str,
        artifact_digest: str | None,
        job_name: str = "",
        output: str = "",
    ) -> VerificationRecord:
        if check_name != "authoritative-ci":
            raise AuthoritativeCIFailure("only authoritative-ci can advance verification")
        if runner_environment != "github-hosted":
            raise AuthoritativeCIFailure("self-hosted/local CI cannot be authoritative")
        failure_class = classify_ci_failure(conclusion=conclusion, job_name=job_name, output=output)
        if conclusion.lower() != CI_SUCCESS and failure_class not in CI_FAILURE_CLASSES:
            raise AuthoritativeCIFailure("unclassified CI failure; failing closed")
        verification_id = str(uuid.uuid4())
        evidence = {
            "repository": repository,
            "branch": branch,
            "pull_request_number": pull_request_number,
            "run_id": run_id,
            "check_name": check_name,
            "conclusion": conclusion,
            "runner_environment": runner_environment,
            "failure_class": failure_class,
        }
        with self.database.transaction() as (_, cursor):
            cursor.execute(
                """
                INSERT INTO phase2_verifications
                    (verification_id, project_id, task_id, attempt_id, lease_epoch,
                     repository, branch, commit_sha, pull_request_number, run_id,
                     check_name, conclusion, failure_class, runner_environment,
                     artifact_digest, evidence_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    verification_id,
                    assignment.project_id,
                    assignment.task_id,
                    assignment.attempt_id,
                    assignment.lease_epoch,
                    repository,
                    branch,
                    commit_sha,
                    pull_request_number,
                    run_id,
                    check_name,
                    conclusion,
                    failure_class,
                    runner_environment,
                    artifact_digest,
                    _canonical_json(evidence),
                ),
            )
        state_version = self._task_snapshot(assignment.task_id)["state_version"]
        if conclusion.lower() == CI_SUCCESS:
            self.control.transition(
                task_id=assignment.task_id,
                attempt_id=assignment.attempt_id,
                lease_epoch=assignment.lease_epoch,
                expected_state_version=state_version,
                target=TaskState.REVIEW,
                reason_code=ReasonCode.REVIEW_PENDING,
                idempotency_key=f"phase2-ci-pass-{verification_id}",
            )
        else:
            self.control.transition(
                task_id=assignment.task_id,
                attempt_id=assignment.attempt_id,
                lease_epoch=assignment.lease_epoch,
                expected_state_version=state_version,
                target=TaskState.READY,
                reason_code=ReasonCode.TEST_FAILURE,
                idempotency_key=f"phase2-ci-fail-{verification_id}",
            )
        return VerificationRecord(
            verification_id=verification_id,
            task_id=assignment.task_id,
            attempt_id=assignment.attempt_id,
            lease_epoch=assignment.lease_epoch,
            repository=repository,
            branch=branch,
            commit_sha=commit_sha,
            pull_request_number=pull_request_number,
            run_id=run_id,
            check_name=check_name,
            conclusion=conclusion,
            failure_class=failure_class,
            runner_environment=runner_environment,
            artifact_digest=artifact_digest,
        )

    def record_review(
        self,
        *,
        assignment: WorkerAssignment,
        verification: VerificationRecord,
        decision: ReviewDecision,
        machine_evidence: Mapping[str, Any],
    ) -> None:
        if decision.reviewer_id == assignment.worker_id:
            raise ReviewerProtocolError("Worker cannot review its own execution")
        if verification.conclusion.lower() != CI_SUCCESS:
            raise AuthoritativeCIFailure("failed authoritative-ci cannot reach Reviewer acceptance")
        with self.database.transaction() as (_, cursor):
            cursor.execute(
                """
                INSERT INTO phase2_reviews
                    (review_id, project_id, task_id, attempt_id, lease_epoch,
                     worker_id, reviewer_id, reviewer_model, reviewer_context_id,
                     input_digest, reviewed_diff_hash, decision, reason_codes, evidence_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                """,
                (
                    str(uuid.uuid4()),
                    assignment.project_id,
                    assignment.task_id,
                    assignment.attempt_id,
                    assignment.lease_epoch,
                    assignment.worker_id,
                    decision.reviewer_id,
                    decision.reviewer_model,
                    decision.reviewer_context_id,
                    decision.input_digest,
                    decision.reviewed_diff_hash,
                    decision.decision,
                    _canonical_json(list(decision.reason_codes)),
                    _canonical_json(dict(machine_evidence)),
                ),
            )
        state_version = self._task_snapshot(assignment.task_id)["state_version"]
        target, reason = {
            "ACCEPT": (TaskState.INTEGRATING, ReasonCode.NONE),
            "REJECT": (TaskState.READY, ReasonCode.REWORK_REQUIRED),
            "HUMAN_REQUIRED": (TaskState.AWAITING_HUMAN, ReasonCode.HUMAN_APPROVAL_REQUIRED),
        }[decision.decision]
        self.control.transition(
            task_id=assignment.task_id,
            attempt_id=assignment.attempt_id,
            lease_epoch=assignment.lease_epoch,
            expected_state_version=state_version,
            target=target,
            reason_code=reason,
            idempotency_key=f"phase2-review-{decision.reviewer_context_id}",
        )

    def integrate_accepted(
        self,
        *,
        assignment: WorkerAssignment,
        source_commit_sha: str,
        verified_commit_sha: str,
        integration_root: Path,
        integration_branch: str = "phase2/integration",
    ) -> IntegrationEvidence:
        current_base = self._git("rev-parse", "HEAD")
        drift = detect_base_drift(expected_base_sha=assignment.base_sha, current_base_sha=current_base)
        if drift["drifted"]:
            self.control.fence_lease(assignment.lease, target=TaskState.BLOCKED, reason_code=ReasonCode.BASE_DRIFT)
            self.worktrees.quarantine(assignment.worktree)
            self._release_slot(assignment.worker_slot)
            raise BaseDriftDetected(_canonical_json(drift))
        integration_path = integration_root.resolve(strict=False)
        manager = WorktreeManager(repository=self.repository, worktree_root=integration_path.parent)
        manager.create(branch=integration_branch, path=integration_path, base_sha=assignment.base_sha)
        try:
            _run_git(integration_path, "cherry-pick", source_commit_sha)
            integration_commit = _run_git(integration_path, "rev-parse", "HEAD").stdout.strip()
        except Exception:
            manager.quarantine(integration_path)
            raise
        evidence = IntegrationEvidence(
            integration_id=str(uuid.uuid4()),
            task_id=assignment.task_id,
            integration_branch=integration_branch,
            base_sha=assignment.base_sha,
            source_task_commit_sha=source_commit_sha,
            verified_commit_sha=verified_commit_sha,
            integration_commit_sha=integration_commit,
        )
        with self.database.transaction() as (_, cursor):
            cursor.execute(
                """
                INSERT INTO phase2_integrations
                    (integration_id, project_id, task_id, attempt_id, lease_epoch,
                     integration_branch, base_sha, source_task_commit_sha,
                     verified_commit_sha, reviewer_decision, integration_commit_sha)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACCEPT', %s)
                """,
                (
                    evidence.integration_id,
                    assignment.project_id,
                    assignment.task_id,
                    assignment.attempt_id,
                    assignment.lease_epoch,
                    integration_branch,
                    assignment.base_sha,
                    source_commit_sha,
                    verified_commit_sha,
                    integration_commit,
                ),
            )
        state_version = self._task_snapshot(assignment.task_id)["state_version"]
        self.control.transition(
            task_id=assignment.task_id,
            attempt_id=assignment.attempt_id,
            lease_epoch=assignment.lease_epoch,
            expected_state_version=state_version,
            target=TaskState.CLOSED,
            reason_code=ReasonCode.NONE,
            idempotency_key=f"phase2-integrated-{evidence.integration_id}",
        )
        return evidence

    def recover_expired(self, assignment: WorkerAssignment) -> RecoveryEvidence:
        if not self.control.expire_lease(assignment.lease):
            raise StaleLease("lease was not expired or no longer owns task")
        quarantine = self.worktrees.quarantine(assignment.worktree)
        snapshot = self._task_snapshot(assignment.task_id)
        self._release_slot(assignment.worker_slot)
        self._mark_worker_run_quarantined(assignment.task_id, assignment.attempt_id, assignment.lease_epoch)
        return RecoveryEvidence(
            task_id=assignment.task_id,
            attempt_id=assignment.attempt_id,
            expired_lease_epoch=assignment.lease_epoch,
            next_attempt_id=snapshot["current_attempt_id"],
            next_lease_epoch=snapshot["lease_epoch"],
            worktree=assignment.worktree,
            quarantine_path=quarantine,
        )

    def _acquire_slot(self, slot: str, task_id: str, lease: Lease, branch: str, worktree: Path, runtime_dir: Path) -> None:
        with self.database.transaction() as (_, cursor):
            cursor.execute("SELECT active_task_id FROM phase2_worker_slots WHERE slot_name = %s FOR UPDATE", (slot,))
            row = cursor.fetchone()
            if row is None:
                raise Phase2PilotError(f"unknown Worker slot: {slot}")
            if row[0] is not None:
                raise SlotBusy(f"{slot} is already active")
            cursor.execute(
                """
                UPDATE phase2_worker_slots
                   SET active_task_id = %s, attempt_id = %s, lease_epoch = %s,
                       branch = %s, worktree = %s, runtime_dir = %s,
                       acquired_at = clock_timestamp(), released_at = NULL
                 WHERE slot_name = %s
                """,
                (task_id, lease.attempt_id, lease.lease_epoch, branch, str(worktree), str(runtime_dir), slot),
            )

    def _release_slot(self, slot: str) -> None:
        with self.database.transaction() as (_, cursor):
            cursor.execute(
                """
                UPDATE phase2_worker_slots
                   SET active_task_id = NULL, attempt_id = NULL, lease_epoch = NULL,
                       branch = NULL, worktree = NULL, runtime_dir = NULL,
                       released_at = clock_timestamp()
                 WHERE slot_name = %s
                """,
                (slot,),
            )

    def _insert_worker_run(self, *, run_id: str, assignment: tuple[Any, ...]) -> None:
        task_id, lease, slot, worker_id, branch, worktree, runtime_dir, base_sha = assignment
        with self.database.transaction() as (_, cursor):
            cursor.execute(
                """
                INSERT INTO phase2_worker_runs
                    (run_id, project_id, task_id, attempt_id, lease_epoch, worker_slot,
                     worker_id, branch, worktree, runtime_dir, base_sha, started_at, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        clock_timestamp(), 'RUNNING')
                """,
                (run_id, self.project_id, task_id, lease.attempt_id, lease.lease_epoch, slot, worker_id, branch, str(worktree), str(runtime_dir), base_sha),
            )

    def _finish_worker_run(self, run_id: str, ended_at: datetime, exit_code: int, commit_sha: str | None, status: str) -> None:
        with self.database.transaction() as (_, cursor):
            cursor.execute(
                """
                UPDATE phase2_worker_runs
                   SET ended_at = %s, exit_code = %s, commit_sha = %s, status = %s
                 WHERE run_id = %s
                """,
                (ended_at, exit_code, commit_sha, status, run_id),
            )

    def _mark_worker_run_quarantined(self, task_id: str, attempt_id: int, lease_epoch: int) -> None:
        with self.database.transaction() as (_, cursor):
            cursor.execute(
                """
                UPDATE phase2_worker_runs
                   SET status = 'QUARANTINED', ended_at = clock_timestamp()
                 WHERE task_id = %s AND attempt_id = %s AND lease_epoch = %s
                   AND status = 'RUNNING'
                """,
                (task_id, attempt_id, lease_epoch),
            )

    def _recover_after_heartbeat_failure(self, assignment: WorkerAssignment, process: subprocess.Popen[str]) -> None:
        self._terminate_process_group(process)

    @staticmethod
    def _terminate_process_group(process: subprocess.Popen[str]) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    def _run_id(self, assignment: WorkerAssignment) -> str:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT run_id FROM phase2_worker_runs WHERE task_id = %s AND attempt_id = %s AND lease_epoch = %s ORDER BY started_at DESC LIMIT 1",
                    (assignment.task_id, assignment.attempt_id, assignment.lease_epoch),
                )
                row = cursor.fetchone()
                if row is None:
                    raise Phase2PilotError("worker run metadata is missing")
                return str(row[0])

    def _task_snapshot(self, task_id: str) -> dict[str, Any]:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT state, state_version, current_attempt_id, lease_epoch, branch FROM tasks WHERE task_id = %s",
                    (task_id,),
                )
                row = cursor.fetchone()
        if row is None:
            raise KeyError(task_id)
        return {
            "state": row[0],
            "state_version": int(row[1]),
            "current_attempt_id": int(row[2]),
            "lease_epoch": int(row[3]),
            "branch": row[4],
        }

    def _db_probe(self) -> None:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), clock_timestamp()")
                if cursor.fetchone()[0] != "aicc_phase1":
                    raise Phase2PilotError("Phase 2 pilot database target is not aicc_phase1")

    def _db_now(self) -> datetime:
        with self.database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT clock_timestamp()")
                return cursor.fetchone()[0]

    def _git(self, *args: str) -> str:
        return _run_git(self.repository, *args).stdout.strip()

    @staticmethod
    def _git_in_worktree(worktree: Path, *args: str) -> str:
        return _run_git(worktree, *args).stdout


def _run_git(repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
    if any(arg in {"--force", "-f"} for arg in args) and args[:2] != ("worktree", "remove"):
        raise PolicyDenied("force Git operations are not allowed in the Phase 2 pilot")
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _validate_slot(slot: str) -> None:
    if slot not in WORKER_SLOTS:
        raise ValueError(f"unsupported Worker slot: {slot}")


def _validate_identifier(value: str, name: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", value):
        raise ValueError(f"invalid {name}")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
