# Agent 角色与模型策略

状态：`FROZEN — V1 ROLE MODEL`

## V1 运行角色

V1 只定义三类运行角色；Frontend、Backend、Data、Test、Documentation 等不创建独立 runtime，而是作为 `specialization_tag` 与 Prompt/Acceptance Contract 约束 Generic Implementer。

| 角色 | 默认模型家族 | 职责 | 禁止 |
|---|---|---|---|
| Sol Project Director | Sol | 需求解析、阶段计划、Task 拆分、依赖图、模型/能力路由、批次决策、失败升级 | 普通业务实现、绕过 Gate、代替 Human Owner 批准高风险动作 |
| Sol Reviewer | Sol | 独立检查 Requirement、AC、Diff、CI、回归、安全、权限、范围、架构和证据 | 修改被审 Worktree、复用实现写权限、缺证据判 PASS |
| Luna Generic Implementer | Luna | 在授权 Worktree 内按 specialization tag 实现、测试、提交和整理证据 | 写 main、访问其他 Project、修改权威 CI/Branch Protection、自审 |

Guardian、Architect、Integration 和 Test Runner 是控制面/验证面能力或按需的受控执行模式，不是 V1 的六套 Worker runtime。任何新增 runtime 必须先更新架构、权限和可行性证据。

## Runtime protocol

Implementer 通过 Codex App Server client 运行。每个 Connection 先执行 `initialize`，再 `initialized`；每个工作单元创建或恢复 Thread，使用 `turn/start` 执行 Turn，消费双向事件直到 `turn/completed`。保存官方 Thread/Turn/Session 标识、模型 ID、resolved version、cwd、sandbox、approval policy 和 runtime event。

App Server schema 是协议真相；Control Center 不猜测字段，也不把自然语言消息当结构化 usage、approval 或完成证据。

## 模型策略

- 低风险、明确范围的执行默认使用 Luna；模型 ID、版本和 reasoning effort 必须由配置和运行事件确认。
- Director、Reviewer、Security、Authentication、Permissions、Migration、跨模块复杂问题和多次失败使用 Sol 或人工升级路径。
- configured model ID/family 变化或 provider 明确 major replacement 时降级自治；内部 revision 变化只触发 shadow recalibration 与抽样，不自动降低自治等级。
- 模型升级必须记录触发证据、前后模型、预算影响和回滚路径。

## 权限与上下文

权限由 `role + project_id + task_id + environment + capability + expiry` 决定。Worker 不继承 Bootstrap 权限，不接收原始 tracker/Secret 凭证，不拥有系统用户、网络、Keychain 或 Branch Protection 修改权限。

Thread 达到配置的 Context Threshold 时生成 Handoff Package；Handoff 至少包含 Task、Requirement、AC、State/reason_code、Scope、Files、Branch、Worktree、Commit、Tests、Review、Usage、Failed Attempts、Decisions、Remaining Work、风险、下一动作和 Event IDs。新 Thread 先确认 Handoff，再获取新的 lease；旧 Thread 不再写入同一 Task。

