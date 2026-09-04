# Phase 1 Implementation Report

日期：2026-09-04（Australia/Melbourne）

## Final result

`PHASE_1_PASS`

The scoped Phase 1 minimal Control Kernel has passed its live PostgreSQL
integration gate. The Codex `0.153.2` executable/schema pair is independently
verified and pinned; the exact nine-state model, leases/fencing, deterministic
policy, idempotency, append-only evidence, Worker privilege boundary, and
machine verification handoff are covered by contract tests and real PostgreSQL
tests against the disposable `aicc_phase1` database. The implementation remains
fail-closed for any runtime or schema outside the recorded pin.

This PASS covers the explicitly authorized minimal Control Kernel only. It does
not authorize Phase 2 or any deferred product/operations scope.

No Dashboard, two-Worker scheduler, full Director/Reviewer automation,
multi-project runtime, deployment, production API, or real business project was
started.

## Authority and scope

The Human Owner explicitly authorized Phase 1 only. The implementation was
performed under the frozen documents listed below; `07-SOL-FINAL-ARCHITECTURE-
ARBITRATION.md` remains the priority document where earlier text conflicts:

- `00-CONSTITUTION.md`
- `06-FINAL-ARCHITECTURE-CONVERGENCE.md`
- `07-SOL-FINAL-ARCHITECTURE-ARBITRATION.md`
- revised `01`–`14` architecture documents
- `DECISIONS.md`
- `OPEN-QUESTIONS.md`
- `13-IMPLEMENTATION-ACCEPTANCE.md`

The higher-priority `06-FINAL-ARCHITECTURE-CONVERGENCE.md` and
`07-SOL-FINAL-ARCHITECTURE-ARBITRATION.md` were not modified during this
correction. The affected local frozen lifecycle/provenance documents are listed
below and their post-correction hashes are recorded in Git.

## Focused architecture-compliance correction

The initial Phase 1 implementation exposed a frozen-architecture mismatch: its
domain model and SQL used `TESTING`, `READY_TO_INTEGRATE`, `INTEGRATED`, and
`DONE`. This was corrected before resolving the existing environment blockers.

The authoritative task-state enumeration is now exactly:

```text
BACKLOG, READY, RUNNING, VERIFYING, REVIEW,
AWAITING_HUMAN, INTEGRATING, CLOSED, BLOCKED
```

The correction also makes the following explicit and testable:

- testing, build, lint, and verification details remain evidence/reason/status
  data inside `VERIFYING`;
- a human-required review enters `AWAITING_HUMAN` and cannot transition directly
  to `INTEGRATING` without an explicit human decision;
- integration preparation and completion remain inside `INTEGRATING`, whose
  successful exit is `CLOSED`;
- rework returns to `READY` with `reason_code=REWORK_REQUIRED` and increments
  `attempt_id`; no `REWORK` state is introduced;
- the deprecated task-state strings are rejected by the domain enum and SQL
  state constraint.

Affected local provenance documents were updated only to reconcile this frozen
state-model correction: `03-TASK-LIFECYCLE.md`, `04-ORCHESTRATION-RULES.md`,
`11-DATA-MODEL.md`, and `13-IMPLEMENTATION-ACCEPTANCE.md`.

Post-correction SHA-256 values:

| File | SHA-256 after correction |
|---|---|
| `docs/ai-control-center/03-TASK-LIFECYCLE.md` | `db262089df3855b0c55083aba8fd48e99f1dd2606a6c972a7689372f32fb9fb5` |
| `docs/ai-control-center/04-ORCHESTRATION-RULES.md` | `7c50bdf0ec11df21dbbb13a71a7cec4ed3c8bf47fbd9230a82c20f3ee42a2151` |
| `docs/ai-control-center/11-DATA-MODEL.md` | `f154954fa278fe2c08c57f0c61a1cfe1bf5fe62d13ecf62e7e3e88d2c221a648` |
| `docs/ai-control-center/13-IMPLEMENTATION-ACCEPTANCE.md` | `4e2552a81789a6cfb8dfcd569b645c865efad29c5e8474df62648a5444b2c520` |

