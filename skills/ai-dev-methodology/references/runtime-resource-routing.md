# Runtime Resource Routing

## 目录

- [身份与阶段构造](#身份与阶段构造)
- [设计与契约资源](#设计与契约资源)
- [任务与执行资源](#任务与执行资源)
- [验收与校验命令](#验收与校验命令)

## 身份与阶段构造

| 场景 | 必须使用 |
|---|---|
| workflow 首次启动或恢复 | `templates/workflow-workdir.md` |
| contextpack state | `templates/workflow-state-contextpack.yaml` |
| 标准 workflow state | `templates/workflow-state.yaml` |
| 阶段构造 | `references/stage-construction-protocol.md`、`templates/stage-construction-contracts.yaml`、`workflowctl.py prepare-stage/validate-obligation/validate-stage-construction` |
| 输入登记 | `templates/source-intake-ledger.md` |
| 代码范围发现 | `templates/code-scope-discovery.md` |

旧 active change 只能通过 `workflowctl.py migrate-workflow-runtime` 显式迁移。不得手改 runtime marker、stage status 或 receipt。

## 设计与契约资源

| 场景 | 必须使用 |
|---|---|
| 用户决策 | `templates/user-decision-interaction.md`、`templates/stage-decision-document.md`、`templates/decision-registry.md` |
| AIP propose / 外部事实 / 机制 | `templates/engineering-propose-intake.md`、`external-capability-research.md`、`mechanism-design-model.md` |
| 决策面 / 语义消费 | `templates/decision-surface-discovery.md`、`semantic-consumption-matrix.md` |
| 契约 / 覆盖 / 验证 | `templates/cross-module-contract.md`、`traceability-matrix.md`、`verification-matrix.md`、`verification-feasibility.md` |
| 状态与变体 | `stateful-behavior-matrix.*`、`existing-object-action-consumer-graph.md`、`variant-impact-matrix.md` |
| 外部副作用与 runtime | `progress-change-producer-chain-matrix.md`、`external-side-effect-contract-matrix.md`、`runtime-materialization-parity.md`、`runtime-test-topology-matrix.md` |
| 版本与评分 | `version-branch-alignment.md`、`artifact-rubric-scorecard.md`、`references/artifact-review-rubric.md` |

## 任务与执行资源

| 场景 | 必须使用 |
|---|---|
| Atomic Issue source | `templates/atomic-issue-packets.yaml` |
| Atomic Issue compiler | `scripts/atomic_issue_compile.py` |
| Atomic Issue format | `templates/atomic-issue.md`、`references/golden-atomic-issue.md`、`bad-atomic-issue.md` |
| DAG / sidecar | `task-dag.*`、`semantic-objects.yaml`、`contracts.yaml`、`verification.yaml`、`backflow.yaml` |
| review | `multi-perspective-review.yaml`、`task-semantic-review.yaml`、`atomic-issue-quality-review.yaml` |

## 验收与校验命令

| 目的 | 命令/资源 |
|---|---|
| 阶段结构校验 | `workflowctl.py validate <stage>` |
| 签收阶段 | `workflowctl.py pass-stage <stage>` |
| 全 artifact 校验 | `validate_artifacts.py <change-dir>` |
| 图与回流 | `workflowctl.py graph/backflow/reopen-stage` |
| 执行 | `begin-execution/admit-task/validate-task-diff/pass-task` |
| 上线收敛 | `templates/launch-readiness-review.md`、`validate-launch-readiness` |
| skill 回归 | `scripts/validate_skill_suite.py` |
| workflow 指标 | `workflowctl.py metrics <change-dir>` |

阶段 `passed`/`not_applicable` 只能由对应命令和 canonical receipt 写入。所有行为相关资源由 runtime manifest pin；修改后必须发布新 runtime 并运行 skill suite。

`workflow-events.yaml` 只提供可观测性，不是 workflow source of truth 或 admission evidence。`workflowctl.py metrics` 必须拒绝断链或篡改事件；事件链损坏不得阻断 canonical artifact、receipt 和 backflow 恢复路径，也不得用事件行替代 orchestrator、验证或 review 证据。
