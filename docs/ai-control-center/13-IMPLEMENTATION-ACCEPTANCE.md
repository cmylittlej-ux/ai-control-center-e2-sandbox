# 实施验收与 Implementation Ready

状态：`FROZEN — PHASE 0 GATED`

本文件只定义 Phase 0 之后的准入和验收，不授权本轮开发正式产品。

## Implementation Ready Gate

必须同时满足：

- `PHASE-0-FEASIBILITY-REPORT.md` 状态允许进入 Implementation Phase 1；
- E-1 Restricted Runtime 和 E-2 Independent Verification 达到各自最低 PASS；
- `OPEN-QUESTIONS.md` 中的阻塞项已由证据、Human Bootstrap 或明确决定关闭；
- 官方 Symphony/App Server Delta、目标 schema、模型/运行时版本和权限边界已冻结；
- Project Policy、License Policy、Billing Mode、预算、Kill Switch、审计 writer、备份恢复和人工审批边界已批准；
- 第一阶段只跑通受控 Control Kernel，不接入真实业务 Project，不开发正式 Dashboard。

## Phase 1 验收基线

- Symphony/App Server integration baseline 可启动并可恢复；
- Control Plane 事务状态、单实例锁、lease/heartbeat/fencing、幂等/dedup 和九状态 reason_code 通过测试；
- 一个 Generic Implementer 在一个隔离 Worktree 中完成受控 fixture task；
- 权威验证、独立 Review、Evidence Manifest、append-only hash chain 和 Kill Switch 可工作；
- Token、Billing Mode、API actual cost/API-equivalent estimate 语义可验证；
- Backup/Restore 能重建状态和证据索引。

## 两 Worker 试点 Gate

扩展到 V1 的两个 Worker slots 前必须通过隔离、冲突、Base Drift、CI 权限、lease expiry、数据库/端口/进程污染和 token burn 实验。扩容到更高并行度必须另有真实 pilot 证据；不默认扩到四个 Worker。

## 安全验收

必须证明 Worker 无法写 main、其他 Project、其他 Worktree、Branch Protection、权威证据或原始 Secrets；缺少 Commit/CI/Review/Integration Evidence 时无法 DONE；预算/Stop 边界会暂停；Crash/Restart/Timeout/Conflict 可恢复或安全阻塞；高风险动作需要 Human + Guardian；Event Log 可重建状态，重复命令不产生重复副作用。

## 明确非目标

不包含自动 Merge main、生产自动部署、无限 Agent、跨项目共享 Context、无审计外部写操作、公开远程访问、Jira-style Gantt、velocity/story points、AI ETA、multi-user RBAC 或真实业务项目改造。

