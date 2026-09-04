from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .domain import ReasonCode, TaskState
from .errors import PolicyDenied, UnsupportedRuntime


PROTECTED_PATHS = frozenset({
    "00-CONSTITUTION.md",
    "DECISIONS.md",
    "OPEN-QUESTIONS.md",
    "MASTER-SPEC.md",
})
PROTECTED_PREFIXES = (
    ".github/workflows",
    "docs/ai-control-center",
    "policy",
    "budget",
)


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    rule: str
    reason: str


class DeterministicPolicy:
    """Policy decisions are pure code; no model output is consulted."""

    def authorize_worker_write(self, worktree: Path, candidate: Path) -> PolicyDecision:
        root = worktree.resolve(strict=False)
        target = (root / candidate if not candidate.is_absolute() else candidate).resolve(strict=False)
        try:
            relative = target.relative_to(root).as_posix()
        except ValueError:
            return PolicyDecision(False, "WORKTREE_CONTAINMENT", "target is outside the authorized worktree")

        if relative.startswith(".github/workflows/") or relative == ".github/workflows":
            return PolicyDecision(False, "PROTECTED_PATH", "workflow files are protected")
        if any(relative == prefix or relative.startswith(prefix + "/") for prefix in PROTECTED_PREFIXES):
            return PolicyDecision(False, "PROTECTED_PATH", "control-plane and policy paths are protected")
        if relative in PROTECTED_PATHS:
            return PolicyDecision(False, "PROTECTED_PATH", "governance files are protected")
        return PolicyDecision(True, "WORKTREE_ONLY", "path is contained by the authorized worktree")

    def authorize_state_write(self, actor_role: str) -> PolicyDecision:
        if actor_role.lower() == "worker":
            raise PolicyDenied("Worker cannot authoritatively mutate Control Plane state")
        return PolicyDecision(True, "CONTROL_PLANE_ONLY", "state write is restricted to the Control Plane")

    def authorize_transition(
        self,
        *,
        current: TaskState | str,
        target: TaskState | str,
        reason_code: ReasonCode,
        actor_role: str,
        approval_id: str | None,
    ) -> PolicyDecision:
        self.authorize_state_write(actor_role)
        current_state = TaskState(current)
        target_state = TaskState(target)
        if (
            current_state is TaskState.REVIEW
            and target_state is TaskState.INTEGRATING
            and reason_code is ReasonCode.HUMAN_APPROVAL_REQUIRED
        ):
            raise PolicyDenied("human-required review must enter AWAITING_HUMAN first")
        if current_state is TaskState.AWAITING_HUMAN:
            if actor_role.lower() != "human" or not approval_id:
                raise PolicyDenied("AWAITING_HUMAN requires an explicit human approval decision")
        return PolicyDecision(True, "DETERMINISTIC_TRANSITION", "transition is permitted by policy")

    def authorize_runtime(
        self,
        reported_version: str,
        schema_bytes: bytes,
        expected_version: str,
        expected_schema_sha256: str | None,
    ) -> None:
        if reported_version != expected_version:
            raise UnsupportedRuntime(f"unsupported Codex runtime: {reported_version!r}")
        if not expected_schema_sha256:
            raise UnsupportedRuntime("exact version-specific App Server schema digest is not pinned")
        observed = hashlib.sha256(schema_bytes).hexdigest()
        if observed != expected_schema_sha256:
            raise UnsupportedRuntime("App Server schema digest does not match the pinned artifact")
