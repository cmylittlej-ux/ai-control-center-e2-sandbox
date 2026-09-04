# Git 与 Worktree 规则

状态：`FROZEN — GIT/GITHUB GATES`

## Branch 与 Worktree

- `main` 受保护，仅 Human Gate 之后才能改变。
- Task 使用包含 Project/Task 标识的独立 Branch 和 Worktree；返工使用新轮次引用，保留历史。
- Integration 使用受控 Branch/Queue 和独立 Worktree；Worker 不写 Integration 或 main。
- Reviewer 和权威 CI 使用只读或完全独立的 checkout；任何 active writer lease 不能共享。
- Workspace 路径必须在配置根目录内，cwd 必须等于当前 Task Worktree；越界即拒绝。

## Worker 权限

Worker 无权 force push main、修改 Branch Protection、修改权威 CI、删除 Evidence、写其他 Project 或重置其他 Task 的 Worktree。Bootstrap 权限不继承给 Worker。

## Commit 与证据

每个可审变更必须有 Commit SHA、父 Commit、Project/Task/Execution/Agent metadata、Diff、测试命令和工作树状态。未提交 Diff 只能作为中间状态，不能作为完成证据。

## Integration

Integration Queue 只接受通过 Review Gate、AC mapping、权威 CI、Policy Check、Project ID 校验和 Base Drift 检查的证据包。冲突或漂移时暂停并进入 `BLOCKED` + reason_code；禁止强制覆盖。Integration 成功必须有 merge/cherry-pick 记录、集成检查和回滚证据。

## GitHub 权威验证

E-2 的权威验证优先使用 GitHub-hosted ephemeral runner。Worker credential 只能触发和读取允许的 checks，不能修改 Branch Protection、force push main 或删除权威 evidence。若平台权限模型无法形成该边界，必须记录为 Gap，不得把本地或持久 self-hosted Mac runner 当权威替代。

## Main 与回滚

Main protection 必须要求所需 checks、独立 Review、Integration Evidence 和 Human Approval。回滚记录为新事件并保留原 Commit、Review、CI、Usage 和失败证据；修复使用新 Task。

