-- Phase 1 Control Kernel authoritative PostgreSQL schema.
-- No SQLite fallback is permitted.
BEGIN;

CREATE SCHEMA IF NOT EXISTS control_kernel;
SET LOCAL search_path = control_kernel, public;

CREATE TABLE IF NOT EXISTS tasks (
    project_id TEXT NOT NULL,
    task_id TEXT PRIMARY KEY,
    state TEXT NOT NULL CHECK (state IN (
        'BACKLOG', 'READY', 'RUNNING', 'TESTING', 'REVIEW',
        'READY_TO_INTEGRATE', 'INTEGRATED', 'DONE', 'BLOCKED'
    )),
    reason_code TEXT NOT NULL CHECK (reason_code IN (
        'UNPLANNED', 'DEPENDENCY_PENDING', 'AWAITING_ASSIGNMENT', 'IMPLEMENTING',
        'REWORK_REQUIRED', 'TEST_FAILURE', 'REVIEW_PENDING', 'REVIEW_FAILURE',
        'VERIFICATION_PENDING', 'HUMAN_APPROVAL_REQUIRED', 'POLICY_DENIED',
        'BUDGET_WARNING', 'BUDGET_HARD_LIMIT', 'RUNTIME_CRASH', 'TIMEOUT',
        'STALL', 'GIT_CONFLICT', 'BASE_DRIFT', 'CANCELLED', 'ROLLED_BACK',
        'NO_PROGRESS', 'EVIDENCE_MISSING', 'NONE'
    )),
    state_version BIGINT NOT NULL DEFAULT 0 CHECK (state_version >= 0),
    current_attempt_id BIGINT NOT NULL DEFAULT 0 CHECK (current_attempt_id >= 0),
    lease_epoch BIGINT NOT NULL DEFAULT 0 CHECK (lease_epoch >= 0),
    branch TEXT NOT NULL,
    acceptance_contract JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS executions (
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    attempt_id BIGINT NOT NULL CHECK (attempt_id > 0),
    lease_epoch BIGINT NOT NULL CHECK (lease_epoch > 0),
    worker_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'EXPIRED', 'RELEASED')),
    lease_expires_at TIMESTAMPTZ NOT NULL,
    heartbeat_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    PRIMARY KEY (task_id, attempt_id),
    UNIQUE (task_id, lease_epoch)
);

CREATE UNIQUE INDEX IF NOT EXISTS one_active_execution_per_task
    ON executions(task_id) WHERE status = 'ACTIVE';

CREATE TABLE IF NOT EXISTS idempotency_keys (
    scope TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (scope, idempotency_key)
);

CREATE TABLE IF NOT EXISTS audit_chain_heads (
    singleton_id SMALLINT PRIMARY KEY CHECK (singleton_id = 1),
    last_hash TEXT
);
INSERT INTO audit_chain_heads(singleton_id, last_hash) VALUES (1, NULL)
    ON CONFLICT (singleton_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS audit_events (
    record_hash TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    task_id TEXT NOT NULL,
    attempt_id BIGINT,
    lease_epoch BIGINT,
    payload_json JSONB NOT NULL,
    prev_hash TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS evidence_records (
    record_hash TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    attempt_id BIGINT NOT NULL,
    lease_epoch BIGINT NOT NULL,
    kind TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    prev_hash TEXT,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE OR REPLACE FUNCTION control_kernel.reject_append_only_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'append-only record cannot be updated or deleted';
END;
$$;

DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events;
CREATE TRIGGER audit_events_append_only
    BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION control_kernel.reject_append_only_mutation();

DROP TRIGGER IF EXISTS evidence_records_append_only ON evidence_records;
CREATE TRIGGER evidence_records_append_only
    BEFORE UPDATE OR DELETE ON evidence_records
    FOR EACH ROW EXECUTE FUNCTION control_kernel.reject_append_only_mutation();

-- No role receives a public direct-write path.  The application role is granted
-- only the narrow privileges needed by the Control Plane below.
REVOKE ALL ON tasks, executions, idempotency_keys, audit_chain_heads, audit_events, evidence_records FROM PUBLIC;
REVOKE UPDATE, DELETE, TRUNCATE ON audit_events, evidence_records FROM PUBLIC;
REVOKE UPDATE, DELETE, TRUNCATE ON audit_chain_heads FROM PUBLIC;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'control_kernel_app') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE ON control_kernel.tasks, control_kernel.executions, control_kernel.idempotency_keys TO control_kernel_app';
        EXECUTE 'REVOKE UPDATE, DELETE, TRUNCATE ON control_kernel.audit_events, control_kernel.evidence_records FROM control_kernel_app';
        EXECUTE 'GRANT SELECT, INSERT ON control_kernel.audit_events, control_kernel.evidence_records TO control_kernel_app';
        EXECUTE 'GRANT SELECT, UPDATE ON control_kernel.audit_chain_heads TO control_kernel_app';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'control_kernel_worker') THEN
        EXECUTE 'REVOKE ALL ON control_kernel.tasks, control_kernel.executions, control_kernel.idempotency_keys, control_kernel.audit_chain_heads, control_kernel.audit_events, control_kernel.evidence_records FROM control_kernel_worker';
    END IF;
END;
$$;

COMMIT;
