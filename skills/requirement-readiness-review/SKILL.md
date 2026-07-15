---
name: requirement-readiness-review
description: 需求和 AIP 进入工程 workflow 前的门禁。Use before code archaeology, new-feature design, or implementation to review whether product requirements and AIP decisions are clear enough, identify unresolved product/architecture decisions, determine required specs/changes artifacts, and prevent AI from making product or architecture decisions during coding.
---

# Requirement Readiness Review

## 目的

在任何考古、设计或实现前，确认输入是否足够。

本阶段是聚合门禁，不替代 `product-requirement-design` 和 `aip-readiness-review`。
它不写代码，不做技术实现细节推断。它只回答：

1. 需求是否定义了用户视角的产品行为。
2. AIP 是否锁定了工程设计决策。
3. 还有哪些问题会导致 AI 在实现阶段自作主张。
4. 需要哪些 `specs/changes` artifacts。

Readiness 不是 SDD 模板检查。必须按 `ai-dev-methodology/references/artifact-completeness-spec.md` 判断后续阶段需要哪些 artifact，以及当前 PRD/AIP 是否满足 Stage 1/2 的完整度标准。

本阶段发现的 readiness 阻塞项、阶段路由选择、是否允许进入下一阶段等决策，必须写入 `specs/changes/<change-id>/decision-reviews/readiness-decisions.md`，使用或等价满足 `ai-dev-methodology/templates/stage-decision-document.md`，并同步进入 Decision Registry。有 `open` 产品或架构决策时不得进入考古、设计或实现。

## 输入

- 需求文档、PRD 草稿、飞书文档、issue、标题或对话输入。Readiness 中一律视为 Propose / Source，除非它是本 workflow 生成并通过 PRD Completeness Gate 的 PRD。
- AIP 或工程方案。
- Product Requirement Design 输出，如果有。
- AIP Readiness Review 输出，如果有。
- `decision-surface-discovery.md`，如果需求涉及新/改 mode、创建后能力、前端 action、runtime capability、persistent mutation、mock/playground，或用户只给 purpose。
- Decision Registry，如果已有。
- 目标仓库 / 产品范围。
- 如有：已有 `specs/changes/<change-id>/`。

## 检查维度

### 1. 产品语义门禁

首先判断当前所谓“PRD”是否真的是 workflow-owned PRD：

| 检查项 | 要求 |
|---|---|
| Source intake | 所有输入已登记，包含对话输入 |
| Propose extraction | 已从每个 source 抽取 propose statement、明确事实、推断事实、未知决策 |
| Workflow-generated PRD | PRD 是本 workflow 重新生成，不是直接接受外部文档 |
| Current Product/Code Understanding | 写 PRD 前已理解相关当前项目代码/产品现状，并有 evidence path |
| User/AI decision authority | 未授权 AI 产品决策时，每个待决策点已由用户确认 |
| PRD Completeness Gate | 没有 `Blocks next stage=yes` 的 incomplete 维度 |

如果输入只是飞书文档、issue、用户对话或 PRD 草稿，但没有上述产物，判定为 `blocked-by-prd-not-generated`，必须回到 `product-requirement-design`。

需求文档必须回答：

| 维度 | 必须明确 |
|---|---|
| 用户/场景 | 谁使用，解决什么任务 |
| 范围 | 哪些能力在 scope 内 |
| 非目标 | 哪些明确不做 |
| 配置 | 用户能配置什么，默认值是什么 |
| 状态 | 用户能看到哪些状态，状态含义是什么 |
| 错误 | 失败、不可用、unknown 怎么表达 |
| 权限 | 谁能创建、修改、查看、删除 |
| 兼容 | 旧用户/旧配置/旧 API 如何表现 |
| 产品决策 | 模糊点是否已有明确选择 |

如果需求涉及云资源、部署模式、托管资源，或要求“参考现有 X 实现 / 与 X 类似 / 复用 X 模式”，必须额外检查：

| 维度 | 必须明确 |
|---|---|
| 参考实现 | 参考对象是什么，是否已完成 UI/API/后端/任务/云资源全链路考古 |
| 参数归属 | 每个云资源参数是用户选择、后端自动创建、从已有资源推导、环境固定，还是不支持 |
| 空 payload | 前端不传字段时是否合法，后端必须补齐哪些字段 |
| 缺失行为 | 参考对象缺少源字段时，是阻塞、补选、自动创建，还是降级 |
| 错误语义 | 用户看到哪个字段/资源缺失，而不是笼统 invalid |

缺少参考实现字段矩阵或参数归属表时，判定为 `blocked-by-product-decision`，不得进入实现。

如果需求新增或修改 deployment/runtime/compute/storage/network mode，必须额外检查“同级模式差异矩阵”：

