# Phase 2 Implementation Report

日期：2026-09-04（Australia/Melbourne）

## Final result

`PHASE_2_BLOCKED`

The bounded local Phase 2 pilot foundations and real disposable PostgreSQL/Git
worktree tests pass, but Phase 2 cannot be accepted. A real Codex App Server
initialize handshake passed, while the bounded two-turn App Server execution
probe did not complete and produced no turn completion or usage evidence. The
existing GitHub credential helper has no usable write credential, so no Phase 2
PR or GitHub-hosted `authoritative-ci` Run ID exists. The approved Sol Reviewer
runtime was therefore not exercised as an independent real Reviewer.

This is a fail-closed blocker, not a downgrade of any Phase 1 guarantee. Local
fixture Reviewer and fixture CI records are explicitly not claimed as
authoritative GitHub or production Reviewer evidence.

No Dashboard, more than two Worker slots, production deployment, public API,
multi-project runtime, real business project, unrestricted Director autonomy,
automatic protected-main merge, dynamic model routing, or Phase 3 work was
started.

## Authority and preserved Phase 1 baseline

Phase 2 was explicitly authorized by the Human Owner. The frozen architecture
and Phase 1 guarantees remain authoritative:

- Phase 1 result: `PHASE_1_PASS`;
- PostgreSQL integration evidence commit:
  `ddffc18eeb114d33436dac4c55a484451835aab4`;
- final Phase 1 report commit:
  `0826fe4158ad37da087c9a660e3a0da06b581b1b`;
- Phase 1 documentation finalization commit: `811a728`;
- states remain exactly `BACKLOG`, `READY`, `RUNNING`, `VERIFYING`, `REVIEW`,
  `AWAITING_HUMAN`, `INTEGRATING`, `CLOSED`, `BLOCKED`;
- no `TESTING`, `REWORK`, `READY_TO_INTEGRATE`, `INTEGRATED`, or `DONE` state
  was added;
- PostgreSQL remains authoritative and the Codex runtime/schema pin remains
  fail-closed.

## 1. Scope implemented

The minimum pilot foundations include exactly `worker_slot_1` and
`worker_slot_2`, database-backed slot ownership, maximum concurrency 2,
deterministic task branch/worktree/runtime-directory names, task/attempt/lease/
slot binding, independent heartbeat/process-group handling, explicit-path
hotspot detection, base-SHA drift fencing, deterministic CI failure classes,
structured independent-review protocol, reject/rework, human gate handling,
controlled `phase2/integration`, crash recovery and worktree quarantine, and a
fail-closed pinned App Server v2 client with usage-event capture.

No public API, Dashboard, semantic-lock inference, scheduler scaling, or
protected-main merge path was added.

## 2. Database and migration evidence

Only the disposable local database was used:

```text
PostgreSQL 17.11 (Homebrew) on aarch64-apple-darwin24.6.0
database: aicc_phase1; socket: /tmp; port: 5432
administrative test user: mengyaocong
```

Migration command:

```text
/opt/homebrew/opt/postgresql@17/bin/psql -h /tmp -p 5432 -U mengyaocong -d aicc_phase1 -v ON_ERROR_STOP=1 -f migrations/002_phase2_pilot.sql
```

Result: exit 0, `BEGIN`, `SET`, two slot rows inserted, five Phase 2 metadata
tables created, index created, ACL `REVOKE`/`DO` completed, `COMMIT`.

The migration adds only `phase2_worker_slots`, `phase2_worker_runs`,
`phase2_verifications`, `phase2_reviews`, and `phase2_integrations`. Existing
Phase 1 migration, tables, roles, runtime pin and E-1/E-2 evidence were not
modified or weakened.

## 3. Test commands and exact results

Phase 2 tests:

```text
env PYTHONPATH=/private/tmp/aicc-phase1-psycopg python3 -m unittest discover -s tests -p 'test_phase2_*.py' -v
Ran 12 tests in 8.034s
OK
```

This is 7 Phase 2 contract tests plus 5 real PostgreSQL/Git worktree pilot
tests. Final all-suite command:

```text
env PYTHONPATH=/private/tmp/aicc-phase1-psycopg python3 -m unittest discover -s tests -v
Ran 35 tests in 10.617s
OK
```

Breakdown: 15 existing Phase 1 contract tests, 8 existing Phase 1 live
PostgreSQL tests, 7 Phase 2 contract tests, and 5 Phase 2 live pilot tests.
Phase 1 tests were not modified. Local tests are not GitHub authoritative CI.

