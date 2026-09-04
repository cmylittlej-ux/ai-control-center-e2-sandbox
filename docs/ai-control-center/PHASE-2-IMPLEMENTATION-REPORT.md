# Phase 2 Implementation Report

日期：2026-09-04（Australia/Melbourne）

## Final result

`PHASE_2_BLOCKED`

The bounded local Phase 2 pilot foundations and real disposable PostgreSQL/Git
worktree tests pass, but Phase 2 cannot be accepted. The App Server harness was
corrected to negotiate the pinned runtime's `experimentalApi` capability and
now reaches real `thread/start` and `turn/start` responses. Two bounded Worker
turns nevertheless end with `turn.status=failed` because the isolated Worker
runtime has no bearer/basic authentication; neither produced a Worker commit
or usage event. A fresh independent Reviewer thread accepts the requested
`gpt-5.6-sol` selection, but its turn fails for the same authentication reason.
The existing GitHub credential helper has no usable write credential, so no
Phase 2 PR or GitHub-hosted `authoritative-ci` Run ID exists.

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
Ran 35 tests in 10.716s
OK
```

Breakdown: 15 existing Phase 1 contract tests, 8 existing Phase 1 live
PostgreSQL tests, 7 Phase 2 contract tests, and 5 Phase 2 live pilot tests.
Phase 1 tests were not modified. The final run used the already-authorized
disposable PostgreSQL database with local Unix-socket access. The pinned
runtime contract still proves unsupported runtime/schema input fails closed.
Local tests are not GitHub authoritative CI.

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

### Protocol diagnosis and minimal harness correction

The first bounded probe used `runtimeWorkspaceRoots` without negotiating the
experimental capability. The pinned App Server returned JSON-RPC `-32600`:
`thread/start.runtimeWorkspaceRoots requires experimentalApi capability`.
The Worker client now sends `initialize.params.capabilities.experimentalApi=true`.
This is a protocol compatibility correction, not an architecture change.

The corrected client also treats only `turn.status=completed` as success. A
`turn/completed` notification with `status=failed` now raises
`Phase2PilotError`; failed turns cannot be recorded as successful Worker work.

### Two real bounded Worker turns

The probes used separate disposable worktrees and the isolated temporary state
directory `/private/tmp/aicc-phase2-codex-home-isolated`; no credential file was
copied or printed. Each process was terminated safely after the protocol
outcome, and each binding was supplied as `(task_id, attempt_id=1,
lease_epoch=1, worker_slot)`.

| Worker | Thread ID | Turn ID | protocol outcome | usage events | Git result |
|---|---|---|---|---:|---|
| `worker_slot_1` / `phase2-authorized-worker-1` | `01a06c52-3791-7872-9b86-e9ab299addb0` | `01a06c52-37a4-7f20-bd1b-4fbae4e1b5d8` | `turn/completed`, status `failed` | 0 | no file, no commit |
| `worker_slot_2` / `phase2-authorized-worker-2` | `01a06c52-9594-7242-92fa-32c1ac005940` | `01a06c52-959e-7ef2-9a2d-f0780170c2a2` | `turn/completed`, status `failed` | 0 | no file, no commit |

Observed lifecycle for both was `initialize` response, `remoteControl/status/changed`,
`thread/start`, `thread/started`, `thread/status/changed`, `turn/start`,
`turn/started`, user-message item events, repeated `error` notifications, and
`turn/completed`. With network enabled for diagnosis, stderr identified
`401 Unauthorized` and `Missing bearer or basic authentication in header` for
`wss://api.openai.com/v1/responses`; without the network exception the same
probe failed earlier at DNS/startup. No `thread/tokenUsage/updated` event was
emitted. ChatGPT subscription usage is not classified as API billing cost.

The corrected client was separately exercised against the real failed turn and
returned `failed_closed` with:
`App Server turn ended with non-success status: 'failed'`.

### Independent approved Reviewer attempt

A fresh independent App Server thread was started with the explicitly
requested model `gpt-5.6-sol` and machine-assembled evidence containing the
repository, commit/diff digest, authoritative-ci fields, and frozen acceptance
criteria. App Server echoed `model=gpt-5.6-sol`:

```text
thread_id: 01a06c55-310a-77b1-933b-62f4e6e9d0a2
turn_id:   01a06c55-3144-7823-bd91-42ad48bbd6bf
turn/completed status: failed
usage events: 0
decision: none
```

The Reviewer turn failed with the same 401 authentication error. No Reviewer
decision was accepted, no Worker self-assessment was used, and no local
fixture decision was relabeled as real Sol evidence.

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

