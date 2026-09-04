# Upstream Symphony / Codex App Server Delta

状态：`PHASE 0 ALIGNMENT COMPLETE — IMPLEMENTATION PENDING`

## 来源与边界

本对齐基于：

- [OpenAI Symphony repository](https://github.com/openai/symphony)
- [Symphony SPEC.md](https://github.com/openai/symphony/blob/main/SPEC.md)
- [OpenAI: An open-source spec for Codex orchestration: Symphony](https://openai.com/index/open-source-codex-orchestration-symphony/)
- [OpenAI: Unlocking the Codex harness: how we built the App Server](https://openai.com/index/unlocking-the-codex-harness/)
- [Codex App Server official documentation](https://learn.chatgpt.com/docs/app-server)

Symphony 当前公开规范是 language-agnostic Draft v1，并明确面向 trusted environments 的 engineering preview；它是 scheduler/runner 与 tracker reader，不是 Control Center 的完整事务控制面、强安全沙箱或 Dashboard。Codex App Server 是首选机器接口，协议 shape/transport/字段以目标版本官方 schema 为准。

## 能力 Delta

| Capability | Upstream 事实 | 决定 | Control Center 增量 |
|---|---|---|---|
| Dispatch | 固定轮询 tracker，按 active/eligible issue 和 bounded concurrency dispatch | `REUSE` | 加入事务命令、Project/Task scope、AC/Policy/Budget gate 和 evidence-based eligibility |
| Workspace | 每 issue 确定性 workspace，root containment、sanitized key、cwd 校验，可复用并按 terminal 清理 | `REUSE` | 升级为 Project/Task Worktree，写 lease/fencing、进程/端口/临时目录/凭证隔离 |
| Codex App Server session | App Server client 初始化连接，创建/恢复 Thread，启动 Turn，消费双向 JSON-RPC/JSONL 事件 | `REUSE` | 绑定 session snapshot、审批/沙箱/模型/Scope，记录 Thread/Turn/Item/Usage/approval audit |
| Retries | clean exit continuation、failure exponential backoff、stall timeout、retry queue | `EXTEND` | 加入 Task 总边界、reason_code、no-progress、budget/stop circuit breaker、有限返工和升级 |
| Concurrency | global/per-state limits，poll tick 中按 slot dispatch | `EXTEND` | 加入 transactional reservation、唯一 execution lease、资源隔离、逐步扩容 Gate；V1 先用两个 Worker slots |
| State | authoritative in-memory orchestrator state，tracker refresh/reconciliation，restart 可恢复但不恢复精确内存状态 | `EXTEND` | 持久 Control Plane State、版本、DAG、AC、Evidence、CI、lease、checkpoint 和事件重建 |
| Recovery | worker exit、stall、active/terminal refresh、startup terminal workspace cleanup | `EXTEND` | fencing、Git/CI reconciliation、幂等外部动作、backup/restore、Kill Switch 和 Human Decision |
| Tracker abstraction | adapter、normalized issue、provider-native tool extension、tracker credential 可由 host 注入 | `REUSE` | tracker 不是控制面真相；跨 Project/Secret Scope、写入 policy 和 Acceptance Contract 由 Control Center 控制 |
| Observability | structured logs、issue/session context、runtime events、token/rate-limit aggregate、可选 status surface | `EXTEND` | append-only Evidence/Audit hash chain、trace correlation、Review/Gate、Token/Cost Ledger、Security/Decision surface |

## 关键协议对齐

目标客户端必须执行：

```text
open transport
  -> initialize once
  -> initialized
  -> thread/start or thread/resume
  -> turn/start
  -> consume bidirectional notifications/requests
  -> turn/completed or explicit failure/cancel
```

协议支持 JSON-RPC 2.0 语义；默认 stdio transport 为 newline-delimited JSON。App Server 可通过 server-initiated requests 请求 command/file-change/permission approval 或 user input；客户端必须用确定性策略响应，不能让运行无限挂起。Thread 是可持久、可恢复的会话容器，Turn 是一次工作单元，Item 是输入/输出/工具/变更等原子事件。

## 为什么不能只复用 Symphony

Control Center 仍需要以下明确增量：

- transactional state：确保状态、预算、lease 和事件原子一致；
- lease/fencing：防止 Crash/Restart 后双 Worker 写入；
- deterministic policy：让权限、License、网络、Secrets、Production 和 Main Gate 可机械拒绝；
- acceptance contracts：冻结 Requirement/AC，完成不依赖自然语言；
- independent review：把实现与审核分离；
- evidence notarization：保存 Commit、CI、Review、Approval、hash chain 和不可覆盖证据；
- token/cost ledger：区分 raw usage、subscription/API billing 和 estimated/actual cost；
- Dashboard：以中文为主展示 Agent Activity、当前/最近/下一步、Blocked、Security、Cost 和 Kill Switch；
- Human Decision/autonomy gates：为高风险动作保留 Human Owner 否决权。

## 采用与替换边界

采用 upstream primitives 不代表复制 upstream 实现。目标版本升级时必须重新生成 schema、执行 protocol probe、更新本文件和 Evidence；如果上游协议与本文件的协议字段描述冲突，以目标 App Server schema 为协议真相，以本文件为 Control Center 编排与安全真相。

## 当前结论

上游关系已完成架构对齐；不存在重造 Symphony dispatch/workspace/retry/session primitive 的授权。E-1/E-2 未通过前，不实现正式 Orchestrator、Dashboard、多 Agent runtime 或正式 DB schema。