| 维度 | 必须明确 |
|---|---|
| 模式地位 | 新 mode 是否与旧 mode 同级，而不是旧 mode 的子分支 |
| 能力差异 | 创建/更新/删除、事件、状态、日志、Worker、Endpoint、Metrics、插件验证等能力逐项 same/different/unavailable |
| 配置差异 | 同名字段是否语义相同；不同语义是否拆成独立配置 |
| UI 差异 | 每个页面区域在各 mode 下 show/hide/disabled/unavailable |
| 运行时差异 | 云资源、任务、状态回写、endpoint discovery、日志采集的 mode-specific 行为 |
| Evidence | PRD、AIP、Terraform/API 设计、代码考古、运行时样本之间是否一致 |

缺少同级模式差异矩阵时，判定为 `blocked-by-product-decision`。不得通过“参考现有实现应该能推断”来放行，因为已有实现通常只证明旧 mode 语义，不证明新 mode 可继承。

如果用户提供了补充设计链接、Terraform/API 设计、飞书文档或 issue，Readiness 必须检查这些输入是否已被读取并进入 Source Trace / Evidence。未读取用户提供的补充设计文档时，判定为 `blocked-by-input-not-normalized`，不得进入考古、设计或实现。

如果 PRD 缺少 Current Product/Code Understanding，或该理解没有具体 evidence path / command，判定为 `blocked-by-current-context-missing`。不得让 AIP、设计或实现阶段替 PRD 补当前产品语义。

如果需求只给 purpose，或涉及新/改 mode、创建后能力、前端 action、runtime capability、persistent mutation、mock/playground，但缺少 Decision Surface Discovery，判定为 `blocked-by-decision-surface-missing`。Readiness 必须检查每个 surface 是否有 owner stage、产品/工程决策状态、后续 artifact 和验证路线；不能只检查 PRD/AIP 是否看起来完整。

### 2. AIP 决策门禁

AIP 必须回答：

| 维度 | 必须明确 |
|---|---|
| 方案方向 | 推荐方案是什么 |
| 备选方案 | 至少列出重要反选方案及拒绝原因 |
| 接口 | OpenAPI / Terraform / CLI / 内部 API 变化 |
| 数据/状态 | DB、状态机、事件、任务模型变化 |
| 部署 | K8s、云资源、Helm、Terraform、权限 |
| 观测 | metrics、logs、events、alerts、runbooks |
| 兼容 | 升级、回滚、旧字段、旧行为 |
| 验证 | 哪些行为如何证明正确 |

### 3. AI 原子边界风险

标记所有会破坏原子执行的点：

- 含产品判断。
- 含架构选择。
- 跨层一致性没有契约。
- 旧代码隐式约束未考古。
- 决策面没有被发现：mode consumer、capability、frontend action、post-create consumer、persistent mutation、runtime lifecycle、mock/playground、observability、permission、compatibility 缺行或 owner。
- UI/前端 pattern 未指定。
- 验证方式不明确。

### 4. Decision Registry 一致性

检查所有产品和 AIP 决策是否已经登记：

| 检查项 | 要求 |
|---|---|
| 产品决策 | 用户可见行为、配置、状态、错误、权限都有 PDEC/DEC |
| 工程决策 | 方案取舍、接口、兼容、观测、验证都有 DEC |
| open decision | 任何 `open` 都阻塞实现 |
| source | 每个决策能追溯到需求、AIP 或用户确认 |
| affected modules | 每个决策说明影响范围，供任务拆分使用 |

### 5. 后续阶段判定

```markdown
| 阶段 | Required? | Reason |
|---|---:|---|
| product-requirement-design | yes/no |  |
| aip-readiness-review | yes/no |  |
| new-feature-design | yes/no |  |
| code-archaeology-sdd | yes/no |  |
| migration-diff-analysis | yes/no |  |
| frontend-contract-design | yes/no |  |
| cross-module-contract-sdd | yes/no |  |
| verification-matrix | yes/no |  |
| atomic-task-planning | yes/no |  |
```

## Local Audit Gate: Readiness Independent Audit

Readiness verdict 输出后、允许进入考古/设计/实现前，主 agent 必须本地二次审计 readiness 结论。本地审计只复核输入完整度和路由决策，不替主流程做产品或架构决策。

输入：

- Source Intake Ledger / PRD / AIP / Decision Registry。
- Current Product/Code Understanding 和 Current Architecture Understanding。
- PRD Completeness Gate、Engineering Decision Completeness Gate。
- Stage Routing 和 Blocking Questions。

输出：

```markdown
### Readiness Local Audit Report

| Audit scope | Verdict | Finding | Evidence | Required backflow | Blocks next stage |
|---|---|---|---|---|---:|
```

