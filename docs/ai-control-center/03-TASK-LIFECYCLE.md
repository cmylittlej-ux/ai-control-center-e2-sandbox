# Task 生命周期与状态机

状态：`FROZEN — 9 STATES`

## 设计

Task 使用恰好九个顶层状态；等待、返工、失败、取消、回滚、暂停、预算和人工原因通过 `reason_code` 表达，不再扩展顶层状态。执行尝试的内部生命周期另行记录，不改变 Task 状态集合。

```text
BACKLOG -> READY -> RUNNING -> VERIFYING -> REVIEW
REVIEW -> AWAITING_HUMAN (when a human gate is required)
REVIEW -> INTEGRATING (when no human gate is required)
AWAITING_HUMAN -> INTEGRATING / READY / CLOSED / BLOCKED (after a human decision)
INTEGRATING -> CLOSED
任何可恢复或不可自动解决的异常 -> BLOCKED
```

## 九个状态

| 状态 | 进入条件 | 退出条件与证据 |
|---|---|---|
| BACKLOG | 需求已登记但尚未形成可执行 Task | Requirement、AC、Owner、范围和风险完整后 READY |
| READY | 依赖、Scope、Acceptance Contract、预算和策略检查通过 | 分配 lease、Worktree 和 Generic Implementer 后 RUNNING |
| RUNNING | 运行实例持有有效 lease，并在授权 Worktree 执行 | 实现 Commit 和开发证据后 VERIFYING；超时、返工或异常按 reason_code 回 READY 或 BLOCKED |
| VERIFYING | PR/验证作业已触发；测试、构建、lint 等细节由 evidence/reason/status 表达 | 隔离权威验证作业终结后 REVIEW；失败可按 reason_code 回 READY 或 BLOCKED |
| REVIEW | 独立 Reviewer 拥有只读证据包 | `PASS` 且无需人工门禁时 INTEGRATING；命中 blocking/approval/escalation 时只能 AWAITING_HUMAN；FAIL 回 READY 并递增 attempt_id；无法审查 BLOCKED |
| AWAITING_HUMAN | 命中 Blocking Review、审批或升级阈值 | 仅 Human Decision 可进入 INTEGRATING、READY、CLOSED 或 BLOCKED；超时只 park，不自动批准 |
| INTEGRATING | Review 通过且已获准进入受控 integration 流程 | 在本状态内完成准备、rebase、全量验证和单一可回滚集成提交后 CLOSED；冲突/漂移/失败回 READY 或 BLOCKED |
| CLOSED | 集成完成，或任务被取消、取代或放弃，且结果证据已保存 | 终态；后续回归创建新 Task，不重写历史 |
| BLOCKED | 需要人工、依赖、权限、预算、循环、故障或证据修复 | Human 处置后回 READY 或 CLOSED；否则保持 |

## reason_code

`reason_code` 必须使用受控枚举并在人类界面显示中文解释。基础集合：

`UNPLANNED`、`DEPENDENCY_PENDING`、`AWAITING_ASSIGNMENT`、`IMPLEMENTING`、`REWORK_REQUIRED`、`TEST_FAILURE`、`REVIEW_PENDING`、`REVIEW_FAILURE`、`VERIFICATION_PENDING`、`HUMAN_APPROVAL_REQUIRED`、`POLICY_DENIED`、`BUDGET_WARNING`、`BUDGET_HARD_LIMIT`、`RUNTIME_CRASH`、`TIMEOUT`、`STALL`、`GIT_CONFLICT`、`BASE_DRIFT`、`CANCELLED`、`ROLLED_BACK`、`NO_PROGRESS`、`EVIDENCE_MISSING`、`NONE`。

每次状态转移必须记录 `from_state`、`to_state`、`reason_code`、actor、state_version、evidence_refs、correlation_id 和 next_allowed_action。未知 reason_code 或非法状态跳转必须拒绝。

## 返工与限制

返工轮次、运行时长、调用次数和预算属于可调 Runtime/Project Policy，不写入宪法。无论配置如何，不能通过新 Thread、换 Agent、模型升级或重启绕过已批准的总边界；达到边界进入 BLOCKED 并保留证据。

## 状态可解释性

每个非 CLOSED Task 必须能回答：当前状态、reason_code、进入事件、责任主体、依赖、所需证据、下一允许动作和阻塞影响。百分比不能替代状态证据。