## 4. Local machine evidence

### Parallel Workers, double claim, isolation and cap

Final parallel pilot:

| Field | `worker_slot_1` | `worker_slot_2` |
|---|---|---|
| task_id | `phase2-parallel-a-1788522262391772000` | `phase2-parallel-b-1788522262405960000` |
| worker_id | `worker-a` | `worker-b` |
| attempt / epoch | `1 / 1` | `1 / 1` |
| branch | `task/phase2-parallel-a-1788522262391772000/attempt-1` | `task/phase2-parallel-b-1788522262405960000/attempt-1` |
| base_sha | `1a8059e52b57aeb1e6925fb4f37cd5987c7e643d` | same |
| commit_sha | `59eaa655eefe1d5010088bcf60c8cf76d2940b52` | `ec54b1cefb71c1183265fce31ad77ebc32436b51` |
| started_at | `2026-09-04T21:44:22.567141+10:00` | `2026-09-04T21:44:22.567141+10:00` |
| ended_at | `2026-09-04T21:44:23.381910+10:00` | `2026-09-04T21:44:23.375070+10:00` |

The two real subprocesses overlapped, wrote only their own files, used distinct
worktrees, produced separate commits, and recorded `max_concurrency=2`. A
double claim was rejected. Worker A cross-worktree and protected workflow-path
writes were denied by deterministic policy.

### Crash, expiry, base drift and human gate

Crash fixture: `phase2-human-and-recovery-1788522256608849000`; epoch `1`
expired under database time and recovered as attempt `2`, epoch `2`. Its
worktree was quarantined at:

```text
/private/var/folders/zw/q0zm0dks55v6nf87q0ff1d_w0000gn/T/aicc-phase2-pilot-9_a1uhd0/worktrees/worker_slot_1/phase2-human-and-recovery-1788522256608849000/attempt-1.quarantine-5c56f77d5d05
```

Base-drift fixture: `phase2-base-drift-1788522257939709000`; current base
`dcc289cd376b03a99a04d5f71819d119c8d479a5`. Old/current SHA were recorded,
the lease was fenced, the task became `BLOCKED` with `BASE_DRIFT`, and no
integration was created.

Human fixture: `phase2-human-gate-1788522258126385000` entered
`AWAITING_HUMAN`; a transition without approval was denied, and only the
explicit fixture decision `human-decision-fixture-1` moved it to `INTEGRATING`.

### Conflict/hotspot pilot

Two real workers changed explicit path `hotspot.txt`:

```text
tasks: phase2-hotspot-a-1788522259194709000, phase2-hotspot-b-1788522259207813000
commits: 639b8b0284296e19e87c4d476436e9c665ca58cc, 02634f9fc4de077d239e6a1822f4bad4af3c4179
reason_code: GIT_CONFLICT
action: BLOCK_OR_SERIALIZE
```

The pilot asserted no silent overwrite and unchanged fixture `main`. No
semantic lock inference was used.

### CI failure classification and rework

Local deterministic CI failure fixture:

```text
task: phase2-ci-failure-1788522255549297000
commit: 36545281bb6cb43b14fb741b9d5bb0a594184800
run_id: fixture-authoritative-run-failure
check: authoritative-ci; conclusion: failure; failure_class: LINT_FAILURE
state: READY; review_blocked: true
```

Reviewer reject/rework fixture:

```text
task: phase2-review-loop-1788522260314891000
attempt 1 / epoch 1 / worker commit df50e8afc4aae47d5012ed02e08a750316e9decb / REJECT
attempt 2 / epoch 3 / worker commit 5560107d654c24592438aea1acbd210992eb0d78 / ACCEPT
integration branch: phase2/integration
integration commit: 5560107d654c24592438aea1acbd210992eb0d78
```

The old lease was rejected after rework. Both CI identifiers above are local
fixture identifiers, not GitHub Run IDs.

## 5. App Server and usage evidence

Pinned runtime verification remained:

```text
codex-cli 0.153.2
executable SHA-256: 195ace4100a634a9df39147f493e730e666b5bd87795f3c9f3251d8542400424
schema SHA-256:     e5f798fd1343c539f01fedea0e8a84a43c080fcca4615c80eb04a5edab4f7d0a
```

