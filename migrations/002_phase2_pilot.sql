-- Phase 2 disposable pilot metadata. PostgreSQL remains the sole authority.
BEGIN;

SET LOCAL search_path = control_kernel, public;

CREATE TABLE IF NOT EXISTS phase2_worker_slots (
    slot_name TEXT PRIMARY KEY CHECK (slot_name IN ('worker_slot_1', 'worker_slot_2')),
    active_task_id TEXT REFERENCES tasks(task_id),
    attempt_id BIGINT,
    lease_epoch BIGINT,
    branch TEXT,
    worktree TEXT,
    runtime_dir TEXT,
    acquired_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ
);

INSERT INTO phase2_worker_slots(slot_name) VALUES
    ('worker_slot_1'), ('worker_slot_2')
ON CONFLICT (slot_name) DO NOTHING;

CREATE TABLE IF NOT EXISTS phase2_worker_runs (
    run_id UUID PRIMARY KEY,
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    attempt_id BIGINT NOT NULL,
    lease_epoch BIGINT NOT NULL,
    worker_slot TEXT NOT NULL CHECK (worker_slot IN ('worker_slot_1', 'worker_slot_2')),
    worker_id TEXT NOT NULL,
    branch TEXT NOT NULL,
    worktree TEXT NOT NULL,
    runtime_dir TEXT NOT NULL,
    base_sha TEXT NOT NULL,
    commit_sha TEXT,
    process_group_id BIGINT,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    exit_code INTEGER,
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED', 'EXPIRED', 'QUARANTINED'))
);

CREATE INDEX IF NOT EXISTS phase2_worker_runs_task_idx
    ON phase2_worker_runs(task_id, attempt_id, lease_epoch);

CREATE TABLE IF NOT EXISTS phase2_verifications (
    verification_id UUID PRIMARY KEY,
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    attempt_id BIGINT NOT NULL,
    lease_epoch BIGINT NOT NULL,
    repository TEXT NOT NULL,
    branch TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    pull_request_number BIGINT,
    run_id TEXT,
    check_name TEXT NOT NULL,
    conclusion TEXT NOT NULL,
    failure_class TEXT,
    runner_environment TEXT NOT NULL,
    artifact_digest TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    evidence_json JSONB NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (failure_class IS NULL OR failure_class IN (
        'TEST_FAILURE', 'BUILD_FAILURE', 'LINT_FAILURE', 'POLICY_FAILURE',
        'INFRA_FAILURE', 'TIMEOUT', 'CANCELLED'
    ))
);

CREATE TABLE IF NOT EXISTS phase2_reviews (
    review_id UUID PRIMARY KEY,
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    attempt_id BIGINT NOT NULL,
    lease_epoch BIGINT NOT NULL,
    worker_id TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    reviewer_model TEXT NOT NULL,
    reviewer_context_id TEXT NOT NULL,
    input_digest TEXT NOT NULL,
    reviewed_diff_hash TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('ACCEPT', 'REJECT', 'HUMAN_REQUIRED')),
    reason_codes JSONB NOT NULL,
    evidence_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (worker_id <> reviewer_id)
);

CREATE TABLE IF NOT EXISTS phase2_integrations (
    integration_id UUID PRIMARY KEY,
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL UNIQUE REFERENCES tasks(task_id),
    attempt_id BIGINT NOT NULL,
    lease_epoch BIGINT NOT NULL,
    integration_branch TEXT NOT NULL,
    base_sha TEXT NOT NULL,
    source_task_commit_sha TEXT NOT NULL,
    verified_commit_sha TEXT NOT NULL,
    reviewer_decision TEXT NOT NULL CHECK (reviewer_decision = 'ACCEPT'),
    integration_commit_sha TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

REVOKE ALL ON phase2_worker_slots, phase2_worker_runs, phase2_verifications,
    phase2_reviews, phase2_integrations FROM PUBLIC;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'control_kernel_app') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE ON control_kernel.phase2_worker_slots TO control_kernel_app';
        EXECUTE 'GRANT SELECT, INSERT, UPDATE ON control_kernel.phase2_worker_runs TO control_kernel_app';
        EXECUTE 'GRANT SELECT, INSERT ON control_kernel.phase2_verifications TO control_kernel_app';
        EXECUTE 'GRANT SELECT, INSERT ON control_kernel.phase2_reviews TO control_kernel_app';
        EXECUTE 'GRANT SELECT, INSERT ON control_kernel.phase2_integrations TO control_kernel_app';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'control_kernel_worker') THEN
        EXECUTE 'REVOKE ALL ON control_kernel.phase2_worker_slots, control_kernel.phase2_worker_runs, control_kernel.phase2_verifications, control_kernel.phase2_reviews, control_kernel.phase2_integrations FROM control_kernel_worker';
    END IF;
END;
$$;

COMMIT;
