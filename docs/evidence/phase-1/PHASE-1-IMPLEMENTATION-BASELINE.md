# Phase 1 Implementation Baseline

Captured before Phase 1 product code. This manifest records the frozen architecture and Phase 0 evidence inputs used by the Control Kernel implementation. The baseline commit SHA is recorded in `PHASE-1-IMPLEMENTATION-REPORT.md` after the commit is created.

## Scope

- Human Owner authorization: Phase 1 only.
- Product code at capture: not started.
- Dashboard, multi-agent runtime, production deployment, and real business projects: out of scope.
- E-1 and E-2 evidence: immutable baseline inputs; not modified in Phase 1.

## Governing architecture document hashes

SHA-256 values were captured from the working tree before the baseline commit.

| File | SHA-256 |
|---|---|
| `docs/ai-control-center/00-CONSTITUTION.md` | `8cde53ca7ca036c283c83bb09060de95ffd557d18279ac2224d30f80daa9b94f` |
| `docs/ai-control-center/01-SYSTEM-ARCHITECTURE.md` | `d5bbcbd4d0107b5e22132d0c2271787f2c75b39170603ac0177352c3953ed130` |
| `docs/ai-control-center/02-AGENT-ROLES.md` | `264eec137744ef1949fda0081db31ff5fba5bd22d3b88f79f2deb7416010bb98` |
| `docs/ai-control-center/03-TASK-LIFECYCLE.md` | `2762863e95ad757b2eac780bca0a504040f462724a88c9da37e7eb162f232277` |
| `docs/ai-control-center/04-ORCHESTRATION-RULES.md` | `98fdc325c687d0814b091b9de86f7b8de0f5a73bc29bf7f2a04ee1` |
| `docs/ai-control-center/05-REVIEW-GATES.md` | `27f24eed3de21be7b85c140dbc8d5e771665b808c2cb9f95f842c8d291d18c14` |
| `docs/ai-control-center/06-DASHBOARD-SPEC.md` | `2f8f8ee01ceb41fa9bc9352ab1cfa9764b332b18c0dec301d4059cf7cb76340f` |
| `docs/ai-control-center/06-FINAL-ARCHITECTURE-CONVERGENCE.md` | `923db56b8d50c1ca88e7ca43aaf846a5e3a73ec7d68e24d149d8763b7167fb92` |
| `docs/ai-control-center/07-SOL-FINAL-ARCHITECTURE-ARBITRATION.md` | `484bd365c030b43072286867150db38130f1055af92238a4739fe9d92e008d79` |
| `docs/ai-control-center/07-TOKEN-COST-SPEC.md` | `21ca126740ad200157d72f3625d1cb4682ab770d90c053a0925fb7db2afc93a2` |
| `docs/ai-control-center/08-GIT-WORKTREE-RULES.md` | `95d0209ac8eac7250859b576c10d23877a273c821cc09b7f9d8f9c6ec8c58663` |
| `docs/ai-control-center/09-SAFETY-BOUNDARIES.md` | `668ecab96a0c8938308489d046a7d08ab7b8559f723cd0e42679f9c472b42d50` |
| `docs/ai-control-center/10-FAILURE-RECOVERY.md` | `363ce906f3ad0039926c123bd27d457b3a00fb3803cb29547b91b545738950d0` |
| `docs/ai-control-center/11-DATA-MODEL.md` | `77406cf06dd8cd44473e22bcdb182bc6043a6d40d686eafb965a6713a282d0aa` |
| `docs/ai-control-center/12-OBSERVABILITY.md` | `9b247c76e033247a8fa0e6dfcccc1ce3fc90dadce61b65cb0e59e3520c9b5940` |
| `docs/ai-control-center/13-IMPLEMENTATION-ACCEPTANCE.md` | `2c2961ca8f51a3f8fdaa6cc80ddc91ad46e02566a784c2a0bb535a29f578b847` |
| `docs/ai-control-center/14-ARCHITECTURE-SELF-REVIEW.md` | `46e17fcbf291243185aac6a44438bd805759d5b6246df7062974e3224c5af38e` |
| `docs/ai-control-center/DECISIONS.md` | `b57837e29e911a5681f7c9b7996cae7bfd8364ae4657d197a3d5b9e08de7e888` |
| `docs/ai-control-center/OPEN-QUESTIONS.md` | `9c811698e748cf3707eb23cd291058f383969dbcf23f4c6a91935904f187e19f` |
| `docs/ai-control-center/MASTER-SPEC.md` | `79d551bc994272264fa40185ff46388161477308b637bc9ab860135575afdaee` |
| `docs/ai-control-center/CODEX-USAGE-CAPABILITY.md` | `1fe4e264e789bab945d03213a27736f555e0bb6905db5eeb03b840e4cf30465b` |
| `docs/ai-control-center/PHASE-0-FEASIBILITY-REPORT.md` | `4876df98f569ef92b1a7ead1307cf90fe95f69c98e150b277963fc9bc6cc2823` |
| `docs/ai-control-center/UPSTREAM-SYMPHONY-DELTA.md` | `6966caf7cc5939f2ee5aa67833d1157bc8a2f7e3b7a2576e6b4cf813bec636e7` |

## Phase 0 evidence hashes

| File | SHA-256 |
|---|---|
| `docs/evidence/phase-0-feasibility/E1-environment.md` | `be7c9ffe87e6e282fdfdbd7e38f7d3b4682c6abdc5cc5a738bc29bf7f2a04ee1` |
| `docs/evidence/phase-0-feasibility/E1-policy-results.md` | `7b0d5c57a929205cc666570fee80b46469a00a69ca8321377573ebbb5f8ec770` |
| `docs/evidence/phase-0-feasibility/E1-runtime-events.jsonl` | `c559d7eab5d8e1bb789273aba51659b6b2d5e5f71f1be532c1f96e1dc78840dd` |
| `docs/evidence/phase-0-feasibility/E1-human-bootstrap-request.md` | `272d1a56dd5391bc295ce655337f2d7786dd4b6b6266287b22cc45b4c4a873e6` |
| `docs/evidence/phase-0-feasibility/E2-runs-summary.md` | `eedb95d5b6db5db5ca53651518993cf54e55e338020e3485e12c58afccc9ab1d` |
| `docs/evidence/phase-0-feasibility/E2-permissions.md` | `12223c1e4297cf4323f8559fe6425d5afb6b93609ac1b98496e1add1b394d803` |
| `docs/evidence/phase-0-feasibility/E2-run-ids.md` | `c2af533ddd4b34383639a9097a0b1bc25829870cc7c06644073ae718f9de5698` |
| `docs/evidence/phase-0-feasibility/usage-capability.md` | `bac321478e7957282171a8b5d7732281b6ff816834868755f022996c8d8f674d` |
| `docs/evidence/phase-0-feasibility/app-server-schema/codex_app_server_protocol.v2.schemas.json` | `d3eace08be5dca386bfd1f1e8df650058b4113f1e10870a284d775d75517576a` |

## Baseline invariants

- 07 remains the higher-priority arbitration when earlier architecture text conflicts.
- PostgreSQL is the authoritative state store; no local SQLite fallback is an implementation authority.
- Codex CLI/App Server target is `0.153.2`; unsupported runtime/schema changes fail closed.
- E-1/E-2 evidence is read-only input to this phase.
