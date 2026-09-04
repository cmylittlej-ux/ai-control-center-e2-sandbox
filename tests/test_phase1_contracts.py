from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from control_kernel.domain import ReasonCode, TaskState, validate_transition
from control_kernel.errors import IdempotencyConflict, InvalidTransition, PolicyDenied, StaleLease, UnsupportedRuntime
from control_kernel.policy import DeterministicPolicy
from control_kernel.runtime import RuntimePin, validate_runtime
from control_kernel.verification import build_verification_handoff
from control_kernel.worker import AppServerWorkerSession, SessionBinding


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "migrations/001_control_kernel.sql").read_text(encoding="utf-8")
KERNEL_SOURCE = (ROOT / "control_kernel/kernel.py").read_text(encoding="utf-8")


class ReferenceKernelModel:
    """Small deterministic model used to exercise the invariants without SQLite."""

    def __init__(self) -> None:
        self.lock_owner: str | None = None
        self.tasks: dict[str, dict[str, object]] = {}
        self.idempotency: dict[tuple[str, str], tuple[str, dict[str, object]]] = {}
        self.audit: list[dict[str, object]] = []
        self.evidence: list[dict[str, object]] = []

    def acquire_orchestrator(self, owner: str) -> None:
        if self.lock_owner is not None:
            raise RuntimeError("orchestrator already owned")
        self.lock_owner = owner

    def create_task(self, task_id: str) -> None:
        self.tasks[task_id] = {
            "state": TaskState.BACKLOG,
            "state_version": 0,
            "attempt_id": 0,
            "lease_epoch": 0,
            "lease_active": False,
        }
        self.audit.append({"event": "TASK_CREATED", "task_id": task_id})

    def make_ready(self, task_id: str) -> None:
        task = self.tasks[task_id]
        validate_transition(task["state"], TaskState.READY)
        task["state"] = TaskState.READY
        task["state_version"] = int(task["state_version"]) + 1

    def claim(self, task_id: str) -> tuple[int, int]:
        task = self.tasks[task_id]
        if task["state"] != TaskState.READY:
            raise InvalidTransition("claim requires READY")
        task["attempt_id"] = int(task["attempt_id"]) if int(task["attempt_id"]) > 0 else 1
        task["lease_epoch"] = int(task["lease_epoch"]) + 1
        task["state"] = TaskState.RUNNING
        task["state_version"] = int(task["state_version"]) + 1
        task["lease_active"] = True
        return int(task["attempt_id"]), int(task["lease_epoch"])

    def expire(self, task_id: str) -> None:
        task = self.tasks[task_id]
        if not task["lease_active"]:
            return
        task["lease_active"] = False
        task["state"] = TaskState.READY
        task["attempt_id"] = int(task["attempt_id"]) + 1
        task["lease_epoch"] = int(task["lease_epoch"]) + 1
        task["state_version"] = int(task["state_version"]) + 1
        self.audit.append({"event": "LEASE_EXPIRED", "task_id": task_id})

    def transition(
        self,
        task_id: str,
        attempt_id: int,
        lease_epoch: int,
        expected_state_version: int,
        target: TaskState,
        idempotency_key: str,
        *,
        reason_code: ReasonCode = ReasonCode.NONE,
        actor_role: str = "control_plane",
        approval_id: str | None = None,
    ) -> tuple[dict[str, object], bool]:
        if actor_role == "worker":
            raise PolicyDenied("worker cannot write authoritative state")
        DeterministicPolicy().authorize_transition(
            current=self.tasks[task_id]["state"],
            target=target,
            reason_code=reason_code,
            actor_role=actor_role,
            approval_id=approval_id,
        )
        request = json.dumps(
            [task_id, attempt_id, lease_epoch, expected_state_version, target.value, reason_code.value, approval_id],
            separators=(",", ":"),
        )
        request_hash = hashlib.sha256(request.encode()).hexdigest()
        existing = self.idempotency.get((task_id, idempotency_key))
        if existing is not None:
            if existing[0] != request_hash:
                raise IdempotencyConflict("key reused for a different request")
            return existing[1], True
        task = self.tasks[task_id]
        if (
            task["state_version"] != expected_state_version
            or task["attempt_id"] != attempt_id
            or task["lease_epoch"] != lease_epoch
        ):
            raise StaleLease("fence mismatch")
        if task["state"] in {TaskState.RUNNING, TaskState.VERIFYING, TaskState.REVIEW} and not task["lease_active"]:
            raise StaleLease("lease expired")
        validate_transition(task["state"], target)
        is_rework = target is TaskState.READY and reason_code is ReasonCode.REWORK_REQUIRED
        if is_rework:
            task["attempt_id"] = int(task["attempt_id"]) + 1
            task["lease_epoch"] = int(task["lease_epoch"]) + 1
            task["lease_active"] = False
        task["state"] = target
        task["state_version"] = int(task["state_version"]) + 1
        response = {"task_id": task_id, "state": target.value, "state_version": task["state_version"]}
        self.idempotency[(task_id, idempotency_key)] = (request_hash, response)
        self.audit.append({"event": "STATE_TRANSITION", "task_id": task_id})
        return response, False


