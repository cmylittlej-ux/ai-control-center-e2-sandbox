# 失败恢复规范

状态：`FROZEN — C2 RECOVERY`

## 持久状态与 checkpoint

必须持久化 Project/Task 状态版本、Dependency Graph、Acceptance Contract、Execution lease、fencing token、Agent/Thread/Turn、Worktree/Branch/Commit、CI/Review/Evidence、Usage/Cost、Budget、Approval、Event Log、Handoff Package 和恢复 checkpoint。

在接受 Task、每次 App Server request/notification、工具调用、Commit、验证套件、Review、状态转移、模型变化、预算事件、失败和恢复边界写 checkpoint。checkpoint 至少包含当前 State/reason_code、state version、Commit、未完成动作、上下文摘要、失败尝试、预算、lease 和下一安全动作。

## 通用恢复流程

```text
detect -> fence/revoke lease -> persist failure
       -> validate checkpoint + Git + CI + budget
       -> classify -> idempotent retry or rework
       -> verify + independent review
       -> recover, block, cancel, or rollback with evidence
```

恢复前必须证明不存在第二个 Writer、Worktree 没有被占用、目标 Project/Commit 匹配、预算有效、Approval 未过期。无法证明时进入 BLOCKED，不靠 Dashboard 手工改绿。

## Context Handoff

Context Threshold 由运行时/Project Policy 配置。达到摘要阈值生成结构化 summary；达到 handoff 阈值停止非必要背景并创建 Handoff Package；达到上限或阶段结束时停止旧 Thread。Package 必须携带 Task、Requirement、AC、State/reason_code、Scope、Files、Branch、Worktree、Commit、Tests、Review、Usage、Failed Attempts、Decisions、Remaining Work、风险、下一动作和 Event IDs。新 Thread 先确认 Package，再取得新 lease。

## 故障分类

| 故障 | 自动动作 | 无法安全恢复时 |
|---|---|---|
| Worker/Codex crash | 保存日志，fence，按 checkpoint 恢复 | BLOCKED + `RUNTIME_CRASH` |
| Mac/Orchestrator restart | 从 Event/Checkpoint/Git/CI 重建并 reconciliation | BLOCKED + `STATE_RECONCILIATION_FAILED` |
| API timeout/network/model error | 有界退避、幂等查询后重试 | BLOCKED/预算暂停 |
| Git conflict/base drift/worktree conflict | 只读检测，建立修复上下文 | BLOCKED + `GIT_CONFLICT`/`BASE_DRIFT` |
| Test hang | 终止进程组，保存输出和环境 | BLOCKED + `TEST_HANG` |
| Token/Cost boundary | 撤销 lease，暂停 Task | 需要重新授权或缩减 Scope |
| Invalid patch/dirty state | 保留现场，重新创建隔离 Worktree | BLOCKED + `EVIDENCE_MISSING` |
| Reviewer failure | 不改变 PASS，重试独立 Reviewer | Sol/Guardian/Human 决定 |

## 幂等与灾备

状态命令、外部动作、Commit 登记、UsageRecord、通知和恢复均使用 idempotency key；重复事件保留并标记 duplicate，不重复副作用。Audit/Evidence 采用 append-only writer、链式 hash 和机外备份；恢复演练必须证明可从备份重建状态和证据索引。

