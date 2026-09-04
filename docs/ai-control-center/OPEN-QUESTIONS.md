# Open Questions

状态：CLOSED FOR PHASE 0 — NO REMAINING P0 BLOCKERS

07 remains the authoritative architecture arbitration. E-1 and E-2 are PASS. The items below distinguish cleared Phase 0 acceptance from non-blocking Phase 1 controls; no requirement is weakened.

## OQ-001 — E-1 Restricted Runtime

- 问题：Codex App Server/Worker 能否在无主用户 Secrets、低权限 macOS identity 和受控 Workspace/Network 边界内完成 fixture coding task？
- 当前：CLOSED — PASS. Dedicated Standard User aicc-worker, boundary denials, real App Server Turn, expected fixture-only change, fixture test, and live structured usage were verified.
- 是否阻塞实施：否。

## OQ-002 — E-2 Independent Verification

- 问题：GitHub-hosted ephemeral runner 是否能稳定运行完整验证，并使 Worker 无权修改 Branch Protection、main 或权威 evidence？
- 当前：CLOSED — PASS. Disposable repository cmylittlej-ux/ai-control-center-e2-sandbox, 20/20 authoritative runs, negative gate, exact Run IDs/SHAs, and permission denials were verified.
- 是否阻塞实施：否。

## OQ-003 — Codex Usage Event Fields

- 问题：目标 App Server 版本的 thread/tokenUsage/updated 实际 payload 是否提供 input、cached input、output、reasoning、total、context window 等字段？
- 当前：CLOSED FOR PHASE 0 — PASS. A real App Server Turn exposed all required token fields and modelContextWindow; observed context window was 258400.
- Phase 1 residual：保留 raw payload，并在可用时记录 configured/resolved model ID/version；未提供的 resolved model metadata 不得由 Agent 补齐。
- 是否阻塞 Phase 0：否。是否允许 Phase 1 implementation 仍受版本/schema pin gate 约束：是。

## OQ-004 — Subscription vs API Billing Semantics

- 问题：当前 runtime 的 billing mode 是 chatgpt_subscription、api_billed 还是 unknown，以及是否存在可引用的官方实际账单接口？
- 当前：CLOSED FOR PHASE 0 — SUBSCRIPTION SEMANTICS. Verified account evidence reported plan_type Plus. This is ChatGPT subscription/runtime usage, not API billing cost.
- Frozen rule：chatgpt_subscription 只显示 Token 和明确标注的 API-equivalent estimate；不能称为实际扣费。api_billed 仍须 provider-confirmed usage 与版本化 rate card；unknown 仍显示 unavailable/不确定。
- 是否阻塞 Phase 0：否。实际账单接口仍不得假设存在。

## OQ-005 — Target App Server Version Pin

- 问题：实施环境应固定哪个可验证的 Codex CLI/App Server build 和 schema snapshot？
- 当前：CLOSED FOR PHASE 0 EVIDENCE — verified Codex CLI/App Server is 0.153.2.
- Phase 1 residual：Implementation Gate 仍必须在实施前固定 executable version、对应 schema snapshot、权限边界和可复核的 build metadata；本项不是 E-1/E-2 可行性阻塞。
- 是否阻塞 Phase 0：否。是否阻塞 Phase 1 implementation until pinned: 是。

## OQ-006 — Missing Convergence Source

- 问题：08 要求纳入 docs/ai-control-center/06-FINAL-ARCHITECTURE-CONVERGENCE.md，当前工作区是否存在真实文件？
- 当前：CLOSED — PROVENANCE VERIFIED. The exact file is present at the required path and was read in full: 702 lines, SHA-256 `923db56b8d50c1ca88e7ca43aaf846a5e3a73ec7d68e24d149d8763b7167fb92`.
- 一致性：文件标题为 `Architecture Review #2C — Final Convergence & Freeze Recommendation`; it defines the seven-layer architecture, 11 P0 Capabilities, V1 two Worker slots, GitHub-hosted ephemeral verification, E-1/E-2 as pre-autonomy experiments, and `NO IMPLEMENTATION. HARD STOP.` This is the convergence source accepted by 07 and explicitly required by 08.
- 处理：已将真实文件纳入本地 read order and Phase 0 provenance record. 07 remains the higher-priority arbitration if any earlier text conflicts.
- 是否阻塞 Phase 0 deliverable：否。是否改变已通过的 E-1/E-2：否。
