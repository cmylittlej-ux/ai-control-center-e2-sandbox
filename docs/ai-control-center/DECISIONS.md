# Final P0 Architecture Decision Log

状态：`FROZEN — 11 P0 ADRs`

以下十一项是最终 P0 capability 决定；全部实现仍以 E-1/E-2 和 Human Gate 为前提。

## ADR-P0-C1 — Control Plane Correctness

Control Plane 是 Project、Task、AC、Policy、Budget、Lease、Evidence 和 Integration 的事务权威；状态版本、幂等和事件关联必须机械执行。理由：避免 Agent、Dashboard 或 Tracker 文本伪造状态。

Status：Accepted for Phase 0 / Implementation gated

## ADR-P0-C2 — Leasing & Crash Recovery

每个 Execution 使用 lease、heartbeat、fencing 和 checkpoint；重启先 reconciliation 再恢复。理由：防止双写和丢进度。

Status：Accepted for Phase 0 / Implementation gated

## ADR-P0-C3 — Worker Isolation & Local Hygiene

每个 Task/Project 使用隔离 Worktree、进程、端口、临时目录和凭证环境；Worker 外的写入默认拒绝。理由：防止代码、进程和 Secrets 污染。

Status：Accepted for Phase 0 / Implementation gated

## ADR-P0-C4 — Deterministic Policy Enforcement

所有动作经过 Project/Task/Role/Environment/Target/Capability/预算/Approval 组合策略；未知策略不自动放行。理由：把安全边界从 Prompt 愿望变成可验证决策。

Status：Accepted for Phase 0 / Implementation gated

## ADR-P0-C5 — Contract-first Acceptance

Requirement、AC、Scope、风险、回滚和 Evidence mapping 在执行前冻结；完成由契约和证据决定。理由：减少模糊需求和主观进度。

Status：Accepted for Phase 0 / Implementation gated

## ADR-P0-C6 — Independent Verification

权威 Test/Lint/Build 优先运行于 Worker 无法修改的 GitHub-hosted ephemeral runner；Reviewer 独立于实现身份。理由：防止测试弱化和自审 PASS。

Status：Accepted for Phase 0 / Implementation gated

## ADR-P0-C7 — Git & Integration Safety

Worker 只能提交 Task Branch；Integration Queue 只接收通过 Gate 的证据包；main/Branch Protection/生产动作需要人工。理由：将并行开发与稳定主线隔离。

Status：Accepted for Phase 0 / Implementation gated

## ADR-P0-C8 — Evidence & Audit

Evidence Manifest、Event Log 和 Cost/Usage 记录追加式保存，审计 writer 只 INSERT/SELECT，记录 prev_hash 并机外备份。理由：支持复核、恢复和争议审计。

Status：Accepted for Phase 0 / Implementation gated

## ADR-P0-C9 — Budget & Runaway Protection

Task、Project、Agent 和 Global 都有预算、运行和停止策略；Warning、Hard、Emergency Stop 具有明确语义且不可通过换 Thread 绕过。理由：控制 Token、时间和 Agent runaway。

Status：Accepted for Phase 0 / Implementation gated

## ADR-P0-C10 — Human Loop & Notification

低风险路径自动推进；Main、Production、Secrets、Billing、安全边界和不可逆操作进入 Human Decision，并提供 Security Event、Decision Inbox 和 Kill Switch。理由：无人值守不等于无人负责。

Status：Accepted for Phase 0 / Implementation gated

## ADR-P0-C11 — Backup & Disaster Recovery

状态、事件、证据、配置、Usage、审批和 Handoff 可备份、可恢复、可重建；恢复前校验 Git/CI/lease/预算。理由：Mac、Orchestrator 或 Runtime 崩溃不能丢失控制面真相。

Status：Accepted for Phase 0 / Implementation gated