The actual command `/Users/Shared/aicc-phase1-pin/codex-0.153.2 app-server
--stdio` completed JSON-RPC `initialize`, identifying
`Codex Desktop/0.153.2 (Mac OS 15.5.0; arm64) dumb`.

A bounded two-worker `thread/start`/`turn/start` probe did not produce
`turn/completed` within its timeout and was terminated safely. No Phase 2
App Server Worker commit or `thread/tokenUsage/updated` event was claimed. No
ChatGPT subscription usage was labeled as API billing cost.

## 6. GitHub authoritative CI and Reviewer evidence

Authorized sandbox:

```text
https://github.com/cmylittlej-ux/ai-control-center-e2-sandbox
remote main: 99c99b53dc0c05f11e762776690b9304ae9c0622
```

Read-only access succeeded. Local disposable branch/commit:

```text
branch: phase2-pilot-worker-slot-1
commit: 5493352d58d7eac7b0b90a52d90445110d7fe635
```

Actual push failed before a remote branch, PR, or workflow run:

```text
fatal: could not read Username for 'https://github.com': Device not configured
```

`git credential fill` also returned exit 128 with the same denial. The main
repository has no configured GitHub remote and no `gh` CLI. Consequently there
is no Phase 2 PR, GitHub Run ID, authoritative-ci conclusion, runner timestamp,
or authoritative positive/negative gate evidence. Phase 0 E-2 IDs were not
reused as Phase 2 evidence.

The local `IndependentReviewer` enforces fresh context, distinct Worker
identity, machine-assembled evidence, structured `ACCEPT`/`REJECT`/
`HUMAN_REQUIRED`, self-review denial, and fail-closed model substitution. The
local fixture exercised reject then accept, but no actual approved Sol Reviewer
runtime identity or independent App Server review was available.

## 7. Acceptance mapping

| Acceptance | Result |
|---|---|
| A/B/C/D/E/F/G local worker, lease, isolation, conflict and drift behaviors | PASS locally |
| H protected workflow policy | PASS locally; GitHub protected-main proof unavailable |
| I/J authoritative CI PASS/FAIL gates | BLOCKED: no Phase 2 PR/Run ID |
| K independent approved Reviewer | BLOCKED: no real Sol runtime evidence |
| L Worker natural-language done is insufficient | PASS in machine-input protocol |
| M reject/rework/fresh lease path | PASS locally; CI identifiers are fixtures |
| N human gate | PASS locally; explicit fixture approval required |
| O controlled integration provenance | PASS locally on temporary integration branch |
| P full-loop append-only evidence | BLOCKED: authoritative full loop incomplete |
| Q maximum two Worker slots | PASS |
| R Phase 1 regression | PASS, final `35/35 OK` |

No unmet mandatory acceptance criterion was downgraded to a warning.

## 8. Changed files

- `control_kernel/kernel.py` — deterministic lease fencing for drift/safety;
- `control_kernel/phase2.py` — bounded scheduler, worktrees, App Server client,
  CI/review/rework/integration/recovery primitives;
- `migrations/002_phase2_pilot.sql` — Phase 2 slot and evidence metadata/ACLs;
- `tests/test_phase2_contracts.py` — 7 contract tests;
- `tests/test_phase2_integration.py` — 5 real PostgreSQL/Git worktree pilot
  tests and machine evidence output;
- `docs/ai-control-center/PHASE-2-IMPLEMENTATION-REPORT.md` — this report.

Phase 1 architecture documents, Phase 1 migrations, Phase 1 tests, runtime pin,
and E-1/E-2 evidence were not modified.

## 9. Remaining blockers and deferred scope

Human Bootstrap is required for a least-privilege GitHub credential that can
push task branches, open/read PR checks, and cannot modify workflows,
administration, branch protection, evidence or protected main. Phase 2 also
requires real GitHub-hosted PASS and FAIL Run IDs, the approved Sol Reviewer
machine identity/context, and bounded successful App Server Worker turns with
usage events where emitted.

Until those gates are satisfied, do not call Phase 2 PASS, do not substitute
local CI or fixture Reviewer records, and do not start Phase 3 or excluded
product scope.

## 10. Git commit

Phase 2 implementation/evidence commit SHA: `6cb0c66b669526e1a32d141346c7a1bccef235e4`.

## HARD STOP

Do not start Phase 3 automatically. Do not start Dashboard, more than two
Workers, production deployment, multi-project runtime, real business-project
execution, or protected-main automatic merge. Wait for Human Owner review and
the missing bootstrap/authority evidence.
