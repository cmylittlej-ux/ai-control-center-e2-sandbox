from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

from .domain import ReasonCode, TaskState, validate_transition
from .errors import IdempotencyConflict, InvalidTransition, OrchestratorAlreadyOwned, StaleLease
from .policy import DeterministicPolicy
from .postgres import PostgresConnection


@dataclass(frozen=True)
class Lease:
    task_id: str
    attempt_id: int
    lease_epoch: int
    worker_id: str


@dataclass(frozen=True)
class TransitionReceipt:
    task_id: str
    state: str
    state_version: int
    idempotency_key: str
    replayed: bool


class OrchestratorLock:
    def __init__(self, connection: Any):
        self._connection = connection

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "OrchestratorLock":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()


class PostgresControlPlane:
    """Authoritative state operations backed exclusively by PostgreSQL."""

    def __init__(self, database: PostgresConnection, policy: DeterministicPolicy | None = None):
        self.database = database
        self.policy = policy or DeterministicPolicy()

    @staticmethod
    def advisory_lock_key(scope: str) -> int:
        digest = hashlib.sha256(f"control-plane:{scope}".encode("utf-8")).digest()[:8]
        return int.from_bytes(digest, byteorder="big", signed=True)

    def acquire_orchestrator_lock(self, scope: str) -> OrchestratorLock:
        connection = self.database.connect()
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", (self.advisory_lock_key(scope),))
            acquired = bool(cursor.fetchone()[0])
        except Exception:
            connection.close()
            raise
        finally:
            cursor.close()
        if not acquired:
            connection.close()
            raise OrchestratorAlreadyOwned(f"orchestrator lock is already held for {scope!r}")
        return OrchestratorLock(connection)

    @contextmanager
    def _transaction(self) -> Iterator[tuple[Any, Any]]:
        with self.database.transaction() as pair:
            yield pair

    def create_task(
        self,
        *,
        project_id: str,
        task_id: str,
        acceptance_contract: Mapping[str, Any],
        branch: str,
    ) -> None:
        with self._transaction() as (_, cursor):
            cursor.execute(
                """
                INSERT INTO tasks
                    (project_id, task_id, state, reason_code, state_version, current_attempt_id, lease_epoch,
                     branch, acceptance_contract, created_at, updated_at)
                VALUES (%s, %s, 'BACKLOG', 'UNPLANNED', 0, 0, 0, %s, %s::jsonb, clock_timestamp(), clock_timestamp())
                """,
                (project_id, task_id, branch, json.dumps(dict(acceptance_contract), sort_keys=True)),
            )
            self._append_audit(cursor, "TASK_CREATED", task_id, None, None, {"project_id": project_id})

    def claim_task(self, *, task_id: str, worker_id: str, lease_seconds: int) -> Lease:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        with self._transaction() as (_, cursor):
            cursor.execute(
                "SELECT state, current_attempt_id, lease_epoch FROM tasks WHERE task_id = %s FOR UPDATE",
                (task_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise KeyError(task_id)
            state, current_attempt, current_epoch = row
            if state != TaskState.READY.value:
                raise InvalidTransition(f"cannot claim task in state {state}")
            attempt_id = int(current_attempt) if int(current_attempt) > 0 else 1
            lease_epoch = int(current_epoch) + 1
            cursor.execute(
                """
                UPDATE tasks
                   SET state = 'RUNNING', reason_code = 'IMPLEMENTING',
                       current_attempt_id = %s, lease_epoch = %s,
                       state_version = state_version + 1, updated_at = clock_timestamp()
                 WHERE task_id = %s AND state = 'READY'
                """,
                (attempt_id, lease_epoch, task_id),
            )
            if cursor.rowcount != 1:
                raise StaleLease("task changed before lease claim")
            cursor.execute(
                """
                INSERT INTO executions
                    (task_id, attempt_id, lease_epoch, worker_id, status, lease_expires_at, heartbeat_at, started_at)
                VALUES (%s, %s, %s, %s, 'ACTIVE',
                        clock_timestamp() + (%s * interval '1 second'), clock_timestamp(), clock_timestamp())
                """,
                (task_id, attempt_id, lease_epoch, worker_id, lease_seconds),
            )
            self._append_audit(cursor, "LEASE_CLAIMED", task_id, attempt_id, lease_epoch, {"worker_id": worker_id})
            return Lease(task_id, attempt_id, lease_epoch, worker_id)

    def heartbeat(self, lease: Lease, lease_seconds: int) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        with self._transaction() as (_, cursor):
            cursor.execute(
                """
                UPDATE executions
                   SET heartbeat_at = clock_timestamp(),
                       lease_expires_at = clock_timestamp() + (%s * interval '1 second')
                 WHERE task_id = %s AND attempt_id = %s AND lease_epoch = %s
                   AND status = 'ACTIVE' AND lease_expires_at > clock_timestamp()
                """,
                (lease_seconds, lease.task_id, lease.attempt_id, lease.lease_epoch),
            )
            if cursor.rowcount != 1:
                raise StaleLease("heartbeat rejected by fencing or expiry")

    def expire_lease(self, lease: Lease) -> bool:
        with self._transaction() as (_, cursor):
            cursor.execute(
                """
                SELECT state, current_attempt_id, lease_epoch
                  FROM tasks WHERE task_id = %s FOR UPDATE
                """,
                (lease.task_id,),
            )
            task = cursor.fetchone()
            if task is None:
                raise KeyError(lease.task_id)
            if (task[0], int(task[1]), int(task[2])) != (
                TaskState.RUNNING.value,
                lease.attempt_id,
                lease.lease_epoch,
            ):
                raise StaleLease("expired execution no longer owns task")
            cursor.execute(
                """
                UPDATE executions SET status = 'EXPIRED', ended_at = clock_timestamp()
                 WHERE task_id = %s AND attempt_id = %s AND lease_epoch = %s
                   AND status = 'ACTIVE' AND lease_expires_at <= clock_timestamp()
                """,
                (lease.task_id, lease.attempt_id, lease.lease_epoch),
            )
            if cursor.rowcount != 1:
                return False
            cursor.execute(
                """
                UPDATE tasks
                   SET state = 'READY', reason_code = 'TIMEOUT',
                       current_attempt_id = current_attempt_id + 1,
                       lease_epoch = lease_epoch + 1,
                       state_version = state_version + 1, updated_at = clock_timestamp()
                 WHERE task_id = %s AND state = 'RUNNING' AND current_attempt_id = %s AND lease_epoch = %s
                """,
                (lease.task_id, lease.attempt_id, lease.lease_epoch),
            )
            if cursor.rowcount != 1:
                raise StaleLease("expired execution no longer owns task")
            self._append_audit(cursor, "LEASE_EXPIRED", lease.task_id, lease.attempt_id, lease.lease_epoch, {})
            return True

    def fence_lease(self, lease: Lease, *, target: TaskState, reason_code: ReasonCode) -> None:
        """Fence an active execution and move it to a safe terminal/recovery state."""
        self.policy.authorize_state_write("control_plane")
        with self._transaction() as (_, cursor):
            cursor.execute(
                """
                SELECT state, current_attempt_id, lease_epoch
                  FROM tasks WHERE task_id = %s FOR UPDATE
                """,
                (lease.task_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise KeyError(lease.task_id)
            if (row[1], row[2]) != (lease.attempt_id, lease.lease_epoch):
                raise StaleLease("cannot fence a stale execution")
            validate_transition(row[0], target)
            cursor.execute(
                """
                UPDATE executions
                   SET status = 'RELEASED', ended_at = clock_timestamp()
                 WHERE task_id = %s AND attempt_id = %s AND lease_epoch = %s AND status = 'ACTIVE'
                """,
                (lease.task_id, lease.attempt_id, lease.lease_epoch),
            )
            cursor.execute(
                """
                UPDATE tasks
                   SET state = %s, reason_code = %s,
                       state_version = state_version + 1, updated_at = clock_timestamp()
                 WHERE task_id = %s AND state = %s
                   AND current_attempt_id = %s AND lease_epoch = %s
                """,
                (target.value, reason_code.value, lease.task_id, row[0], lease.attempt_id, lease.lease_epoch),
            )
            if cursor.rowcount != 1:
                raise StaleLease("lease fencing lost its state predicate")
            self._append_audit(
                cursor,
                "LEASE_FENCED",
                lease.task_id,
                lease.attempt_id,
                lease.lease_epoch,
                {"target": target.value, "reason_code": reason_code.value},
            )

    def transition(
        self,
        *,
        task_id: str,
        attempt_id: int,
        lease_epoch: int,
        expected_state_version: int,
        target: TaskState,
        reason_code: ReasonCode,
        idempotency_key: str,
        actor_role: str = "control_plane",
        approval_id: str | None = None,
        evidence_refs: tuple[str, ...] = (),
    ) -> TransitionReceipt:
        self.policy.authorize_state_write(actor_role)
        request = {
            "task_id": task_id,
            "attempt_id": attempt_id,
            "lease_epoch": lease_epoch,
            "expected_state_version": expected_state_version,
            "target": target.value,
            "reason_code": reason_code.value,
            "approval_id": approval_id,
            "evidence_refs": evidence_refs,
        }
        request_hash = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with self._transaction() as (_, cursor):
            cursor.execute(
                "SELECT request_hash, response_json FROM idempotency_keys WHERE scope = %s AND idempotency_key = %s FOR UPDATE",
                (task_id, idempotency_key),
            )
            existing = cursor.fetchone()
            if existing is not None:
                if existing[0] != request_hash:
                    raise IdempotencyConflict("idempotency key was reused with a different request")
                response = json.loads(existing[1]) if isinstance(existing[1], str) else existing[1]
                return TransitionReceipt(**response, replayed=True)
            cursor.execute(
                """
                SELECT state, state_version, current_attempt_id, lease_epoch
                  FROM tasks WHERE task_id = %s FOR UPDATE
                """,
                (task_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise KeyError(task_id)
            current_state, current_version, current_attempt, current_epoch = row
            self.policy.authorize_transition(
                current=current_state,
                target=target,
                reason_code=reason_code,
                actor_role=actor_role,
                approval_id=approval_id,
            )
            if int(current_version) != expected_state_version or int(current_attempt) != attempt_id or int(current_epoch) != lease_epoch:
                raise StaleLease("state transition failed fencing/version checks")
            if current_state in {TaskState.RUNNING.value, TaskState.VERIFYING.value, TaskState.REVIEW.value}:
                cursor.execute(
                    """
                    SELECT 1 FROM executions
                     WHERE task_id = %s AND attempt_id = %s AND lease_epoch = %s
                       AND status = 'ACTIVE' AND lease_expires_at > clock_timestamp()
                    """,
                    (task_id, attempt_id, lease_epoch),
                )
                if cursor.fetchone() is None:
                    raise StaleLease("state transition rejected by an expired or missing lease")
            validate_transition(current_state, target)
            is_rework = target is TaskState.READY and reason_code is ReasonCode.REWORK_REQUIRED
            if is_rework:
                cursor.execute(
                    """
                    UPDATE executions
                       SET status = 'RELEASED', ended_at = clock_timestamp()
                     WHERE task_id = %s AND attempt_id = %s AND lease_epoch = %s AND status = 'ACTIVE'
                    """,
                    (task_id, attempt_id, lease_epoch),
                )
            cursor.execute(
                """
                UPDATE tasks
                   SET state = %s, reason_code = %s,
                       current_attempt_id = CASE WHEN %s THEN current_attempt_id + 1 ELSE current_attempt_id END,
                       lease_epoch = CASE WHEN %s THEN lease_epoch + 1 ELSE lease_epoch END,
                       state_version = state_version + 1, updated_at = clock_timestamp()
                 WHERE task_id = %s AND state_version = %s AND current_attempt_id = %s AND lease_epoch = %s
                """,
                (
                    target.value,
                    reason_code.value,
                    is_rework,
                    is_rework,
                    task_id,
                    expected_state_version,
                    attempt_id,
                    lease_epoch,
                ),
            )
            if cursor.rowcount != 1:
                raise StaleLease("state transition lost its fence")
            new_version = expected_state_version + 1
            response = {
                "task_id": task_id,
                "state": target.value,
                "state_version": new_version,
                "idempotency_key": idempotency_key,
            }
            cursor.execute(
                "INSERT INTO idempotency_keys(scope, idempotency_key, request_hash, response_json, created_at) VALUES (%s, %s, %s, %s::jsonb, clock_timestamp())",
                (task_id, idempotency_key, request_hash, json.dumps(response, sort_keys=True)),
            )
            self._append_audit(cursor, "STATE_TRANSITION", task_id, attempt_id, lease_epoch, request | {"result": response})
            return TransitionReceipt(**response, replayed=False)

    def append_evidence(
        self,
        *,
        task_id: str,
        attempt_id: int,
        lease_epoch: int,
        kind: str,
        payload: Mapping[str, Any],
    ) -> str:
        with self._transaction() as (_, cursor):
            cursor.execute(
                """
                SELECT 1 FROM executions
                 WHERE task_id = %s AND attempt_id = %s AND lease_epoch = %s AND status = 'ACTIVE'
                   AND lease_expires_at > clock_timestamp()
                """,
                (task_id, attempt_id, lease_epoch),
            )
            if cursor.fetchone() is None:
                raise StaleLease("evidence append rejected by fencing or expiry")
            record = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            digest = hashlib.sha256(record.encode("utf-8")).hexdigest()
            cursor.execute(
                """
                SELECT last_hash FROM audit_chain_heads WHERE singleton_id = 1 FOR UPDATE
                """,
            )
            previous = cursor.fetchone()[0]
            record_hash = hashlib.sha256(f"{previous or ''}:{digest}".encode("utf-8")).hexdigest()
            cursor.execute(
                """
                INSERT INTO evidence_records
                    (record_hash, task_id, attempt_id, lease_epoch, kind, payload_json, prev_hash, captured_at)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, clock_timestamp())
                """,
                (record_hash, task_id, attempt_id, lease_epoch, kind, record, previous),
            )
            cursor.execute("UPDATE audit_chain_heads SET last_hash = %s WHERE singleton_id = 1", (record_hash,))
            self._append_audit(cursor, "EVIDENCE_APPENDED", task_id, attempt_id, lease_epoch, {"record_hash": record_hash, "kind": kind})
            return record_hash

    @staticmethod
    def _append_audit(cursor: Any, event_type: str, task_id: str, attempt_id: int | None, lease_epoch: int | None, payload: Mapping[str, Any]) -> str:
        cursor.execute("SELECT last_hash FROM audit_chain_heads WHERE singleton_id = 1 FOR UPDATE")
        previous = cursor.fetchone()[0]
        body = json.dumps({"event_type": event_type, "task_id": task_id, "attempt_id": attempt_id, "lease_epoch": lease_epoch, "payload": dict(payload)}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        record_hash = hashlib.sha256(f"{previous or ''}:{body}".encode("utf-8")).hexdigest()
        cursor.execute(
            """
            INSERT INTO audit_events
                (record_hash, event_type, task_id, attempt_id, lease_epoch, payload_json, prev_hash, occurred_at)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, clock_timestamp())
            """,
            (record_hash, event_type, task_id, attempt_id, lease_epoch, body, previous),
        )
        cursor.execute("UPDATE audit_chain_heads SET last_hash = %s WHERE singleton_id = 1", (record_hash,))
        return record_hash
