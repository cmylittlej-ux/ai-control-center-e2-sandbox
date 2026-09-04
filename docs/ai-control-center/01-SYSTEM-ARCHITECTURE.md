# 系统架构

状态：`FROZEN — REVISED FOR PHASE 0`

## 系统定位

Control Center 是一个 Hardened Symphony-derived AI Development Control Center：用 Symphony 适用的调度、Workspace、Agent Session、重试、并发、Tracker 和基础可观测性作为上游能力；在其上增加事务控制面、确定性策略、契约式验收、独立验证、证据公证、Token/Cost Ledger、中文优先状态面和 Human Autonomy Gates。

## 七层架构

### L1 — Human Governance

Human Owner、Constitution、项目授权、审批、Kill Switch、风险分级和自治等级。L1 永远拥有否决权。

### L2 — Project / Task Control Plane

Project Registry、Requirement、Acceptance Contract、Task、Dependency Graph、状态版本、预算预留、事务命令和持久化状态。该层是“控制面决定”的权威来源。

### L3 — Orchestration

Symphony-derived Poll/Dispatch、Eligibility、Bounded Concurrency、Retry/Backoff、Reconciliation、Batch Loop 和 Calibration Loop。Control Center 额外提供 lease/fencing、幂等、事务状态转移和自主性门禁。

### L4 — Workspace / Process Isolation

根据 Project/Task 创建确定性 Worktree，校验根目录包含关系，绑定写入 lease，隔离进程组、端口、临时目录、网络和凭证环境。Worker 不能访问 Worktree 外资源。

### L5 — Codex App Server Runtime

首选 Codex App Server 作为机器接口：JSON-RPC 2.0 语义、JSONL stdio、双向请求/通知、Thread/Turn/Item 生命周期、Approval/User Input 请求、Diff/Plan/Token Usage 事件。协议字段和传输以目标版本的官方 App Server schema 为准，Symphony 只控制编排行为。

### L6 — Independent Verification / Git Integration

权威 CI、Lint、Unit、Build、Integration、E2E、GitHub checks、PR/Integration Queue、冲突检查、Base Drift、回滚和 Main Protection。Worker 无权修改权威检查、Branch Protection 或主线。

### L7 — Evidence / Observability / Human Surface

Append-only Audit/Evidence、Token/Cost Ledger、Trace Correlation、Decision Inbox、Security Events、Agent Activity Strip 和未来 Dashboard。状态面是只读投影，不能反向改变控制面真相。

## Symphony upstream relationship

上游采用规则见 `UPSTREAM-SYMPHONY-DELTA.md`。复用 Symphony 已经适用的 primitives，不复制其代码；对 Codex App Server 协议不做自定义替代。Control Center 的额外安全、验证、审计和计费要求必须在上游能力之外显式实现并验证。

## 事实边界

- Symphony 是 scheduler/runner 与 tracker reader，不自动等同于完整事务控制面、Dashboard 或多租户系统。
- Codex App Server 是运行时机器接口，不是 Control Center 的状态真相。
- Codex Desktop 仅可作为人工观察面，不能作为机器控制协议；禁止 UI scraping 和模拟点击。
- V1 并行能力从低并行度开始，扩容必须由独立资源实验和真实 pilot 证明，不能把资源容量写成无限假设。

## 一致性与隔离不变量

- Task 状态转移使用版本校验；旧命令拒绝并产生日志。
- 一个 Task 同时只允许一个 active execution lease；租约失效先 fencing，再恢复。
- 一个 Worktree 同时只允许一个写入身份；Reviewer 和权威 CI 只读或使用独立环境。
- 状态、事件、证据和预算计量必须原子关联；无法计量时不能完成。
- 外部动作使用幂等键；重复请求不重复产生副作用。

