# 审核门禁与三个回路

状态：`FROZEN — THREE LOOPS`

## Task Loop

单个 Task 的闭环：

```text
Implementer -> Independent Verification -> Sol Reviewer
       ^                                  |
       |------ structured rework --------|
```

进入下一步必须有证据：Requirement/AC → Commit/Diff → 权威 Test/Lint/Build → 独立 Review → Evidence Manifest。Worker 不能成为 Reviewer，Reviewer 不能修改被审 Worktree。

Review 只能输出 `PASS`、`CONDITIONAL PASS`、`FAIL`、`BLOCKED`。FAIL 必须包含 Problem、Expected、Actual、Evidence、Files、Required Tests、reason_code 和返工上下文；没有证据不能通过。

## Batch Loop

Director 根据 Dependency Graph 形成就绪批次。只有 Task Loop 完成且集成证据存在，Task 才能进入受控 Integration Queue；批次验证通过后，Director 重新读取 Project State、剩余依赖、失败和预算，再生成下一批。

Batch Loop 必须验证：Scope 不冲突、Worktree/lease 不共享、Base Commit 一致、CI checks 权威、集成可回滚、Main 仍受保护。Integration 不是 Main Merge；后者始终进入 Human Gate。

## Calibration Loop

Calibration Loop 观察模型/Agent 的质量与成本，不把内部 revision 变化直接当成自治降级：

- configured model ID/family 改变或 provider 明确 major replacement：标记 baseline change，重新校准并降低自治边界；
- resolved internal revision 变化但 configured model 未变：标记 `baseline_stale`，提高后续抽样；
- false PASS、回归、Policy Incident、stuck rate 或成本异常越过已批准阈值：暂停受影响自治路径并交 Sol/Human；
- calibration 证据恢复稳定后才能清除 stale 或恢复更高自治。

每次校准记录样本、指标、阈值版本、模型/Agent、结论和批准人。

## Gate 目录

| Gate | 结果 | 必要条件 |
|---|---|---|
| G0 Plan | READY / BLOCKED | Requirement、AC、DAG、Scope、Budget、风险和回滚计划 |
| G1 Evidence | READY / BLOCKED | Commit、Diff、Worktree、运行事件和测试计划 |
| G2 Verification | PASS / FAIL | 权威 CI 的 install、lint、unit、build，必要时 integration/E2E |
| G3 Review | PASS / CONDITIONAL PASS / FAIL / BLOCKED | 独立 Reviewer 完成逐条 AC、安全、范围和架构检查 |
| G4 Integration | PASS / BLOCKED | 串行集成、冲突/Base Drift、权威 checks、回滚证据 |
| G5 Human | APPROVED / DENIED / EXPIRED | Main/Production/不可逆动作的精确人工批准与 Guardian 复核 |

