# AI Development Control Center
# 07 — Sol Final Architecture Arbitration
## 最终架构仲裁与冻结修订

**Status:** APPROVED FOR ARCHITECTURE FREEZE, SUBJECT TO E-1 / E-2 FEASIBILITY
**Product Implementation:** NOT YET AUTHORIZED

## 最终结论

接受 `06-FINAL-ARCHITECTURE-CONVERGENCE.md` 的主架构与 11 个 P0 Capabilities，并停止全面架构复审。

核心心智模型：

> 推理层提议，控制面决定，执行层动手，验证层作证，GitHub 把门，证据层留痕。

下一步不是直接写 Dashboard / Orchestrator，而是先：

1. 对齐 OpenAI 官方 Symphony / Codex App Server；
2. 执行 E-1 Restricted Runtime Feasibility；
3. 执行 E-2 Independent Verification Feasibility；
4. 两项通过后才进入产品实现。

---

## A1 — Symphony Upstream-First

OpenAI 已公开 Symphony，其目标与本项目高度重叠：长运行 orchestrator、任务驱动 agent、独立 workspace、bounded concurrency、crash/retry、Codex App Server、observability。

正式实现前必须建立：

`docs/ai-control-center/UPSTREAM-SYMPHONY-DELTA.md`

对每项能力标记：

- REUSE
- EXTEND
- REPLACE
- NOT_APPLICABLE

原则：

> 不重新发明 Symphony 已经提供且适用的 orchestration primitive。

本项目定位为：

> **Hardened Symphony-derived AI Development Control Center**

额外能力包括 transactional control plane、deterministic policy、acceptance contracts、independent review、evidence notarization、token/cost ledger、Chinese-first Dashboard、Human Decision、autonomy gates。

## A2 — Codex App Server 是首选 Runtime Interface

优先使用 Codex App Server / stable machine protocol 驱动 Codex。

禁止把以下方式作为核心控制协议：

- 鼠标点击 Codex Desktop
- UI scraping
- 模拟键盘输入多个 Codex 窗口

Codex Desktop 可以是人工观察窗口，不是机器控制协议。

## A3 — Token 与 Cost 分离

Dashboard 必须记录 Token Usage 与 Billing Mode。

Billing Mode：

- `chatgpt_subscription`
- `api_billed`
- `unknown`

若 API billed：

- usage × 版本化价格表 = API Cost

若 ChatGPT subscription：

- 不得把 API 单价乘 token 后称为“实际费用”
- 可以显示 `API-equivalent estimate`
- 必须标记“等价估算，并非实际扣费”

若 runtime 不提供 usage：

- 显示 Usage unavailable
- 禁止 Agent 自报补齐

## A4 — 模型版本变化的降级规则修订

不得因为每一次内部 revision 变化就自动降低 Autonomy Level。

必须降级：

- configured model ID / family 改变
- provider 明确 major model replacement
- Reviewer calibration 指标越过阈值
- false-PASS / regression 明显上升

仅 Shadow Recalibration：

- 内部 revision / resolved version 变化
- configured model 未变

处理：

- 标记 `baseline_stale`
- 后续 5–10 个任务提高抽样
- 指标正常后清除 stale
- 异常才降级

## A5 — License Policy 项目可配置

宪法不得硬编码 “GPL 永久 HARD DENY”。

架构原则：

> License policy 必须由确定性项目策略执行；未知许可证或命中项目 denylist 时不得自动放行。

具体 AGPL / SSPL / GPL 等策略属于 Project Policy / Runtime Config，不属于 Constitution。

## A6 — Bootstrap 权限与 Worker 权限分离

Worker 继续 HARD DENY：

- `brew install`
- `npm -g`
- 改系统用户
- 改系统网络
- 改 Keychain
- 改 branch protection

但首次系统安装可能需要创建专用 macOS 用户、安装工具链、设置凭证或网络。

这些属于：

**Human-authorized Bootstrap**

要求：

- 在 Worker 外执行
- 一次性或低频
- 留审计
- 不继承给 Worker
- 不成为 Worker 可调用工具

## A7 — Append-only 必须机械实现

V1 最低要求：

- 可变状态 DB role 与 audit writer role 分离
- Audit / Evidence app role 只有 INSERT + SELECT
- 无 UPDATE / DELETE
- 纠错写新 correction record
- 每条记录保存 `prev_hash`
- 机外备份

## A8 — Dashboard 保留 Agent / Done / Next

首页必须直接回答：

1. 系统是否在动
2. Director / Reviewer / Worker 此刻分别在做什么
3. 当前 Running Task
4. 最近完成了什么
5. 下一步自动准备做什么
6. 哪些 Blocked / Rework
7. 是否需要 Human Decision
8. Token / Cost 是否异常
9. 是否有 Security Event
10. Kill Switch

首页必须有 **Agent Activity Strip**：

- Role
- Model
- Task
- State
- Attempt
- Runtime
- Token
- Last event

项目详情必须有：

- 正在进行
- 最近完成
- 下一步队列
- Review / Rework
- Blocked

## A9 — 并行度从 2 起步

V1 = 2 Worker slots。

只有 E-10 与真实 pilot 证明资源隔离稳定后，才按：

2 → 3 → 4

逐步扩容。

## Final 11 P0 Capabilities

保留：

- C1 Control Plane Correctness
- C2 Leasing & Crash Recovery
- C3 Worker Isolation & Local Hygiene
- C4 Deterministic Policy Enforcement
- C5 Contract-first Acceptance
- C6 Independent Verification
- C7 Git & Integration Safety
- C8 Evidence & Audit
- C9 Budget & Runaway Protection
- C10 Human Loop & Notification
- C11 Backup & Disaster Recovery

全部实现同时受 A1–A9 约束。

## Product Implementation Gate

E-1 / E-2 未通过前，不允许开发：

- 正式 Orchestrator
- 正式 Dashboard
- 正式多 Agent runtime
- 正式生产 DB schema

E-1 或 E-2 失败：

- HARD STOP
- 只做局部架构修正
- 不得偷偷降低安全边界继续开发

两项 PASS 后才进入 Implementation Phase 1。
