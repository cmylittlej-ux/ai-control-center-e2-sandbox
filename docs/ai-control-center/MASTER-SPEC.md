# AI Development Control Center — Master Spec

版本：`0.2-PHASE-0-FEASIBILITY`

当前阶段：`Phase 0 — Architecture Freeze Revision + E-1/E-2 Feasibility`

当前状态：`PHASE_0_FEASIBILITY_PASS — IMPLEMENTATION NOT AUTHORIZED`

## 系统是什么

Control Center 是 Hardened Symphony-derived AI Development Control Center。推理层提议，Control Plane 决定，隔离执行层动手，独立验证层作证，GitHub/Integration Gate 把门，Evidence Layer 留痕，Human Owner 保留最高权限。

## 必读顺序

1. `00-CONSTITUTION.md`
2. `MASTER-SPEC.md`
3. `UPSTREAM-SYMPHONY-DELTA.md`
4. `06-FINAL-ARCHITECTURE-CONVERGENCE.md`（实际收敛源）
5. `07-SOL-FINAL-ARCHITECTURE-ARBITRATION.md`（高于旧架构冲突）
6. `01-SYSTEM-ARCHITECTURE.md`、`02-AGENT-ROLES.md`
7. `03-TASK-LIFECYCLE.md`、`04-ORCHESTRATION-RULES.md`、`05-REVIEW-GATES.md`
8. `06-DASHBOARD-SPEC.md`、`07-TOKEN-COST-SPEC.md`
9. `08-GIT-WORKTREE-RULES.md`、`09-SAFETY-BOUNDARIES.md`、`10-FAILURE-RECOVERY.md`
10. `11-DATA-MODEL.md`、`12-OBSERVABILITY.md`
11. `13-IMPLEMENTATION-ACCEPTANCE.md`、`DECISIONS.md`、`OPEN-QUESTIONS.md`
12. `14-ARCHITECTURE-SELF-REVIEW.md`、`CODEX-USAGE-CAPABILITY.md`、`PHASE-0-FEASIBILITY-REPORT.md`

## 冻结不变量

- Human Owner 最高权限；AI 不得自授权。
- Worker 不能审核自己；权威验证必须尽量独立于 Worker。
- 每个 Project/Task 隔离；每个 Task 独立 Worktree/Branch/Commit/lease。
- App Server 是首选机器 runtime interface；Codex Desktop 不是控制协议。
- Task 使用九个顶层状态，等待/返工/失败等由 reason_code 表达。
- Symphony 适用 primitives 优先复用；Control Center 只增加明确的 Hardened controls。
- Token、Billing Mode、API actual cost 和 API-equivalent estimate 不能混称。
- Audit/Evidence append-only；Main、Production、高风险外部动作需要 Human + Guardian。

## 当前允许

仅允许：官方上游对齐、架构文档修订、E-1/E-2 disposable feasibility、Usage capability probe、secret redaction、证据和最终报告。

## 当前禁止

禁止正式 Dashboard、正式 Orchestrator、多 Agent runtime、正式 DB schema、生产 API、部署、自动化、真实业务 Project 访问，及把 09 路线当作当前授权。

## Implementation Ready

只有 E-1/E-2 通过、OQ-006 等阻塞项关闭、版本/schema/权限/预算/备份边界获批准，并且 Human Owner 明确回复 `APPROVED FOR IMPLEMENTATION` 后，才能进入 Implementation Phase 1。当前仍未授权实施。

## 失败处理

E-1/E-2 任一失败或无法证明，或必需的架构 provenance source 缺失时，报告完成后 HARD STOP；只允许局部架构修正和重新设计实验，不得偷偷降低安全边界继续开发。
