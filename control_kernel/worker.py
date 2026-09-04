from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import PolicyDenied, StaleLease
from .policy import DeterministicPolicy
from .runtime import RuntimePin


@dataclass(frozen=True)
class SessionBinding:
    """The immutable identity carried by every single-worker App Server session."""

    task_id: str
    attempt_id: int
    lease_epoch: int

    def __post_init__(self) -> None:
        if not self.task_id or self.attempt_id < 1 or self.lease_epoch < 1:
            raise ValueError("a session binding requires a task and positive attempt/epoch")


class AppServerWorkerSession:
    """One isolated Codex App Server session; no session pooling or reuse."""

    def __init__(
        self,
        *,
        binding: SessionBinding,
        worktree: Path,
        workspace_parent: Path,
        runtime_pin: RuntimePin,
        policy: DeterministicPolicy | None = None,
    ) -> None:
        self.binding = binding
        parent = workspace_parent.resolve(strict=False)
        resolved_worktree = worktree.resolve(strict=False)
        if resolved_worktree == parent:
            raise PolicyDenied("Worker must use a child isolated worktree, not its workspace root")
        try:
            resolved_worktree.relative_to(parent)
        except ValueError as exc:
            raise PolicyDenied("Worker worktree must be contained by its dedicated workspace") from exc
        if not resolved_worktree.is_dir():
            raise ValueError("Worker worktree must already exist as a directory")
        self.worktree = resolved_worktree
        self.runtime_pin = runtime_pin
        self.policy = policy or DeterministicPolicy()
        self._closed = False

    def validate_runtime(self, reported_version: str) -> None:
        self.runtime_pin.validate(reported_version)

    def command(self) -> tuple[str, ...]:
        if self._closed:
            raise RuntimeError("worker session is closed")
        return ("codex", "app-server")

    def validate_event_binding(self, *, task_id: str, attempt_id: int, lease_epoch: int) -> None:
        if (task_id, attempt_id, lease_epoch) != (
            self.binding.task_id,
            self.binding.attempt_id,
            self.binding.lease_epoch,
        ):
            raise StaleLease("App Server event does not match the bound task/attempt/lease")

    def authorize_write(self, candidate: Path) -> None:
        if self._closed:
            raise RuntimeError("worker session is closed")
        decision = self.policy.authorize_worker_write(self.worktree, candidate)
        if not decision.allowed:
            raise PolicyDenied(decision.reason)

    def close(self) -> None:
        self._closed = True