class Phase1ContractTests(unittest.TestCase):
    def test_exact_nine_state_enumeration(self) -> None:
        expected = [
            "BACKLOG",
            "READY",
            "RUNNING",
            "VERIFYING",
            "REVIEW",
            "AWAITING_HUMAN",
            "INTEGRATING",
            "CLOSED",
            "BLOCKED",
        ]
        self.assertEqual([state.value for state in TaskState], expected)
        self.assertIn("'BACKLOG', 'READY', 'RUNNING', 'VERIFYING', 'REVIEW'", MIGRATION)
        self.assertIn("'AWAITING_HUMAN', 'INTEGRATING', 'CLOSED', 'BLOCKED'", MIGRATION)

    def test_deprecated_task_states_are_rejected(self) -> None:
        for deprecated in ("TESTING", "READY_TO_INTEGRATE", "INTEGRATED", "DONE"):
            with self.assertRaises(ValueError, msg=deprecated):
                TaskState(deprecated)
            self.assertNotIn(f"'{deprecated}'", MIGRATION.split("reason_code TEXT", 1)[0])

    def test_verifying_path_and_integration_close_are_valid(self) -> None:
        validate_transition(TaskState.RUNNING, TaskState.VERIFYING)
        validate_transition(TaskState.VERIFYING, TaskState.REVIEW)
        validate_transition(TaskState.REVIEW, TaskState.INTEGRATING)
        validate_transition(TaskState.INTEGRATING, TaskState.CLOSED)

    def test_human_required_review_cannot_bypass_awaiting_human(self) -> None:
        policy = DeterministicPolicy()
        with self.assertRaises(PolicyDenied):
            policy.authorize_transition(
                current=TaskState.REVIEW,
                target=TaskState.INTEGRATING,
                reason_code=ReasonCode.HUMAN_APPROVAL_REQUIRED,
                actor_role="control_plane",
                approval_id=None,
            )
        policy.authorize_transition(
            current=TaskState.REVIEW,
            target=TaskState.AWAITING_HUMAN,
            reason_code=ReasonCode.HUMAN_APPROVAL_REQUIRED,
            actor_role="control_plane",
            approval_id=None,
        )
        with self.assertRaises(PolicyDenied):
            policy.authorize_transition(
                current=TaskState.AWAITING_HUMAN,
                target=TaskState.INTEGRATING,
                reason_code=ReasonCode.NONE,
                actor_role="control_plane",
                approval_id=None,
            )
        policy.authorize_transition(
            current=TaskState.AWAITING_HUMAN,
            target=TaskState.INTEGRATING,
            reason_code=ReasonCode.NONE,
            actor_role="human",
            approval_id="decision-1",
        )

    def test_rework_returns_to_ready_with_incremented_attempt(self) -> None:
        model = ReferenceKernelModel()
        model.create_task("task-1")
        model.make_ready("task-1")
        attempt, epoch = model.claim("task-1")
        response, _ = model.transition(
            "task-1", attempt, epoch, 2, TaskState.VERIFYING, "evt-verify", reason_code=ReasonCode.NONE
        )
        response, _ = model.transition(
            "task-1", attempt, epoch, response["state_version"], TaskState.REVIEW, "evt-review", reason_code=ReasonCode.NONE
        )
        response, _ = model.transition(
            "task-1",
            attempt,
            epoch,
            response["state_version"],
            TaskState.READY,
            "evt-rework",
            reason_code=ReasonCode.REWORK_REQUIRED,
        )
        self.assertEqual(response["state"], TaskState.READY.value)
        self.assertEqual(model.tasks["task-1"]["attempt_id"], 2)
        self.assertEqual(model.claim("task-1"), (2, 3))

    def test_only_one_orchestrator_can_own_control(self) -> None:
        model = ReferenceKernelModel()
        model.acquire_orchestrator("orchestrator-a")
        with self.assertRaises(RuntimeError):
            model.acquire_orchestrator("orchestrator-b")
        self.assertIn("pg_try_advisory_lock", KERNEL_SOURCE)

    def test_stale_lease_cannot_commit_authoritative_state(self) -> None:
        model = ReferenceKernelModel()
        model.create_task("task-1")
        model.make_ready("task-1")
        attempt, epoch = model.claim("task-1")
        with self.assertRaises(StaleLease):
            model.transition("task-1", attempt, epoch - 1, 2, TaskState.VERIFYING, "evt-1")
        model.expire("task-1")
        with self.assertRaises(StaleLease):
            model.transition("task-1", attempt, epoch, 2, TaskState.VERIFYING, "evt-2")
        self.assertIn("lease_expires_at > clock_timestamp()", KERNEL_SOURCE)

    def test_expired_lease_returns_to_ready_and_next_claim_increments_attempt(self) -> None:
        model = ReferenceKernelModel()
        model.create_task("task-1")
        model.make_ready("task-1")
        first_attempt, first_epoch = model.claim("task-1")
        model.expire("task-1")
        second_attempt, second_epoch = model.claim("task-1")
        self.assertEqual((first_attempt, first_epoch), (1, 1))
        self.assertEqual((second_attempt, second_epoch), (2, 3))

    def test_duplicate_events_are_idempotent_and_conflicting_reuse_is_rejected(self) -> None:
        model = ReferenceKernelModel()
        model.create_task("task-1")
        model.make_ready("task-1")
        attempt, epoch = model.claim("task-1")
        first, replayed = model.transition("task-1", attempt, epoch, 2, TaskState.VERIFYING, "evt-1")
        second, replayed_again = model.transition("task-1", attempt, epoch, 2, TaskState.VERIFYING, "evt-1")
        self.assertFalse(replayed)
        self.assertTrue(replayed_again)
        self.assertEqual(first, second)
        with self.assertRaises(IdempotencyConflict):
            model.transition("task-1", attempt, epoch, 2, TaskState.BLOCKED, "evt-1")

    def test_worker_cannot_mutate_authoritative_state(self) -> None:
        with self.assertRaises(PolicyDenied):
            DeterministicPolicy().authorize_state_write("worker")
        self.assertIn("REVOKE ALL ON", MIGRATION)
        self.assertIn("control_kernel_worker", MIGRATION)

    def test_invalid_state_transitions_are_rejected(self) -> None:
        with self.assertRaises(InvalidTransition):
            validate_transition(TaskState.CLOSED, TaskState.READY)
        with self.assertRaises(InvalidTransition):
            validate_transition(TaskState.BACKLOG, TaskState.CLOSED)

    def test_audit_and_evidence_are_append_only(self) -> None:
        self.assertIn("BEFORE UPDATE OR DELETE", MIGRATION)
        self.assertIn("audit_events_append_only", MIGRATION)
        self.assertIn("evidence_records_append_only", MIGRATION)
        self.assertIn("REVOKE UPDATE, DELETE, TRUNCATE ON audit_events, evidence_records FROM PUBLIC", MIGRATION)
        self.assertNotIn("GRANT SELECT, INSERT ON audit_events, evidence_records TO PUBLIC", MIGRATION)

    def test_runtime_and_schema_fail_closed_when_pin_is_incomplete_or_unsupported(self) -> None:
        pin_path = ROOT / "runtime/codex-app-server-pin.json"
        with self.assertRaises(UnsupportedRuntime):
            RuntimePin.from_json(pin_path)
        schema = b'{"jsonrpc":"2.0"}'
        digest = hashlib.sha256(schema).hexdigest()
        self.assertEqual(validate_runtime("0.153.2", schema, expected_schema_sha256=digest), digest)
        with self.assertRaises(UnsupportedRuntime):
            validate_runtime("0.153.0-alpha.5", schema, expected_schema_sha256=digest)
        with self.assertRaises(UnsupportedRuntime):
            validate_runtime("0.153.2", schema)

    def test_worker_session_is_bound_to_one_task_attempt_epoch_and_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            schema_path = Path(directory) / "schema.json"
            schema = b'{"version":"0.153.2"}'
            schema_path.write_bytes(schema)
            pin = RuntimePin("0.153.2", schema_path, hashlib.sha256(schema).hexdigest())
            workspace_parent = Path(directory) / "workspace"
            workspace_parent.mkdir()
            worktree = workspace_parent / "worktree"
            worktree.mkdir()
            session = AppServerWorkerSession(
                binding=SessionBinding("task-1", 1, 1),
                worktree=worktree,
                workspace_parent=workspace_parent,
                runtime_pin=pin,
            )
            session.validate_runtime("0.153.2")
            self.assertEqual(session.command(), ("codex", "app-server"))
            session.authorize_write(Path("src/change.py"))
            with self.assertRaises(StaleLease):
                session.validate_event_binding(task_id="task-2", attempt_id=1, lease_epoch=1)
            with self.assertRaises(PolicyDenied):
                session.authorize_write(Path("docs/ai-control-center/README.md"))

    def test_verification_handoff_is_machine_generated_and_external_ci_authoritative(self) -> None:
        handoff = build_verification_handoff(
            project_id="owner/repo",
            task_id="a" * 40,
            attempt_id=1,
            lease_epoch=1,
            branch="codex/task-1",
            base_sha="b" * 40,
            commit_sha="c" * 40,
            diff_bytes=b"diff",
            acceptance_contract={"required_check": "authoritative-ci"},
        )
        payload = json.loads(handoff.as_machine_input())
        self.assertEqual(payload["provider"], "github-hosted")
        self.assertEqual(payload["required_check"], "authoritative-ci")
        self.assertEqual(payload["lease_epoch"], 1)


if __name__ == "__main__":
    unittest.main()
