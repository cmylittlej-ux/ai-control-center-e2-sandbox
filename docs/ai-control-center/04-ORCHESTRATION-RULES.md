# 编排规则

状态：`FROZEN — SYMPHONY-ALIGNED`

本文件定义 Control Center 如何复用 Symphony primitives，并叠加自己的控制面约束。它不是正式 Orchestrator 实现；本轮只建立行为契约和可行性验收边界。

## C1 — Control Plane Correctness

- Control Plane 对 Project、Task、Dependency、Acceptance Contract、Policy、Budget、Lease、Evidence 和 Integration 拥有唯一权威状态。
- 任意命令必须携带 `project_id`、目标版本、actor、作用域和幂等键；版本不匹配或重复副作用必须拒绝。
- 状态改变、预算预留、lease 变化和对应事件必须事务性提交。
- Dashboard、Agent 自报、Tracker 文本和 App Server 消息都不能直接成为 CLOSED 或集成事实。

## C2 — Leasing & Crash Recovery

- 每个 Execution 在运行前取得带 expiry 的 lease；Heartbeat 续租失败先 fencing，再允许恢复。
- Fencing token 必须在每个写入、状态转移、Commit 登记和外部动作前校验。
- 重启后先读取 Event/Checkpoint/Git/CI 外部事实，重建 authoritative state，再决定恢复、阻塞或取消。
- 恢复使用幂等键和退避；不能因重启产生第二个 Writer 或重复外部动作。

## Symphony primitives：采用方式

| 能力 | 策略 | Control Center 边界 |
|---|---|---|
| Tracker dispatch | `REUSE` | 采用候选读取、状态筛选、priority/created 排序和 active/terminal reconciliation；Task 真相仍由 Control Plane 管理 |
| Workspace | `REUSE + EXTEND` | 采用确定性 workspace key、root containment、cwd 校验和保留策略；扩展 Project/Task Worktree、lease、fencing 和环境隔离 |
| Codex App Server session | `REUSE + EXTEND` | 采用 JSON-RPC/JSONL、initialize、Thread/Turn/Item、双向通知和 schema；扩展 session snapshot、权限、审计和 Handoff |
| Retry / backoff | `REUSE + EXTEND` | 采用失败分类、退避和重试队列；扩展 Task 总边界、no-progress、Budget Hard Limit 和人工门禁 |
| Concurrency | `REUSE + EXTEND` | 采用 bounded slots、eligibility 和 per-state dispatch；扩展 transactional reservation、资源隔离和逐步扩容 Gate |
| Runtime state | `EXTEND` | 采用 Symphony 的运行态概念；用持久 State Store、版本、Event Log、Evidence 和恢复 checkpoint 提供更强控制面真相 |
| Recovery / reconciliation | `REUSE + EXTEND` | 采用启动清理和运行中状态刷新；扩展 lease/fencing、Git/CI 对账、断点恢复和灾备 |
| Tracker abstraction | `REUSE` | 采用 adapter、stable normalized issue、provider-native tool 边界；不把 tracker API 写死进核心 |
| Observability | `REUSE + EXTEND` | 采用 structured logs、session/issue context、token/rate-limit snapshots；扩展 append-only evidence、hash chain、trace correlation、Cost Ledger |

## Codex App Server 对齐

Runtime client 必须遵循目标 App Server schema：连接后单次 `initialize`，发送 `initialized`；使用 `thread/start` 或 `thread/resume`，再 `turn/start`；持续读取 `item/*`、`turn/*`、approval、user-input、diff、plan 和 token usage 事件，直到 `turn/completed` 或明确错误/取消。

`cwd`、sandbox、approval policy、model、effort 和 service identity 必须绑定到 Session Snapshot。运行时收到 server-initiated approval 或 user-input request 时，按确定性策略自动拒绝、交给 Human Decision 或终止为可解释失败，不能无限挂起。

## 调度顺序

Director 解析 Requirement → 冻结 Acceptance Contract → 建立 DAG → 计算 eligibility → Policy Check → 预算预留 → 创建 Workspace/Execution lease → 启动 App Server Session → 执行 → 独立验证 → Review → Integration。每个边界产生事件。

## 失败与停止

运行错误、测试 Hang、Git 冲突、Base Drift、权限拒绝、Token/Cost 异常、审计不完整或模型变更都必须映射到受控 `reason_code`。达到运行策略边界即停止；重新开始必须重新校验 Project、Commit、Budget、Policy 和 Lease。
