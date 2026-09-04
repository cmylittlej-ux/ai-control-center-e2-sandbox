# Dashboard 设计规范

状态：`FROZEN — DESIGN ONLY`

本文件只定义未来状态面，不开发 Dashboard。中文为主，英文为小号辅助；Desktop First；Dark/Light；高信息密度但不拥挤。状态颜色必须克制，颜色不能是唯一语义。

## 首页必须直接回答

1. 系统是否在动、最近状态变化是什么；
2. Director、Reviewer、Worker Slot 1、Worker Slot 2 此刻在做什么；
3. 当前 Running Task、最近完成了什么、下一步队列是什么；
4. 哪些 Review/Rework、Blocked、Attempt 较高；
5. 是否需要 Human Decision；
6. Token、Cost、Burn Rate 是否异常；
7. 是否有 Security Event；
8. Kill Switch 当前状态和最近操作。

## Agent Activity Strip

首页固定显示：

| Role | Model | Task | State | Attempt | Runtime | Token | Last event |
|---|---|---|---|---|---|---|---|
| Director | ... | ... | ... | ... | ... | ... | ... |
| Reviewer | ... | ... | ... | ... | ... | ... | ... |
| Worker Slot 1 | ... | ... | ... | ... | ... | ... | ... |
| Worker Slot 2 | ... | ... | ... | ... | ... | ... | ... |

并行槽位按 V1 低并行度显示；是否扩容只能由可行性和 pilot Gate 决定。

## 首页分区

- 系统状态：运行/暂停/阻塞、最近事件、Scheduler/Runtime/CI 健康。
- 正在进行：Task ID、名称、specialization tag、Agent、状态、Attempt、Runtime、Token、当前证据阶段。
- 最近完成：Task、Commit、Review、CI、Integration Evidence 和完成时间；“完成”必须可下钻。
- 下一步队列：依赖原因、优先级、预计需要的 Policy/Gate、预算状态。
- Review / Rework：待审、失败原因、返工上下文、Reviewer、下一允许动作。
- Blocked：reason_code、影响范围、尝试过的动作、等待对象和解决条件。
- Need Human：精确动作、目标、Commit/版本、风险、Evidence、回滚和到期时间。
- Token / Cost：按 Project/Task/Agent/Model/Date 聚合，分开显示 token、Billing Mode、API actual cost 与 API-equivalent estimate。
- Security：Guardian deny、Secret scan、越权、策略绕过、审计不一致。
- Kill Switch：Soft Stop、Hard Stop、Emergency Stop 的当前状态、触发者、时间、覆盖范围和恢复条件。

## Project / Task detail

Project 详情固定显示正在进行、最近完成、下一步队列、Review/Rework、Blocked、Dependency Graph、健康、Branch/Base Commit、CI 和成本。Task 详情固定显示 Requirement、逐条 AC、State/reason_code、Attempt/failure class、Agent/model、Branch/worktree/Commit/Diff、权威 CI、Review、Token/Cost 和完整 Timeline。

## 明确不做

V1 不做 Jira-style Gantt、velocity/story points、AI ETA、multi-user RBAC 或 public remote access。Dashboard 只读，不拥有改变状态、批准或绕过 Kill Switch 的权限。

