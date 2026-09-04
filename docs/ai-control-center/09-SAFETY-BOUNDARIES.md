# 安全边界

状态：`FROZEN — POLICY DRIVEN`

## Default deny

所有工具调用先校验 `project_id`、Task Scope、Role、Environment、目标资源、动作、能力 token、预算、Approval 和有效期。任何不匹配、缺失或过期都拒绝并记录 `POLICY_DENIED`。

## Worker 与 Bootstrap 分离

Worker 默认 HARD DENY：安装系统工具、全局包、修改系统用户/网络/Keychain、修改 Branch Protection、生产写入、读取原始 Secrets、访问其他 Project。首次安装专用 macOS 用户、工具链、凭证或网络属于 Human-authorized Bootstrap：在 Worker 外执行、低频、单独审计、最小范围且不继承给 Worker。

如果 Bootstrap 需要管理员密码，必须输出明确的 Human Bootstrap Request；不得绕过、猜测或假报已完成。Bootstrap 未完成时只能执行无权限预检。

## 可自动执行范围

在隔离非生产环境和有效策略内，可 Read/Search、创建计划、在 Task Worktree 开发、运行本地测试、提交 Task Branch、申请/执行受控 Rework、消费 Review 结果以及进入 Integration Queue。是否自动批准各动作由 Project Policy 决定，不能由 Agent 自行提升。

## 永久人工门

Merge main、Production Deploy、生产破坏性迁移/删除、删除生产资源、修改生产 Secrets/Billing/Security Boundary、不可逆外部操作和跨 Project 访问都需要 Human Owner 精确批准，并由 Guardian 在执行前复核一次性目标、Commit/版本、范围、有效期和回滚。

## License Policy

许可证策略是确定性的 Project Policy/Runtime Config，不在 Constitution 中硬编码 GPL/AGPL/SSPL 的永久结论。未知许可证或命中项目 denylist 不得自动放行；命中策略的动作进入 `BLOCKED` + `POLICY_DENIED`，由 Human/Project Policy 决定处理。

## Secrets、网络和身份

Agent 不接收原始 Secret；凭证只通过短时最小 capability 提供，日志、Prompt、Diff、Event、Artifact 和 Dashboard 做脱敏/扫描。网络使用 Project allowlist；生产网络默认关闭。Tracker credential 由 Host/Adapter 管理，不复制给 Codex child process。

## Kill Switch 与违规

Soft Stop 停止新 dispatch；Hard Stop 撤销 active leases 并阻止写入；Emergency Stop 还阻止外部副作用。发生越权、疑似泄密、审计篡改、Policy bypass、失控成本或污染时立即触发适用 Kill Switch，保留现场、冻结相关 Project/Task、告警并等待 Human。

