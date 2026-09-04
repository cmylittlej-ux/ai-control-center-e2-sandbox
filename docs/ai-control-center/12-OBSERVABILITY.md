# 可观测性与审计规范

状态：`FROZEN — EVIDENCE FIRST`

## 必须记录的事件

Project/Task 创建和改变、Agent Start/Stop、App Server Connection/Initialize/Thread/Turn、Tool Call、Approval、User Input、Commit、Test/CI、Review、Rework、Model Change、Token/Usage、Cost、Policy Decision、Failure、Recovery、Integration、Rollback、Human Approval、Kill Switch 和 Backup/Restore 都必须产生日志事件。

## 事件字段

```text
event_id, occurred_at, recorded_at, actor_type, actor_id,
event_type, project_id, task_id, execution_id, thread_id, turn_id,
state_version, correlation_id, idempotency_key, target, outcome,
reason_code, evidence_refs, raw_payload_hash, prev_hash,
usage_ref, cost_ref, policy_decision, redaction_class
```

原始 Prompt、工具参数、输出和环境按敏感等级保留；Secret 永不写入 Event/Evidence。必须区分 request、policy deny、result、timeout 和 compensation。

## App Server observability mapping

保存 `initialize` 返回的 client/runtime metadata、Thread/Turn IDs、`item/*` 生命周期、`turn/diff/updated`、`turn/plan/updated`、approval 请求/结果、`turn/completed`、model reroute/verification、`thread/tokenUsage/updated` 和 process/transport 错误。字段是否存在由目标 schema 和 Probe 结果决定。

## 审计链与指标

链路必须为 `Project -> Task -> Execution -> Thread/Turn -> Tool/Test/Commit -> Review -> Gate -> Integration -> Decision`。指标覆盖状态停留、Task lead time、Review PASS/FAIL、Rework、Blocked、Recovery、CI success、Policy deny、Secret risk、Lease conflict、Token、Cost、Burn Rate、预算暂停和 Kill Switch。每个指标可下钻到 Event/Evidence。

## 健康与告警

告警包括 Blocked、Hard/ Emergency Stop、Policy deny、疑似 Secret、审计不一致、重复 Writer、Test Hang、连续失败、usage unavailable、CI 权限缺口、Backup/Restore 失败和 Main 请求。状态无变化不制造噪声；数据延迟或不完整必须显示为不确定，而不是绿色健康。