The original baseline manifest remains the historical pre-correction record;
these hashes are the authoritative post-correction provenance for this focused
compliance commit.

## 1. Implementation Gate — frozen baseline

The implementation baseline was committed before product code was added:

- Baseline branch: `main`
- Baseline commit: `e78b00b3193c30fa70dba0ba5dc8fd3e397385f2`
- Baseline manifest: `docs/evidence/phase-1/PHASE-1-IMPLEMENTATION-BASELINE.md`
- Baseline manifest records SHA-256 hashes for every governing architecture
  document and Phase 0 evidence input.
- The actual convergence source was included in the baseline with SHA-256
  `923db56b8d50c1ca88e7ca43aaf846a5e3a73ec7d68e24d149d8763b7167fb92`.

The baseline manifest also records that E-1 and E-2 are read-only evidence
inputs. Their evidence was not changed in this phase.

## 2. Codex runtime interface pin

### Required target

- Required Codex CLI/App Server version: `0.153.2`
- Required schema artifact: `runtime/schema/codex_app_server_protocol.v2.schemas.json`
- Runtime pin file: `runtime/codex-app-server-pin.json`
- Unsupported runtime or schema: fail closed

### Observed host

The Human/Worker-provided pinned executable was independently verified from:

```text
/Users/Shared/aicc-phase1-pin/codex-0.153.2 --version
codex-cli 0.153.2
```

Executable SHA-256:

```text
195ace4100a634a9df39147f493e730e666b5bd87795f3c9f3251d8542400424
```

The exact Schema artifact is present at:

```text
runtime/schema/codex_app_server_protocol.v2.schemas.json
```

Schema SHA-256:

```text
e5f798fd1343c539f01fedea0e8a84a43c080fcca4615c80eb04a5edab4f7d0a
```

The Schema was generated directly by `codex-cli 0.153.2` using:

```text
codex app-server generate-json-schema --experimental
```

`runtime/codex-app-server-pin.json` now records the exact executable path and
digest, exact Schema path and digest, generator version, generation command, and
`fail_closed: true`. `RuntimePin.from_json()` and `RuntimePin.validate()` verify
both file digests and reject version, executable, or Schema mismatches.

The 220,551,344-byte executable remains outside the repository and is not
tracked by Git. Only the small pin/provenance metadata and the Schema artifact
are stored in the project.

### Compatibility assumptions recorded in code

The runtime adapter is aligned to the official App Server interface:

- JSON-RPC 2.0 messages over JSONL stdio;
- `initialize` followed by `initialized` handshake;
- version-specific generated schema as the protocol compatibility boundary;
- thread/turn lifecycle as the Worker session boundary;
- usage updates are treated as events, not billing claims.

