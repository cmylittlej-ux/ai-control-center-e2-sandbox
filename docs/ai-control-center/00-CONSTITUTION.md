# AI 开发指挥中心开发宪法

状态：`FROZEN — PHASE 0 FEASIBILITY`

本宪法是 AI Development Control Center 的最高工程规则。具体运行配置、实验阈值和实施细节只能补充本文件，不能削弱本文件。

## Human authority

- `Human Owner` 是最终权限持有人、风险承担者和不可替代的审批边界。
- AI 可以规划、执行、测试、审查和调度，但不能自行扩大权限、改变安全边界或把建议变成授权。
- 高风险动作必须由 Human Owner 明确批准；没有批准等同于拒绝。
- 每次人工决定必须保存主体、作用域、理由、时间和结果。

## Evidence over assertion

- Agent 的 `Done`、`Complete` 或相似文字不是完成证明。
- Task 只能由客观证据和适用门禁推进；缺证据不得伪装为完成。
- 证据必须能把需求、验收、代码、测试、审核、集成和审计事件串成可复核链路。

## Separation of duties

- 实现身份不能批准自身实现；Reviewer 必须独立于 Worker 的身份、权限、写入环境和未审上下文。
- 测试/验证必须尽量在 Worker 无法修改或污染的权威环境中运行。
- 任何无法独立验证的结果必须标记为不确定或阻塞。

## Least privilege and default deny

- 权限按 Project、Task、Role、Tool、Environment 和有效时间授予，任务结束后撤销。
- 跨 Project 访问、主分支写入、生产操作、秘密读取和不可逆外部操作默认拒绝。
- 允许自动化的动作仍必须经过确定性策略和审计；允许自动化不等于拥有无限权限。

## Project isolation

每个 Project 必须拥有独立的 Repository、Task 命名空间、Agent Context、Git 状态、Worktree 根目录、Token/Cost 账本、日志、配置、Secrets Scope 和证据链。所有运行上下文必须携带并校验 `project_id`；不能通过路径、环境变量、Prompt 或工具参数绕过隔离。

## Controlled change

- 每个 Task 使用独立 Branch、Worktree、Commit 和执行租约。
- Worker 不得写入 `main` 或其他 Worker 的 Worktree。
- 自动流程只能进入受控 Integration；Main/Production 变更必须经过更高等级人工门禁。
- 所有变更必须可定位、可回滚、可审计；回滚不删除原始证据。

## Bounded autonomy

- Task、Project、Agent 和全局执行都必须有资源边界、运行边界和停止条件。
- 重试、返工、模型升级、Handoff 和恢复必须受策略控制；不能通过换 Thread、换 Agent 或重启绕过限制。
- 无进展、连续失败、预算异常、策略拒绝和状态不一致时必须停止自动推进并解释原因。

## Durable truth

- 状态、事件、证据、预算、使用量、审批和交接包必须持久化。
- 审计与证据记录追加式保存；纠错写 correction record，不覆盖原记录。
- 恢复只能从已持久化 checkpoint 和可验证外部事实开始，不能依赖 Agent 记忆。

## Freeze boundary

本阶段只允许官方上游对齐、架构修订、可行性实验、证据脱敏和报告。禁止开发正式 Dashboard、Orchestrator、多 Agent runtime、正式数据库/API、部署、自动化或接入真实业务 Project。

只有 `PHASE-0-FEASIBILITY-REPORT.md` 达到允许实施的结论，并且 Human Owner 明确批准，才能进入实施阶段。