Read-only GitHub API verification on 2026-09-04 confirmed that the disposable
repository still has ruleset `22258639`, `E2 Main Protection`, with
`enforcement=active`, targeting `~DEFAULT_BRANCH`. Its visible rules remain
PR-required, required status check `authoritative-ci` with strict/up-to-date
policy, deletion blocked, and non-fast-forward blocked. This did not provide
the missing write credential and made no remote mutation.

The local `IndependentReviewer` enforces fresh context, distinct Worker
identity, machine-assembled evidence, structured `ACCEPT`/`REJECT`/
`HUMAN_REQUIRED`, self-review denial, and fail-closed model substitution. The
local fixture exercised reject then accept. The real App Server Reviewer
selection echoed `gpt-5.6-sol`, but authentication failed before an independent
review decision was produced.

## 7. Acceptance mapping

| Acceptance | Result |
|---|---|
| A/B/C/D/E/F/G local worker, lease, isolation, conflict and drift behaviors | PASS locally |
| H protected workflow policy | PASS locally; GitHub protected-main proof unavailable |
| Real pinned App Server Worker path | BLOCKED: protocol handshake and model thread setup pass, but both turns fail closed at authenticated sampling; no Worker commits or usage events |
| I/J authoritative CI PASS/FAIL gates | BLOCKED: no Phase 2 PR/Run ID |
| K independent approved Reviewer | BLOCKED: `gpt-5.6-sol` selection is accepted, but the fresh real turn fails authentication before a decision |
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
  CI/review/rework/integration/recovery primitives; corrected App Server
  experimental capability negotiation and non-success turn fail-closed handling;
- `migrations/002_phase2_pilot.sql` — Phase 2 slot and evidence metadata/ACLs;
- `tests/test_phase2_contracts.py` — 7 contract tests;
- `tests/test_phase2_integration.py` — 5 real PostgreSQL/Git worktree pilot
  tests and machine evidence output;
- `docs/ai-control-center/PHASE-2-IMPLEMENTATION-REPORT.md` — this report.

Phase 1 architecture documents, Phase 1 migrations, Phase 1 tests, runtime pin,
and E-1/E-2 evidence were not modified.

## 9. Remaining blockers and deferred scope

### Human Bootstrap blockers

1. GitHub write authority is unavailable. The main repository has no remote,
   `gh` is not installed, the configured helper is `osxkeychain`, and the
   credential fill/push probe failed with `could not read Username for
   'https://github.com': Device not configured`. The smallest Human action is
   to authenticate a temporary least-privilege credential for the authorized
   disposable repository. It must allow task-branch push, PR create/read and
   check read while denying administration, workflows, Actions, secrets/
   environments, ruleset/branch-protection changes, force push, and protected
   main bypass. No token was printed, copied, or committed.

2. The authenticated Worker/App Server runtime is unavailable to this process.
   The verified `aicc-worker` account is non-admin and its `.codex/auth.json`
   is mode `600`, unreadable by `mengyaocong`; the isolated probe state had no
   bearer/basic authentication. The smallest Human action is a one-time Codex
   login/authorization in the `aicc-worker` environment, or enabling the
   already-authenticated Worker runtime with its existing credentials. Do not
   copy or disclose `auth.json`; no credential was read or logged. Required
   outbound access to the App Server service must also be available.

3. The approved independent Reviewer cannot produce a real decision until an
   authenticated machine interface is available. The exact requested
   `gpt-5.6-sol` model selection is supported and was echoed by App Server, but
   the fresh review turn failed before inference with 401. No model substitute
   or paid API key was introduced.

After those Human Bootstrap actions complete, automation can continue with the
same fail-closed harness: push the Phase 2 branch, create the PR, collect real
GitHub-hosted PASS/FAIL Run IDs, run two successful bounded Workers, capture
usage where emitted, and obtain a fresh independent Sol review. Until then,
do not call Phase 2 PASS, do not substitute local CI or fixture Reviewer
records, and do not start Phase 3 or excluded product scope.

### Deferred scope

Dashboard UI, Phase 3, production deployment, public API, multi-project
runtime, real business-project execution, unrestricted Director autonomy,
automatic protected-main merge, dynamic model routing, and any scheduler
scaling beyond the bounded two-slot pilot remain deferred.

## 10. Git commit

Phase 2 implementation/evidence baseline commit SHA:
`6cb0c66b669526e1a32d141346c7a1bccef235e4`.

This blocker-resolution pass adds only the App Server protocol negotiation and
non-success turn fail-closed correction in `control_kernel/phase2.py`, plus
this evidence/report update. The scoped correction commit SHA is
`84c273b0007f541cdb66f9bbb75a4ed664001f18`.

## HARD STOP

Do not start Phase 3 automatically. Do not start Dashboard, more than two
Workers, production deployment, multi-project runtime, real business-project
execution, or protected-main automatic merge. Wait for Human Owner review and
the missing bootstrap/authority evidence.
