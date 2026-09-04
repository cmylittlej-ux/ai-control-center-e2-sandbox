# 数据模型

状态：`FROZEN — CONTROL PLANE MODEL`

## 核心实体

| 实体 | 关键字段 | 强制约束 |
|---|---|---|
| Project | id、repo、policy_version、phase、health | Project scope 全局唯一 |
| Task | id、project_id、type、requirement、acceptance_contract、state、reason_code、version、budget_id | 只能使用九状态和受控 reason_code |
| Dependency | upstream、downstream、kind | Project 相同且必须是 DAG |
| Agent Runtime | id、role、model_id、resolved_version、specialization_tag、capabilities | V1 只有 Director/Reviewer/Generic Implementer |
| Execution | id、task_id、agent_id、thread_id、turn_id、lease、fencing_token、checkpoint | Task 同时只能一个 active writer |
| Workspace | id、project_id、task_id、path、branch、commit、lock | root containment 和唯一 writer |
| Evidence Manifest | id、task_id、commit、ac、ci、review、artifacts、hash | 内容不可覆盖，Project/Commit 匹配 |
| Review | id、task_id、reviewer_id、result、findings、round | Reviewer 不得等于实现身份 |
| Budget / Usage | scope、thresholds、raw_usage、normalized_usage、billing_mode、rate_snapshot、cost | 缺失 usage 不得 Agent 补齐 |
| Approval | id、human、action、target、commit/version、expires、decision | 目标或版本变化即失效 |
| Event | id、time、actor、type、project/task/execution、state_version、correlation、payload_hash、prev_hash | append-only；纠错写新记录 |

## 事务与审计角色

可变 State Store role 与 Audit/Evidence Writer role 分离。Audit/Evidence role 只有 INSERT + SELECT；不能 UPDATE/DELETE。Correction record 引用原记录并保存原因。机外备份不允许由运行 Worker 删除或覆盖。

## State 与 reason_code

Task 顶层状态恰好为：`BACKLOG`、`READY`、`RUNNING`、`TESTING`、`REVIEW`、`READY_TO_INTEGRATE`、`INTEGRATED`、`DONE`、`BLOCKED`。等待依赖、返工、失败、取消、回滚、暂停、预算、策略和人工原因存于 `reason_code`，不另造状态。

## Acceptance Contract

Requirement 保存原文、解析版本、范围、非目标、风险和来源。AC 保存可验证条目、冻结版本、owner、evidence mapping 和变更历史。Review 后不得由 Implementer 修改 AC；变化必须产生新版本和重新进入控制面。

## 状态视图与隔离

Dashboard 使用带 `as_of`/`source_event_id` 的只读投影。Task、Execution、Branch、Worktree、Commit、Review、Usage、Event 的 Project ID 必须一致；跨 Project 引用默认拒绝。`DONE` 必须存在适用的计划、权威验证、独立 Review、Integration 和审计证据。

