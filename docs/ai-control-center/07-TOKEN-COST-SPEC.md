# Token 与 Cost 规范

状态：`FROZEN — BILLING MODES EXPLICIT`

## Token Usage

每次 App Server/runtime usage 事件原样保存，再生成归一化 `UsageRecord`。不得假设事件一定提供 input、cached input、output、reasoning、total、context window 或 model version；缺失字段保存为 unavailable，不允许 Agent 自报补齐。

优先观察：

- `thread/tokenUsage/updated`：运行中 Thread usage 更新，字段以目标 App Server schema 和实际 Probe 为准；
- `account/usage/read`：ChatGPT 账户级 token activity summary/daily buckets，不等于单个 Task 的完整账单；
- API provider usage：只有 provider-confirmed 字段才可标记 actual。

Usage 记录必须包括 Project、Task、Execution、Thread、Turn、Agent、Model ID、resolved version、reasoning effort、事件时间、原始 payload hash、可用的 token breakdown、context window、source event 和 reliability。

## Billing Mode

每条成本聚合必须显式标记：

- `api_billed`：使用 provider-confirmed usage 与版本化价格表计算 API actual cost；估算和确认值分开。
- `chatgpt_subscription`：可以显示 token；可以显示 API-equivalent estimate，但必须明确“等价估算，并非实际扣费”；除非存在官方实际账单接口，不能称为实际费用。
- `unknown`：显示 Usage/Cost unavailable 或不确定；禁止用 API 单价推断实际费用。

## 价格与预算

API cost 绑定不可变 Rate Card Snapshot，保存模型版本、币种、单位、生效时间、来源和计算字段。Cached input 若是 input 子集不得重复计费；Total 以 provider 报告或明确归一化口径为准。

Task/Project/Agent/Global 预算、warning、hard limit、max runtime、max calls 和 burn-rate policy 必须在运行配置中显式声明。达到 Warning 记录异常并通知 Director；达到 Hard Limit 立即暂停并撤销 lease。重试、返工、Handoff、模型切换都计入同一账本，不能靠新 Thread 绕过。

## Dashboard 语义

Token 与 Cost 分别支持今日、本周、本月和日期下钻，并按 Project、Task、Agent、Model、Date 聚合。所有金额显示币种、billing mode、estimated/confirmed、数据更新时间和证据来源。订阅模式不得把 API-equivalent estimate 命名为实际成本。

