from __future__ import annotations

from enum import Enum

from .errors import InvalidTransition


class TaskState(str, Enum):
    BACKLOG = "BACKLOG"
    READY = "READY"
    RUNNING = "RUNNING"
    TESTING = "TESTING"
    REVIEW = "REVIEW"
    READY_TO_INTEGRATE = "READY_TO_INTEGRATE"
    INTEGRATED = "INTEGRATED"
    DONE = "DONE"
    BLOCKED = "BLOCKED"


class ReasonCode(str, Enum):
    UNPLANNED = "UNPLANNED"
    DEPENDENCY_PENDING = "DEPENDENCY_PENDING"
    AWAITING_ASSIGNMENT = "AWAITING_ASSIGNMENT"
    IMPLEMENTING = "IMPLEMENTING"
    REWORK_REQUIRED = "REWORK_REQUIRED"
    TEST_FAILURE = "TEST_FAILURE"
    REVIEW_PENDING = "REVIEW_PENDING"
    REVIEW_FAILURE = "REVIEW_FAILURE"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
    POLICY_DENIED = "POLICY_DENIED"
    BUDGET_WARNING = "BUDGET_WARNING"
    BUDGET_HARD_LIMIT = "BUDGET_HARD_LIMIT"
    RUNTIME_CRASH = "RUNTIME_CRASH"
    TIMEOUT = "TIMEOUT"
    STALL = "STALL"
    GIT_CONFLICT = "GIT_CONFLICT"
    BASE_DRIFT = "BASE_DRIFT"
    CANCELLED = "CANCELLED"
    ROLLED_BACK = "ROLLED_BACK"
    NO_PROGRESS = "NO_PROGRESS"
    EVIDENCE_MISSING = "EVIDENCE_MISSING"
    NONE = "NONE"


ALLOWED_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.BACKLOG: frozenset({TaskState.READY, TaskState.BLOCKED}),
    TaskState.READY: frozenset({TaskState.RUNNING, TaskState.BLOCKED}),
    TaskState.RUNNING: frozenset({TaskState.TESTING, TaskState.BLOCKED}),
    TaskState.TESTING: frozenset({TaskState.REVIEW, TaskState.RUNNING, TaskState.BLOCKED}),
    TaskState.REVIEW: frozenset({TaskState.READY_TO_INTEGRATE, TaskState.RUNNING, TaskState.BLOCKED}),
    TaskState.READY_TO_INTEGRATE: frozenset({TaskState.INTEGRATED, TaskState.BLOCKED}),
    TaskState.INTEGRATED: frozenset({TaskState.DONE, TaskState.BLOCKED}),
    TaskState.DONE: frozenset(),
    TaskState.BLOCKED: frozenset({TaskState.READY, TaskState.RUNNING}),
}


def validate_transition(current: TaskState | str, target: TaskState | str) -> None:
    current_state = TaskState(current)
    target_state = TaskState(target)
    if target_state not in ALLOWED_TRANSITIONS[current_state]:
        raise InvalidTransition(f"{current_state.value} -> {target_state.value} is not allowed")
