from __future__ import annotations

import hashlib
import json
import threading
import time
import unittest
import uuid

try:
    import psycopg
except ImportError:  # pragma: no cover - exercised only when live deps are absent
    psycopg = None

from control_kernel.domain import ReasonCode, TaskState
from control_kernel.errors import IdempotencyConflict, StaleLease
from control_kernel.kernel import PostgresControlPlane
from control_kernel.postgres import PostgresConnection


@unittest.skipIf(psycopg is None, "psycopg is required for live PostgreSQL integration tests")
class PostgresIntegrationTests(unittest.TestCase):
    dsn = "host=/tmp port=5432 dbname=aicc_phase1 user=mengyaocong"

    @classmethod
    def setUpClass(cls) -> None:
        cls.database = PostgresConnection(cls.dsn)
        cls.control = PostgresControlPlane(cls.database)
        with psycopg.connect(cls.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), current_user, version()")
                database, user, version = cursor.fetchone()
                if database != "aicc_phase1" or user != "mengyaocong":
                    raise AssertionError(f"unexpected integration target: {database=} {user=}")
                cls.pg_version = version

    @classmethod
    def tearDownClass(cls) -> None:
        cls.database = None

    @classmethod
    def new_ready_task(cls) -> str:
        task_id = f"live-{uuid.uuid4().hex}"
        cls.control.create_task(
            project_id="phase1-disposable",
            task_id=task_id,
            acceptance_contract={"check": "live-postgres"},
            branch=f"task/{task_id}",
        )
        cls.control.transition(
            task_id=task_id,
            attempt_id=0,
            lease_epoch=0,
            expected_state_version=0,
            target=TaskState.READY,
            reason_code=ReasonCode.AWAITING_ASSIGNMENT,
            idempotency_key=f"ready-{task_id}",
        )
        return task_id

    def test_migration_constraints_match_exact_frozen_nine_states(self) -> None:
        expected = {
            "BACKLOG",
            "READY",
            "RUNNING",
            "VERIFYING",
            "REVIEW",
            "AWAITING_HUMAN",
            "INTEGRATING",
            "CLOSED",
            "BLOCKED",
        }
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pg_get_constraintdef(oid)
                      FROM pg_constraint
                     WHERE conrelid = 'control_kernel.tasks'::regclass
                       AND conname LIKE '%state%'
                    """
                )
                definition = " ".join(row[0] for row in cursor.fetchall())
                for state in expected:
                    self.assertIn(state, definition)
                for deprecated in ("TESTING", "READY_TO_INTEGRATE", "INTEGRATED", "DONE"):
                    self.assertNotIn(deprecated, definition)
                with self.assertRaises(psycopg.errors.CheckViolation):
                    cursor.execute(
                        """
                        INSERT INTO control_kernel.tasks
                            (project_id, task_id, state, reason_code, branch, acceptance_contract)
                        VALUES ('phase1-disposable', %s, 'TESTING', 'NONE', 'task/invalid', '{}'::jsonb)
                        """,
                        (f"invalid-{uuid.uuid4().hex}",),
                    )

    def test_two_independent_sessions_allow_only_one_advisory_lock_owner(self) -> None:
        scope = f"live-lock-{uuid.uuid4().hex}"
        key = PostgresControlPlane.advisory_lock_key(scope)
        first = psycopg.connect(self.dsn)
        second = psycopg.connect(self.dsn)
        try:
            with first.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_lock(%s)", (key,))
                self.assertTrue(cursor.fetchone()[0])
            with second.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_lock(%s)", (key,))
                self.assertFalse(cursor.fetchone()[0])
        finally:
            first.close()
            second.close()
        with psycopg.connect(self.dsn) as third:
            with third.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_lock(%s)", (key,))
                self.assertTrue(cursor.fetchone()[0])

    def test_real_lease_fencing_db_time_and_expiry_increment_attempt(self) -> None:
        task_id = self.new_ready_task()
        lease = self.control.claim_task(task_id=task_id, worker_id="live-worker", lease_seconds=1)
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE control_kernel.tasks
                       SET state = 'VERIFYING'
                     WHERE task_id = %s AND state_version = 2
                       AND current_attempt_id = %s AND lease_epoch = %s
                    """,
                    (task_id, lease.attempt_id, lease.lease_epoch - 1),
                )
                self.assertEqual(cursor.rowcount, 0)
                cursor.execute("SELECT clock_timestamp(), lease_expires_at FROM control_kernel.executions WHERE task_id = %s", (task_id,))
                db_now, expires_at = cursor.fetchone()
                self.assertGreater(expires_at, db_now)
        time.sleep(1.2)
        with self.assertRaises(StaleLease):
            self.control.heartbeat(lease, lease_seconds=5)
        self.assertTrue(self.control.expire_lease(lease))
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT state, current_attempt_id, lease_epoch FROM control_kernel.tasks WHERE task_id = %s",
                    (task_id,),
                )
                state, attempt_id, lease_epoch = cursor.fetchone()
                self.assertEqual((state, attempt_id), ("READY", 2))
                self.assertEqual(lease_epoch, 2)
        next_lease = self.control.claim_task(task_id=task_id, worker_id="live-worker-2", lease_seconds=10)
        self.assertEqual((next_lease.attempt_id, next_lease.lease_epoch), (2, 3))

    def test_transaction_rollback_row_lock_and_conflicting_transition(self) -> None:
        rollback_task = f"rollback-{uuid.uuid4().hex}"
        with self.assertRaises(RuntimeError):
            with self.database.transaction() as (_, cursor):
                cursor.execute(
                    """
                    INSERT INTO control_kernel.tasks
                        (project_id, task_id, state, reason_code, branch, acceptance_contract)
                    VALUES ('phase1-disposable', %s, 'BACKLOG', 'UNPLANNED', %s, '{}'::jsonb)
                    """,
                    (rollback_task, f"task/{rollback_task}"),
                )
                raise RuntimeError("intentional rollback probe")
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM control_kernel.tasks WHERE task_id = %s", (rollback_task,))
                self.assertEqual(cursor.fetchone()[0], 0)

        lock_task = self.new_ready_task()
        lock_lease = self.control.claim_task(task_id=lock_task, worker_id="lock-holder", lease_seconds=30)
        holder_ready = threading.Event()

        def hold_row_lock() -> None:
            with psycopg.connect(self.dsn) as holder:
                with holder.cursor() as cursor:
                    cursor.execute("BEGIN")
                    cursor.execute("SELECT task_id FROM control_kernel.tasks WHERE task_id = %s FOR UPDATE", (lock_task,))
                    holder_ready.set()
                    time.sleep(1.0)
                    cursor.execute("COMMIT")

        holder_thread = threading.Thread(target=hold_row_lock)
        holder_thread.start()
        self.assertTrue(holder_ready.wait(timeout=5))
        with psycopg.connect(self.dsn) as contender:
            with contender.cursor() as cursor:
                cursor.execute("SET lock_timeout = '200ms'")
                cursor.execute("BEGIN")
                with self.assertRaises(psycopg.errors.LockNotAvailable):
                    cursor.execute("SELECT task_id FROM control_kernel.tasks WHERE task_id = %s FOR UPDATE", (lock_task,))
                cursor.execute("ROLLBACK")
        holder_thread.join(timeout=5)
        self.assertFalse(holder_thread.is_alive())

        conflict_task = self.new_ready_task()
        conflict_lease = self.control.claim_task(task_id=conflict_task, worker_id="conflict-worker", lease_seconds=30)
        barrier = threading.Barrier(2)
        outcomes: list[object] = []

        def conflicting_transition(index: int) -> None:
            try:
                barrier.wait(timeout=5)
                outcomes.append(
                    self.control.transition(
                        task_id=conflict_task,
                        attempt_id=conflict_lease.attempt_id,
                        lease_epoch=conflict_lease.lease_epoch,
                        expected_state_version=2,
                        target=TaskState.VERIFYING,
                        reason_code=ReasonCode.VERIFICATION_PENDING,
                        idempotency_key=f"conflict-{index}",
                    )
                )
            except Exception as exc:  # noqa: BLE001 - preserve exact competing outcome
                outcomes.append(exc)

        threads = [threading.Thread(target=conflicting_transition, args=(index,)) for index in (1, 2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(sum(isinstance(outcome, StaleLease) for outcome in outcomes), 1)

    def test_idempotent_replay_and_conflicting_payload_are_rejected(self) -> None:
        task_id = self.new_ready_task()
        lease = self.control.claim_task(task_id=task_id, worker_id="idempotency-worker", lease_seconds=30)
        first = self.control.transition(
            task_id=task_id,
            attempt_id=lease.attempt_id,
            lease_epoch=lease.lease_epoch,
            expected_state_version=2,
            target=TaskState.VERIFYING,
            reason_code=ReasonCode.VERIFICATION_PENDING,
            idempotency_key=f"same-{task_id}",
        )
        replay = self.control.transition(
            task_id=task_id,
            attempt_id=lease.attempt_id,
            lease_epoch=lease.lease_epoch,
            expected_state_version=2,
            target=TaskState.VERIFYING,
            reason_code=ReasonCode.VERIFICATION_PENDING,
            idempotency_key=f"same-{task_id}",
        )
        self.assertFalse(first.replayed)
        self.assertTrue(replay.replayed)
        with self.assertRaises(IdempotencyConflict):
            self.control.transition(
                task_id=task_id,
                attempt_id=lease.attempt_id,
                lease_epoch=lease.lease_epoch,
                expected_state_version=2,
                target=TaskState.REVIEW,
                reason_code=ReasonCode.REVIEW_PENDING,
                idempotency_key=f"same-{task_id}",
            )

    def test_worker_role_has_no_forbidden_table_privileges_or_mutation_path(self) -> None:
        task_id = self.new_ready_task()
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT has_table_privilege('control_kernel_worker', 'control_kernel.tasks', 'UPDATE'),
                           has_table_privilege('control_kernel_worker', 'control_kernel.audit_events', 'INSERT'),
                           has_table_privilege('control_kernel_worker', 'control_kernel.evidence_records', 'DELETE')
                    """
                )
                self.assertEqual(cursor.fetchone(), (False, False, False))
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET ROLE control_kernel_worker")
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    cursor.execute("UPDATE control_kernel.tasks SET reason_code = 'POLICY_DENIED' WHERE task_id = %s", (task_id,))
                connection.rollback()

    def test_app_append_only_permissions_chain_reconstruction_and_correction_append(self) -> None:
        task_id = self.new_ready_task()
        lease = self.control.claim_task(task_id=task_id, worker_id="evidence-worker", lease_seconds=30)
        audit_hash = hashlib.sha256(f"audit:{task_id}".encode()).hexdigest()
        evidence_hash = hashlib.sha256(f"evidence:{task_id}".encode()).hexdigest()
        correction_hash = hashlib.sha256(f"correction:{task_id}".encode()).hexdigest()
        app = psycopg.connect(self.dsn)
        try:
            with app.cursor() as cursor:
                cursor.execute("SET ROLE control_kernel_app")
                cursor.execute("SELECT last_hash FROM control_kernel.audit_chain_heads WHERE singleton_id = 1")
                previous = cursor.fetchone()[0]
                cursor.execute(
                    """
                    INSERT INTO control_kernel.audit_events
                        (record_hash, event_type, task_id, attempt_id, lease_epoch, payload_json, prev_hash)
                    VALUES (%s, 'LIVE_APPEND', %s, %s, %s, %s::jsonb, %s)
                    """,
                    (audit_hash, task_id, lease.attempt_id, lease.lease_epoch, json.dumps({"source": "live-test"}), previous),
                )
                cursor.execute("UPDATE control_kernel.audit_chain_heads SET last_hash = %s WHERE singleton_id = 1", (audit_hash,))
                cursor.execute(
                    """
                    INSERT INTO control_kernel.evidence_records
                        (record_hash, task_id, attempt_id, lease_epoch, kind, payload_json, prev_hash)
                    VALUES (%s, %s, %s, %s, 'live-test', %s::jsonb, %s)
                    """,
                    (evidence_hash, task_id, lease.attempt_id, lease.lease_epoch, json.dumps({"status": "PASS"}), audit_hash),
                )
                cursor.execute("UPDATE control_kernel.audit_chain_heads SET last_hash = %s WHERE singleton_id = 1", (evidence_hash,))
                app.commit()
        finally:
            app.close()

        for statement, parameter in (
            ("UPDATE control_kernel.audit_events SET event_type = 'MUTATED' WHERE record_hash = %s", audit_hash),
            ("DELETE FROM control_kernel.audit_events WHERE record_hash = %s", audit_hash),
            ("UPDATE control_kernel.evidence_records SET kind = 'MUTATED' WHERE record_hash = %s", evidence_hash),
            ("DELETE FROM control_kernel.evidence_records WHERE record_hash = %s", evidence_hash),
        ):
            denied = psycopg.connect(self.dsn)
            try:
                with denied.cursor() as cursor:
                    cursor.execute("SET ROLE control_kernel_app")
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        cursor.execute(statement, (parameter,))
            finally:
                denied.close()

        with psycopg.connect(self.dsn) as correction:
            with correction.cursor() as cursor:
                cursor.execute("SET ROLE control_kernel_app")
                cursor.execute(
                    """
                    INSERT INTO control_kernel.audit_events
                        (record_hash, event_type, task_id, payload_json, prev_hash)
                    VALUES (%s, 'CORRECTION', %s, %s::jsonb, %s)
                    """,
                    (correction_hash, task_id, json.dumps({"correction_of": audit_hash}), evidence_hash),
                )
                cursor.execute("UPDATE control_kernel.audit_chain_heads SET last_hash = %s WHERE singleton_id = 1", (correction_hash,))
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT record_hash, prev_hash FROM control_kernel.audit_events WHERE record_hash IN (%s, %s) ORDER BY record_hash",
                    (audit_hash, correction_hash),
                )
                rows = cursor.fetchall()
                self.assertEqual(len(rows), 2)
                cursor.execute("SELECT prev_hash FROM control_kernel.evidence_records WHERE record_hash = %s", (evidence_hash,))
                self.assertEqual(cursor.fetchone()[0], audit_hash)
                cursor.execute("SELECT payload_json->>'correction_of' FROM control_kernel.audit_events WHERE record_hash = %s", (correction_hash,))
                self.assertEqual(cursor.fetchone()[0], audit_hash)

    def test_evidence_and_chain_reconstruct_after_reconnect(self) -> None:
        task_id = self.new_ready_task()
        lease = self.control.claim_task(task_id=task_id, worker_id="reconnect-worker", lease_seconds=30)
        record_hash = self.control.append_evidence(
            task_id=task_id,
            attempt_id=lease.attempt_id,
            lease_epoch=lease.lease_epoch,
            kind="reconnect-check",
            payload={"status": "PASS", "source": "live-postgres"},
        )
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM control_kernel.evidence_records WHERE record_hash = %s", (record_hash,))
                self.assertEqual(cursor.fetchone()[0], 1)
                cursor.execute("SELECT last_hash FROM control_kernel.audit_chain_heads WHERE singleton_id = 1")
                head = cursor.fetchone()[0]
                self.assertIsNotNone(head)
        with psycopg.connect(self.dsn) as reconnected:
            with reconnected.cursor() as cursor:
                cursor.execute(
                    "SELECT e.record_hash, e.prev_hash, a.record_hash, a.event_type FROM control_kernel.evidence_records e LEFT JOIN control_kernel.audit_events a ON a.payload_json->'payload'->>'record_hash' = e.record_hash WHERE e.record_hash = %s",
                    (record_hash,),
                )
                evidence_record, previous_hash, audit_record, audit_event_type = cursor.fetchone()
                self.assertEqual(evidence_record, record_hash)
                self.assertIsNotNone(previous_hash)
                self.assertIsNotNone(audit_record)
                self.assertEqual(audit_event_type, "EVIDENCE_APPENDED")


if __name__ == "__main__":
    unittest.main()