必须审计：

- 当前输入是否真是 workflow-owned PRD / locked AIP，还是只是外部文档 source。
- 用户补充链接、Terraform/API 设计、飞书文档是否已被纳入 PRD/AIP evidence。
- Product semantics ready / Engineering decisions ready 是否有对应 completeness gate 支撑。
- Stage Routing 是否漏掉 code archaeology、frontend contract、cross-module contract、verification matrix、mock/product acceptance。
- Decision Surface Discovery 是否存在，且每个 surface 都路由到 owner stage / locked N/A；是否漏掉创建后消费者、运行时能力、前端 action 或持久化 mutation。
- Decision Registry 是否存在 open decision、冲突 decision key 或未记录的阶段决策。

阻塞条件：

- 未通过 PRD/AIP completeness gate 却放行下一阶段。
- 需新增/修改 mode、运行时能力、mock/playground、前端 action，却没有路由到对应阶段。
- 需新增/修改 mode、创建后能力、runtime capability、persistent mutation、mock/playground 或只给 purpose，却缺 Decision Surface Discovery，或 surface 行没有 owner stage / locked N/A。
- Stage Routing 漏掉任何后续必需 artifact。
- 有 open/blocking question 或 unread behavior-affecting source。

## 输出

写入或返回以下内容；如果使用 `automq-sdd`，同步到 `proposal.md` 的 Review Plan / Open Questions / Required Files。

```markdown
## Requirement Readiness Review

### Input Summary

- Requirement:
- AIP:
- Target repos:
- Product scope:

### Readiness Verdict

| 项 | 结论 |
|---|---|
| Product semantics ready | yes/no |
| PRD workflow-generated | yes/no |
| Current product/code understanding ready | yes/no |
| PRD completeness gate passed | yes/no |
| Engineering decisions ready | yes/no |
| Can enter archaeology/design | yes/no |
| Can enter implementation | yes/no |

### Blocking Questions

| ID | 问题 | 类型 | 阻塞阶段 | 建议决策方式 |
|---|---|---|---|---|
| BQ-001 |  | product/architecture/interface/compat/validation | design/implementation |  |

### Required Artifacts

| Artifact | Required | Reason |
|---|---:|---|
| proposal.md | yes |  |
| spec.md | yes/no |  |
| plan.md | yes/no |  |
| tasks.md | no | produced by atomic-task-planning after contracts and verification are locked |
| atomic-issues/Txxx.md | no | produced by atomic-task-planning as self-contained executable issues |
| current/<area> | yes/no |  |

### Decision Registry Seed

| Decision ID | Decision | Source | Status | Affected areas | Verification |
|---|---|---|---|---|---|
| DEC-001 |  | Requirement/AIP/User | locked/open |  |  |

### Stage Routing

| Next stage | Required? | Blocking reason if skipped |
|---|---:|---|
| product-requirement-design | yes/no |  |
| aip-readiness-review | yes/no |  |
| code-archaeology-sdd | yes/no |  |
| new-feature-design | yes/no |  |
| migration-diff-analysis | yes/no |  |
| frontend-contract-design | yes/no |  |
| cross-module-contract-sdd | yes/no |  |
| verification-matrix | yes/no |  |
```

## 退出规则

- 有 blocking question 时，不得进入 `atomic-execution-sdd`。
- 输入不是 workflow 生成且通过完备性校验的 PRD 时，不得进入 AIP/design/implementation 路径。
- PRD 缺少 Propose Extraction、Source Trace、Current Product/Code Understanding 或 PRD Completeness Gate 时，不得进入下一阶段。
- 用户未授权 AI 做产品决策时，未确认的产品决策不得被 AI 锁定。
- 产品语义不清，不得用技术方案替用户做决定。
- AIP 方案不清，不得通过代码考古倒推出架构选择。
- 依赖现有产品模式但没有参考实现字段矩阵和参数归属表时，不得进入实现。
- 用户提供的补充设计文档、Terraform/API 设计或飞书链接未纳入 PRD/AIP evidence 时，不得进入实现。
- 新增/修改 deployment/runtime/compute/storage/network mode 但没有同级模式差异矩阵时，不得进入实现。
- 对旧 mode 的 UI、事件、状态、日志、Worker、Endpoint、Metrics、插件验证等语义未逐项证明可继承时，不得默认继承。
- Readiness Local Audit Report 存在 `Blocks next stage=yes` 项时，不得进入下一阶段。
- Decision Registry 存在 `open` 决策时，不得生成可执行 tasks。
- PRD/AIP 未满足 artifact-completeness-spec Stage 1/2 时，不得进入 implementation-only 路径。
