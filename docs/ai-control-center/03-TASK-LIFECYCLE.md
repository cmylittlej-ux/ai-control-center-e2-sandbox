# Task 生命周期与状态机

状态：`FROZEN — 9 STATES`

## 设计

Task 使用恰好九个顶层状态；等待、返工、失败、取消、回滚、暂停、预算和人工原因通过 `reason_code` 表达，不再扩展顶层状态。执行尝试的内部生命周期另行记录，不改变 Task 状态集合。

```text
BACKLOG -> READY -> RUNNING -> TESTING -> REVIEW
REVIEW -> READY_TO_INTEGRATE -> INTEGRATED -> DONE
任何可恢复或不可自动解决的异常 -> BLOCKED
```

## 九个状态

| 状态 | 进入条件 | 退出条件与证据 |
|---|---|---|
| BACKLOG | 需求已登记但尚未形成可执行 Task | Requirement、AC、Owner、范围和风险完整后 READY |
| READY | 依赖、Scope、Acceptance Contract、预算和策略检查通过 | 分配 lease、Worktree 和 Generic Implementer 后 RUNNING |
| RUNNING | 运行实例持有有效 lease，并在授权 Worktree 执行 | 实现 Commit 和开发证据后 TESTING；无权/异常则 BLOCKED |
| TESTING | Commit 固定且测试计划已冻结 | 权威验证结果完整后 REVIEW；失败按 reason_code 返工或 BLOCKED |
| REVIEW | 独立 Reviewer 拥有只读证据包 | `PASS` 后 READY_TO_INTEGRATE；FAIL 返 RUNNING 并带返工原因；无法审查 BLOCKED |
| READY_TO_INTEGRATE | Review PASS、AC 映射、证据 Manifest 和策略检查完整 | Integration Queue 接受后 INTEGRATED；冲突/漂移 BLOCKED |
| INTEGRATED | 变更进入受控 integration 分支并有集成记录 | 集成验证和回滚证据通过后 DONE；回归则 BLOCKED |
| DONE | DoD、Review、权威验证、Integration 和审计证据完整 | 终态；后续回归创建新 Task，不重写历史 |
| BLOCKED | 需要人工、依赖、权限、预算、循环、故障或证据修复 | 原因消除、重新授权和版本校验后回 READY/RUNNING；否则保持 |

## reason_code

`reason_code` 必须使用受控枚举并在人类界面显示中文解释。基础集合：

`UNPLANNED`、`DEPENDENCY_PENDING`、`AWAITING_ASSIGNMENT`、`IMPLEMENTING`、`REWORK_REQUIRED`、`TEST_FAILURE`、`REVIEW_PENDING`、`REVIEW_FAILURE`、`VERIFICATION_PENDING`、`HUMAN_APPROVAL_REQUIRED`、`POLICY_DENIED`、`BUDGET_WARNING`、`BUDGET_HARD_LIMIT`、`RUNTIME_CRASH`、`TIMEOUT`、`STALL`、`GIT_CONFLICT`、`BASE_DRIFT`、`CANCELLED`、`ROLLED_BACK`、`NO_PROGRESS`、`EVIDENCE_MISSING`、`NONE`。

每次状态转移必须记录 `from_state`、`to_state`、`reason_code`、actor、state_version、evidence_refs、correlation_id 和 next_allowed_action。未知 reason_code 或非法状态跳转必须拒绝。

## 返工与限制

返工轮次、运行时长、调用次数和预算属于可调 Runtime/Project Policy，不写入宪法。无论配置如何，不能通过新 Thread、换 Agent、模型升级或重启绕过已批准的总边界；达到边界进入 BLOCKED 并保留证据。

## 状态可解释性

每个非 DONE Task 必须能回答：当前状态、reason_code、进入事件、责任主体、依赖、所需证据、下一允许动作和阻塞影响。百分比不能替代状态证据。

