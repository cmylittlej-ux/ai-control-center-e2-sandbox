# Phase 0 Feasibility Report

日期：2026-09-04（Australia/Melbourne）

## Status

`PASS`

E-1 and E-2 satisfy their frozen acceptance criteria. The actual 06 convergence source is now present, has been read in full, and is consistent with the 07/08 provenance requirements. Product implementation remains not started and is not authorized by this report.

## Scope and authority

- 07 is the final architecture arbitration and has priority over conflicting earlier architecture text.
- 08 is the only execution authorization for this run.
- 09 is future roadmap reference only and was not implemented.
- This report records feasibility evidence only. It does not authorize Dashboard, Orchestrator, database/control-plane, multi-agent runtime, or product implementation.

## Architecture Freeze and official alignment

- Freeze revision：现有 `docs/ai-control-center/` 文档已按 07 仲裁和 08 范围修订。
- Upstream delta：[`UPSTREAM-SYMPHONY-DELTA.md`](UPSTREAM-SYMPHONY-DELTA.md) records the official OpenAI Symphony primitives and the hardened Control Center extensions, marked `REUSE`/`EXTEND` rather than silently reimplementing upstream behavior.
- Symphony alignment：采用 [OpenAI Symphony](https://github.com/openai/symphony) 的适用 scheduler/runner/workspace/retry/concurrency/state/recovery/tracker/observability primitives；Control Center retains explicit transactional state, leases/fencing, policy gates, independent verification, evidence, cost semantics, and human authority.
- Codex runtime alignment：采用 [Codex App Server official documentation](https://learn.chatgpt.com/docs/app-server) 的 JSON-RPC/JSONL transport, `initialize`/`initialized`, Thread/Turn/Item lifecycle, bidirectional approvals, generated version-specific schema, and usage events. App Server is the preferred machine interface; Codex Desktop is not the control protocol.
- Actual convergence source：`docs/ai-control-center/06-FINAL-ARCHITECTURE-CONVERGENCE.md` is present and was read in full (702 lines; SHA-256 `923db56b8d50c1ca88e7ca43aaf846a5e3a73ec7d68e24d149d8763b7167fb92`). Its title is `Architecture Review #2C — Final Convergence & Freeze Recommendation`; it contains the seven-layer architecture, 11 P0 Capabilities, V1 two Worker slots, GitHub-hosted ephemeral verification, E-1/E-2 pre-autonomy experiments, and `NO IMPLEMENTATION. HARD STOP.`
- Provenance consistency：07 explicitly accepts `06-FINAL-ARCHITECTURE-CONVERGENCE.md` and its 11 P0 Capabilities, while 08 explicitly requires the file to be read and included. The source is now in the local read order; 07 remains higher priority if any earlier text conflicts. OQ-006 is cleared.
- Architecture contradictions：no new contradiction was introduced, and no architecture requirement was weakened to obtain E-1/E-2 PASS.

## E-1 — Restricted Worker Runtime

### Result

`PASS`

The verified Human Bootstrap evidence satisfies the frozen E-1 acceptance criteria.

### Environment evidence

| Control | Verified result |
|---|---|
| Dedicated identity | macOS Standard User `aicc-worker` |
| Administrative authority | `aicc-worker` is not a member of the admin group |
| Worker home | `/Users/aicc-worker` |
| AICC root mode | `700` |
| Main-user SSH access | denied |
| Main-user Keychains access | denied |
| Main-user Chrome profile access | denied |
| Worker pre-existing secret/config state | no pre-existing `~/.ssh`, `~/.npmrc`, API/token environment variables |
| Worker write outside repository | denied |
| Main-user directory write | denied |
| Main-user `.ssh` read | denied |
| Main-user Keychains read | denied |
| Shell-tool outbound network | denied during probe |

### Codex/App Server evidence

- Codex CLI: `0.153.2`.
- Codex App Server: available and operational.
- A real App Server Turn completed successfully.
- The disposable fixture was modified only in the expected repository file.
- The fixture test passed.
- No main-user secret values or token values were copied into evidence.

### Live structured usage evidence

The real App Server Turn emitted `thread/tokenUsage/updated`. The observed payload made the following fields available:

- `inputTokens`
- `cachedInputTokens`
- `outputTokens`
- `reasoningOutputTokens`
- `totalTokens`
- `modelContextWindow` — observed value `258400`

`AccountRateLimitsUpdated` was also observed. The account evidence reported `plan_type: Plus` and available primary and secondary rate-limit windows.

These usage values are ChatGPT subscription/runtime usage evidence. They are not API billing charges. The frozen billing semantics remain unchanged: only `api_billed` with provider-confirmed usage and a versioned rate card may be labeled API actual cost; `chatgpt_subscription` may show Token plus an explicitly labeled API-equivalent estimate; unavailable values remain unavailable.

### E-1 evidence index

- [`E1-environment.md`](../evidence/phase-0-feasibility/E1-environment.md)
- [`E1-policy-results.md`](../evidence/phase-0-feasibility/E1-policy-results.md)
- [`E1-runtime-events.jsonl`](../evidence/phase-0-feasibility/E1-runtime-events.jsonl)
- [`E1-human-bootstrap-request.md`](../evidence/phase-0-feasibility/E1-human-bootstrap-request.md)
- [`CODEX-USAGE-CAPABILITY.md`](CODEX-USAGE-CAPABILITY.md)

## E-2 — Independent Authoritative Verification

### Result

`PASS`

The verified disposable GitHub evidence satisfies the frozen E-2 acceptance criteria without replacing GitHub-hosted authority with a local runner.

### Authoritative repository and workflow

- Repository: [`cmylittlej-ux/ai-control-center-e2-sandbox`](https://github.com/cmylittlej-ux/ai-control-center-e2-sandbox)
- Workflow: `.github/workflows/e2-authoritative.yml`
- Required check: `authoritative-ci`
- Ruleset: `E2 Main Protection`
- PR: `#1 — E2 Worker Authoritative CI Probe`

### Ruleset and credential boundary

Verified rules:

- enforcement active;
- target is the default branch;
- pull request required;
- required status check `authoritative-ci`;
- branch must be up to date;
- deletion blocked;
- non-fast-forward/force push blocked;
- no bypass.

Worker credential: temporary fine-grained PAT restricted only to this disposable repository.

Worker permissions:

- Contents: Read/Write
- Pull Requests: Read/Write
- Metadata: Read
- no Administration
- no Workflows write
- no Actions write
- no Secrets/Environment administration

### Permission attack evidence

| Attempt | Verified result |
|---|---|
| Worker task-branch push | PASS / allowed |
| PR creation | PASS / allowed |
| Direct main push | denied |
| Force push to main | denied |
| Ruleset create/modify | HTTP 403 |
| Actions Run deletion | HTTP 403 |
| Workflow modification push | rejected: `refusing to allow a Personal Access Token to create or update workflow .github/workflows/e2-authoritative.yml without workflow scope` |

### Authoritative CI evidence

- 20 authoritative GitHub-hosted `pull_request` workflow runs completed successfully before the intentional failure probe: `20/20 PASS`.
- Latest successful head before failure: `e796615093ab139f1c832b80f92f4abb0a1cca16`.
- Example/latest successful Run ID: `33856286499`.
- Intentional failure commit: `ef1fe9407acc1514fa484e2d14fea4cf19f6523c`.
- Authoritative failure Run ID: `33856752481`.
- Failure result: `failure`.
- Worker merge attempt: HTTP `405`, `Repository rule violations found Required status check "authoritative-ci" is failing.`
- PR remained open; `merged=false`.
- Main SHA remained unchanged: `99c99b53dc0c05f11e762776690b9304ae9c0622`.

### E-2 evidence index

- [`E2-runs-summary.md`](../evidence/phase-0-feasibility/E2-runs-summary.md)
- [`E2-permissions.md`](../evidence/phase-0-feasibility/E2-permissions.md)
- [`E2-run-ids.md`](../evidence/phase-0-feasibility/E2-run-ids.md)

## Re-evaluation of remaining Phase 0 P0 blockers

| Item | Result | Current conclusion |
|---|---|---|
| E-1 restricted Worker runtime | PASS | Cleared; dedicated low-privilege identity, boundary denials, real App Server Turn, fixture test, and structured usage evidence verified. |
| E-2 independent authoritative verification | PASS | Cleared; 20 successful authoritative runs, negative gate failure, permission denials, and unchanged main SHA verified. |
| Usage fields | PASS for required Phase 0 capability | Required live token fields and context window were observed. Per-turn resolved model ID/version is not claimed where not supplied; raw runtime evidence remains authoritative. |
| Billing semantics | PASS for Phase 0 classification | `plan_type: Plus` and ChatGPT subscription usage do not become API billing cost. Frozen `api_billed`/`chatgpt_subscription`/`unknown` semantics remain unchanged. |
| App Server build pin | Phase 1 control, not a Phase 0 feasibility blocker | Verified runtime is Codex CLI/App Server `0.153.2`; Phase 1 must pin the executable/schema artifact before implementation. |
| 06 convergence source | PASS | Required file is present, fully read, hash-recorded, consistent with 07/08, and OQ-006 is cleared. |
| Product implementation | NOT STARTED | No Dashboard, Orchestrator, database/control plane, multi-agent runtime, API, deployment, automation, or real business project work was performed. |

All remaining Phase 0 P0 blockers are cleared: E-1 PASS, E-2 PASS, usage/billing semantics recorded without weakening, and OQ-006 provenance verified and closed.

## Product Implementation

`NOT STARTED`

This report does not authorize implementation. Phase 1 requires explicit Human Owner approval under the frozen governance documents and its Implementation Gate.

## Recommendation

`READY_FOR_IMPLEMENTATION_PHASE_1`

Reason: E-1, E-2, and the required local architecture provenance checks all PASS. This is readiness only; implementation still requires the frozen Implementation Gate and explicit Human Owner approval.

## Frozen documents governing Phase 1

Phase 1, when explicitly authorized, is governed by `00-CONSTITUTION.md`, the actual `06-FINAL-ARCHITECTURE-CONVERGENCE.md`, `07-SOL-FINAL-ARCHITECTURE-ARBITRATION.md` (higher priority for conflicts), the revised `01`–`14` architecture documents, `DECISIONS.md`, `OPEN-QUESTIONS.md`, and `13-IMPLEMENTATION-ACCEPTANCE.md`. The 09 roadmap remains reference-only until separately authorized.

## Git and evidence integrity

- Parent branch：`main`
- Parent commits：none yet; this workspace started without commits
- Disposable fixture commits：`5f474add441eca4511ed80d69635b537f6f548a4`、`c5a36e9`
- Parent workspace：uncommitted documentation/evidence additions; no product code
- Fixture repository：clean
- Evidence includes exact repository, PR, Run IDs, SHAs, denial results, App Server usage fields, and redacted runtime observations listed above.
- Local convergence provenance: 06 file present, 702 lines, SHA-256 `923db56b8d50c1ca88e7ca43aaf846a5e3a73ec7d68e24d149d8763b7167fb92`.

## HARD STOP

本报告完成后停止。不得写正式 Orchestrator、Dashboard、多 Agent runtime、正式 DB schema、生产 API、部署或自动化；不得访问真实业务 Project。等待 Human Owner 按冻结 Implementation Gate 明确授权；本轮不进入实现。