Reference: [OpenAI Codex App Server documentation](https://learn.chatgpt.com/docs/app-server).

## 3. Implemented minimal Control Kernel

### Authoritative PostgreSQL control plane

`control_kernel/kernel.py` and `migrations/001_control_kernel.sql` provide:

- PostgreSQL-only authority; no SQLite fallback;
- deterministic PostgreSQL advisory lock using `pg_try_advisory_lock`;
- nine states: `BACKLOG`, `READY`, `RUNNING`, `VERIFYING`, `REVIEW`,
  `AWAITING_HUMAN`, `INTEGRATING`, `CLOSED`, `BLOCKED`;
- `task_id`, `attempt_id`, and `lease_epoch` fencing fields;
- lease claim, heartbeat, expiry, and timeout recovery;
- database `clock_timestamp()` for authoritative timestamps;
- row locking and version/fence predicates for state transitions;
- idempotency request hashes and replay receipts;
- append-only audit and evidence tables with hash chaining;
- database triggers rejecting normal UPDATE/DELETE of audit/evidence records;
- no `PUBLIC` direct privileges for the control-plane tables;
- explicit revocation of all control-plane privileges from the Worker database
  role, when that role exists.

### Deterministic policy

`control_kernel/policy.py` provides non-LLM decisions for:

- worktree containment;
- protected governance, policy, control-plane, and workflow paths;
- rejection of Worker authoritative state writes;
- exact runtime-version and schema-digest matching.

### One Worker execution path

`control_kernel/worker.py` provides one isolated App Server session binding:

```text
(task_id, attempt_id, lease_epoch)
```

The binding cannot accept events for another task/attempt/epoch, uses a single
worktree root, rejects protected writes, and has no database-authoritative write
capability. Session pooling, cross-task reuse, and multi-worker scheduling were
not added.

### Minimal verification handoff

`control_kernel/verification.py` produces canonical machine-readable handoff
input containing the project, task, attempt, lease, branch, base SHA, commit
SHA, diff digest, acceptance contract, GitHub-hosted provider, and required
`authoritative-ci` check. GitHub-hosted CI remains the external authority; no
Reviewer automation was added.

## 4. Phase 1 contract test evidence

Command:

```text
python3 -m unittest discover -s tests -v
```

Result:

```text
Ran 15 tests in 0.213s
OK
```

The contract suite covers:

- only one orchestrator owner in the reference model and advisory-lock SQL;
- stale lease/fence rejection;
- expired lease returning to `READY` and incrementing the next attempt;
- exact nine-state enumeration and deprecated-state rejection;
- valid `VERIFYING` transitions and `INTEGRATING -> CLOSED`;
- mandatory `AWAITING_HUMAN` gate for human-required approval;
- rework returning to `READY` with an incremented attempt;
- duplicate event replay and conflicting idempotency-key rejection;
- Worker authoritative-state denial;
- invalid state-transition rejection;
- append-only audit/evidence trigger and ACL contract;
- unsupported version, executable, and Schema fail-closed behavior;
- one-task/attempt/epoch Worker session binding and protected-path denial;
- machine-generated verification handoff with external CI authority.

Additional checks:

- `python3 -m compileall -q control_kernel tests` passed with a temporary
  `PYTHONPYCACHEPREFIX` because the host Python cache location is sandboxed;
- `git diff --check` passed;
- no Ruff or mypy executable is installed, so those optional checks were not
  claimed.

These are source/contract tests. The separate live PostgreSQL evidence is
recorded below.

## 5. Live PostgreSQL integration evidence

### PostgreSQL

The disposable local integration environment was verified with:

```text
/opt/homebrew/opt/postgresql@17/bin/pg_isready -h /tmp -p 5432
/tmp:5432 - accepting connections

/opt/homebrew/opt/postgresql@17/bin/psql -h /tmp -p 5432 -U mengyaocong -d aicc_phase1 -At -v ON_ERROR_STOP=1 -c "SELECT current_database(), current_user, version();"
aicc_phase1|mengyaocong|PostgreSQL 17.11 (Homebrew) on aarch64-apple-darwin24.6.0, compiled by Apple clang version 17.0.0 (clang-1700.6.4.2), 64-bit
```

Migration was applied to the clean disposable database with:

```text
/opt/homebrew/opt/postgresql@17/bin/psql -h /tmp -p 5432 -U mengyaocong -d aicc_phase1 -v ON_ERROR_STOP=1 -f migrations/001_control_kernel.sql
BEGIN
CREATE SCHEMA
CREATE TABLE ...
CREATE INDEX
CREATE FUNCTION
CREATE TRIGGER
REVOKE
DO
COMMIT
```

The command exited 0 and committed successfully. The migration's `tasks.state`
constraint contains exactly the frozen nine states and rejects `TESTING`.

Only disposable Phase 1 roles were created:

```sql
CREATE ROLE control_kernel_app NOLOGIN;
CREATE ROLE control_kernel_worker NOLOGIN;
GRANT USAGE ON SCHEMA control_kernel TO control_kernel_app, control_kernel_worker;
GRANT SELECT, INSERT, UPDATE ON control_kernel.tasks,
  control_kernel.executions, control_kernel.idempotency_keys TO control_kernel_app;
GRANT SELECT, INSERT ON control_kernel.audit_events,
  control_kernel.evidence_records TO control_kernel_app;
GRANT SELECT, UPDATE ON control_kernel.audit_chain_heads TO control_kernel_app;
REVOKE ALL ON control_kernel.tasks, control_kernel.executions,
  control_kernel.idempotency_keys, control_kernel.audit_chain_heads,
  control_kernel.audit_events, control_kernel.evidence_records
  FROM control_kernel_worker;
```

Final read-only role checks returned:

```text
control_kernel_app|f
control_kernel_worker|f
app INSERT audit_events = true
app UPDATE audit_events = false
worker UPDATE tasks = false
```

### Integration test evidence

Live tests used psycopg from the temporary verification dependency directory
`/private/tmp/aicc-phase1-psycopg`; no project or system PostgreSQL dependency
was installed. Exact command:

```text
env PYTHONPATH=/private/tmp/aicc-phase1-psycopg python3 -m unittest discover -s tests -p 'test_postgres_integration.py' -v
```

Result:

```text
Ran 8 tests in 2.490s
OK
```

The eight real database tests provide the following evidence:

| Acceptance behavior | Result | Machine evidence |
|---|---|---|
| A. Clean migration and exact nine-state schema | PASS | `test_migration_constraints_match_exact_frozen_nine_states`; migration `COMMIT` on `aicc_phase1` |
| B. Single orchestrator ownership | PASS | `test_two_independent_sessions_allow_only_one_advisory_lock_owner`; two independent sessions observed `true`, `false`, then `true` after release |
| C. Lease/fencing and DB time | PASS | `test_real_lease_fencing_db_time_and_expiry_increment`; stale epoch update affected 0 rows, DB expiry was after DB clock, heartbeat rejected after expiry, recovery moved to `READY`, attempt `1 -> 2`, epoch `1 -> 2` |
| D. Transactions/concurrency | PASS | `test_transaction_rollback_row_lock_and_conflicting_transition`; rollback left 0 rows, real `FOR UPDATE` contention raised `LockNotAvailable`, one of two conflicting transitions was fenced |
| E. Idempotency | PASS | `test_idempotent_replay_and_conflicting_payload_are_rejected`; same payload replayed, conflicting payload raised `IdempotencyConflict` |
| F. Worker DB isolation | PASS | `test_worker_role_has_no_forbidden_table_privileges_or_mutation_path`; Worker UPDATE attempt raised `InsufficientPrivilege` and forbidden privileges were false |
| G. Append-only audit/evidence | PASS | `test_app_append_only_permissions_chain_reconstruction_and_correction_append`; append succeeded, UPDATE/DELETE denied, chain links reconstructed, correction used a new append record |
| H. Reconnect reconstruction | PASS | `test_evidence_and_chain_reconstruct_after_reconnect`; evidence and its `EVIDENCE_APPENDED` audit record were read after reconnect |

The combined exact command was also run:

```text
env PYTHONPATH=/private/tmp/aicc-phase1-psycopg python3 -m unittest discover -s tests -v
```

Combined result: `Ran 23 tests in 2.634s` / `OK` (`15` contract tests plus
`8` live PostgreSQL integration tests). No simulated test was counted as live
PostgreSQL evidence.

The code contains no SQLite substitute for these checks.

## 6. Architecture compliance mapping

| Frozen requirement | Phase 1 result |
|---|---|
| PostgreSQL authoritative state | Implemented in adapter and migration; live migration and schema checks PASS on `aicc_phase1` |
| Single orchestrator ownership | Advisory-lock implementation; two-session live contention PASS |
| Exact nine-state model | Corrected to `BACKLOG`, `READY`, `RUNNING`, `VERIFYING`, `REVIEW`, `AWAITING_HUMAN`, `INTEGRATING`, `CLOSED`, `BLOCKED`; contract-tested |
| IDs, leases, heartbeat, fencing, expiry | Implemented in PostgreSQL operations; live stale-epoch, DB-time, expiry, and attempt increment checks PASS |
| DB authoritative time | `clock_timestamp()` used in schema and operations; live expiry comparison PASS |
| Idempotent transitions | Request hash, replay, conflict path; live duplicate/conflict checks PASS |
| Append-only audit/evidence | Hash-chain schema, triggers, ACLs, correction append, and reconnect reconstruction; live checks PASS |
| Deterministic policy | Pure code; Worker state writes and protected paths denied and tested |
| Human Bootstrap/Worker separation | Worker session has no authoritative DB path; actual disposable Worker role mutation and privilege checks PASS |
| One App Server Worker path | Binding and fail-closed runtime gate implemented; exact executable and Schema pin verified; Phase 0 real App Server Turn evidence retained |
| Machine verification handoff | Implemented and tested; authoritative GitHub run not started in this phase |
| No formal Dashboard/product scope | Satisfied |

No requirement was weakened to obtain a test result.

## 7. Changed files in the implementation commit

The final implementation commit is recorded below after the report was
finalized. Files added after the frozen baseline are:

- `README.md`
- `control_kernel/__init__.py`
- `control_kernel/domain.py`
- `control_kernel/errors.py`
- `control_kernel/kernel.py`
- `control_kernel/policy.py`
- `control_kernel/postgres.py`
- `control_kernel/runtime.py`
- `control_kernel/verification.py`
- `control_kernel/worker.py`
- `migrations/001_control_kernel.sql`
- `pyproject.toml`
- `runtime/codex-app-server-pin.json`
- `runtime/pinned/CODEX-BINARY-SHA256.txt`
- `runtime/pinned/CODEX-VERSION.txt`
- `runtime/pinned/SCHEMA-SHA256.txt`
- `runtime/schema/codex_app_server_protocol.v2.schemas.json`
- `tests/test_phase1_contracts.py`
- `tests/test_postgres_integration.py`
- `docs/ai-control-center/PHASE-1-IMPLEMENTATION-REPORT.md`

The PostgreSQL live-gate correction also changed:

- `control_kernel/postgres.py` — initialize the PostgreSQL adapter session
  search path to the authoritative `control_kernel` schema;
- `tests/test_postgres_integration.py` — real eight-test disposable database
  suite and corrected nested audit-payload reconstruction assertion.

The state-model correction also changed these frozen local provenance documents:

- `docs/ai-control-center/03-TASK-LIFECYCLE.md`
- `docs/ai-control-center/04-ORCHESTRATION-RULES.md`
- `docs/ai-control-center/11-DATA-MODEL.md`
- `docs/ai-control-center/13-IMPLEMENTATION-ACCEPTANCE.md`

Implementation commit SHA: `b65fb46` (`b65fb46c06fbf65a9a5a292849969ea47fe2fdb9`).
The live PostgreSQL integration and adapter correction are recorded in the
final commit listed at the end of this report.

State-model correction commit SHA: `8409e9106c48c8a84d98ae2f1f56fdb8b81b15a3`.
The report was finalized in the immediately following documentation-only
commit.

Runtime pin evidence update commit SHA: `a9e89af` (`a9e89af3a15490f5251be07a3d7df0bf952cd1c2`).

Phase 1 PostgreSQL integration evidence commit SHA: `ddffc18eeb114d33436dac4c55a484451835aab4`.
The report-only finalization commit follows this evidence commit.

## 8. Known limitations and Phase 2 deferrals

No remaining blocker exists for the explicitly scoped Phase 1 minimal Control
Kernel acceptance. The following are intentionally deferred and require
separate authorization where applicable:

- full Director and Reviewer automation;
- two-Worker parallel orchestration and conflict/base-drift pilot;
- Dashboard UI;
- multi-project runtime and production API;
- deployment and public remote access;
- real business project execution;
- dynamic model routing and AI ETA;
- production backup/restore operations, Kill Switch operations, and broader
  operational automation beyond this kernel proof. The required disposable
  transaction/reconnect evidence reconstruction gate passed in this phase.

## HARD STOP

Do not start Phase 2 automatically. Do not start Dashboard, Orchestrator
expansion, database/control-plane expansion, multi-agent runtime, deployment,
production code, or real business project execution from this report.
