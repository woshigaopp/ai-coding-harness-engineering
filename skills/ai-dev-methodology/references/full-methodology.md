# AutoMQ AI Coding 完整方法论参考

本 reference 保存用户关于大需求 AI coding 的完整思想脉络。`SKILL.md` 只保留高频执行规则；当需要评审、完善、解释或反推 skill 缺口时读取本文件。

## Contents

- [Source Documents](#source-documents)
- [Core Thesis](#core-thesis)
- [P^N Is A Structural Model](#pn-is-a-structural-model)
- [Experience-Shaped Implicit Constraints](#experience-shaped-implicit-constraints)
- [Zero Semantic Coupling Is Impossible](#zero-semantic-coupling-is-impossible)
- [N1 / N2 Model](#n1--n2-model)
- [Atomic Boundary](#atomic-boundary)
- [SDD Container Principle](#sdd-container-principle)
- [Major Change Workflow](#major-change-workflow)
- [Connect Multi-Tenant Case Study](#connect-multi-tenant-case-study)
- [Common Workflow Failure Modes](#common-workflow-failure-modes)
- [Skill Mapping](#skill-mapping)
- [Review Rule](#review-rule)

## Source Documents

| Source | Title | Role |
|---|---|---|
| https://www.feishu.cn/wiki/Q74owBviEiYy8KkW1VhcHjG1npg | 零耦合代码模型不可能解决所有问题 | 证明跨模块语义耦合是问题域固有属性 |
| https://automq66.feishu.cn/wiki/XZN1w1hDDifHhIk6jpQcOtddnWe | 如何定义 AI 写代码的原子能力边界 | 定义 AI 原子任务的 5 个必要条件 |
| https://automq66.feishu.cn/wiki/CMSRwUZtqiBSKnkCOWvcHbsfnKe | AI Code 的正确性分析：从原子能力到大需求的衰减机制 | 分析 P^N、错误传播、上下文溢出、隐式决策 |
| https://automq66.feishu.cn/wiki/TFcRw9CTUiL0bskJKiLcAhC7nCd | 大改动开发工作流 | 旧设计考古、新设计、差异分析、模块设计实现 |
| https://automq66.feishu.cn/wiki/GH63wYeG1iR6SlkA00XcRZffnwb | Connect 多租户模式评审讨论清单 | Q1-Q21 决策前置案例 |
| https://automq66.feishu.cn/wiki/ApOjwMmx6i4lqVkbaoAcnup7nab | 问题收敛 | Connect 多租 29 个收敛 commit 分类证据 |

如果需要原文细节，使用 `lark-cli docs +fetch --doc <url> --as user` 拉取最新正文。

## Core Thesis

AI 对小需求的原子能力已经很强，但大需求不能简单理解为“小需求串联”。大需求失败的核心不是 AI 单点不会写代码，而是：

- 决策点数量多。
- 跨模块语义约束不可消除。
- 隐式约束没有被显式化。
- 子任务错误会污染后续任务输入。
- 验证常常后置，导致错误积累后才暴露。

目标不是承诺“大需求零收敛”，而是把可避免收敛压缩掉，让剩余收敛接近问题域固有的跨模块语义约束数量。

## P^N Is A Structural Model

`P^N` 是衰减结构的启发模型，不是严格概率公式。

- 小需求中，单个任务正确率 P 很高，因为上下文完整、决策少、验证短。
- 大需求中，N 是决策点、隐式约束、跨模块契约、验证边界的数量。
- 如果每个点成功率都很高，N 足够大时整体偏离仍会明显。
- 真实情况通常比独立事件的 P^N 更差，因为错误会传播。

因此优化方向不是“让 AI 更聪明一点”，而是改变问题结构：

1. 决策前置，消灭实现阶段低 P 的选择题。
2. 契约显式化，把 N2 变成可枚举、可验证的列表。
3. 原子任务自包含，切断错误传播。
4. 每步短验证，让错误不进入下一步。

## Experience-Shaped Implicit Constraints

“隐式约束必须显式化”还隐含一个前提：workflow 必须先知道哪些东西算隐式约束。

隐式约束不只来自旧代码、PRD 空白、AIP 缺口和跨模块语义耦合，也来自人类工程经验。人类工程师看到某些问题形状时，会自然展开一组必须检查的语义；AI 不能稳定依赖这种直觉。

典型例子：

- 看到 lifecycle、progress、event、status、terminal，就会追问状态流转、事件名、生产者、消费者、终态、失败态、轮询、重试和前端展示。
- 看到 frontend action，就会追问按钮入口、route、API、loading、success、error、权限、mode 分支和反馈闭环。
- 看到 mock acceptance / repo-specific acceptance runtime，就会追问 mock 边界、fixture graph、真实代码路径、前后端矩阵和状态推进是否可验收。
- 看到 provider selector，就会追问默认值、已有/自动创建、空态、加载态、错误态、父子联动、非法候选和是否禁止 raw text。
- 看到 auto-create、default-created、generated resource、managed resource、select-existing 或 existing external resource，就会追问真实 provider/API 是否创建资源、资源 ID/name/tag 如何持久化、owned/existing provenance 谁维护、runtime 谁消费、update/delete 如何 cleanup 或 protect、失败/幂等/回滚如何表达。
- 看到新 mode、新资源类型、新生命周期或持久化 mutation，就会追问旧字段/旧表/旧 mapper 的必填约束是否仍成立、哪些旧字段在新 mode 下可空/派生/禁止写入、真实 state owner 是谁、哪个 writer 落库/落资源、哪些 list/detail/progress/event 需要 readback。
- 看到 permission、observability、derived config，就会追问可见性、允许操作、指标标签、空/错误查询、来源优先级、fallback 和缺失字段行为。

这些不是独立于方法论之外的新规则，而是“隐式约束显式化”的必要推论：

1. 大需求 workflow 的目标是生成零决策 Atomic Issues。
2. 零决策成立的前提是所有需要建模的语义都已被识别。
3. “识别哪些语义需要建模”本身不能依赖 AI 临场直觉。
4. 因此方法论必须把常见工程问题形状沉淀成触发器、矩阵、sidecar 和 gate。
5. 这些经验型隐式约束最终必须进入 semantic carriers 和 Atomic Issue 执行章节，否则实现阶段仍然保留自由决策空间。

因此“决策前置”前面还必须有“决策面发现”。AI 不能稳定凭 purpose 自行想到所有需要决策的 surface；workflow 必须先强制枚举 mode consumer、capability、frontend action、post-create consumer、persistent mutation、runtime lifecycle、mock acceptance / repo-specific acceptance runtime、observability、permission 和 compatibility。每个 surface 都必须回答：是否支持、如何支持、不支持如何表达、谁提供契约、谁消费、谁实现、谁验证、哪个 Atomic Issue 负责。未枚举的 surface 不会自动进入 Atomic Issue，这是比“决策做错”更早的 failure mode。

这层机制的目标不是为某个需求硬编码经验，而是把反复出现的人类工程直觉制度化。一次收敛事故只有在满足三个条件时才应进入方法论：它能泛化到一类需求；AI 容易用自然语言压缩或漏掉；它可以被结构化成 artifact 并被验证。否则只应作为需求本地决策或普通实现修复。

## Zero Semantic Coupling Is Impossible

零耦合证明的关键结论是：跨模块语义耦合不是工程实现缺陷，而是问题域固有属性。

例子：

- 电商：支付、库存、物流必须协作。
- 权限：用户、角色、资源共同决定操作是否允许。
- Connect 多租：Connector 能否创建取决于 Worker 集群状态。

消息队列、事件、接口抽象只能降低实现耦合，不能消除语义耦合。只要规则谓词涉及两个以上实体状态，就必须有一个地方同时理解这些实体，这就是耦合。

所以 workflow 不追求“消灭耦合”，而是：

- 模块内部高内聚，让 N1 不传播。
- 跨模块语义约束显式枚举，锁定 N2。
- 对每条 N2 contract 定义 Trigger、Normal path、Failure path、Consistency、Timing、Verification。

## N1 / N2 Model

| Type | Meaning | Goal |
|---|---|---|
| N1 | 模块内部子任务、工程纪律、局部实现、pattern、框架语义 | 通过 Atomic Issue、短验证、pattern、考古消除收敛 |
| N2 | 问题域固有跨模块语义约束 | 无法消除，只能显式枚举、锁定、验证 |

理论最优不是 0 收敛，而是收敛范围只剩 N2。

如果出现编译修复、字段遗漏、i18n、UI 文案、API path 404、旧约束漏挖、测试后补，通常是 N1 avoidable，不应归因于大需求固有复杂度。

## Atomic Boundary

一个 AI 原子任务必须同时满足 5 条：

| Condition | Meaning |
|---|---|
| 零决策 | 产品、架构、字段、错误、UI、兼容性等选择已锁定 |
| 单层变更 | 只触达一个细层，如 backend service、API、frontend types、DB migration |
| 上下文自包含 | 任务本体包含执行所需代码参考、规则、pattern、契约摘录 |
| 验证闭环短 | 完成后能立即编译、测试、lint、route smoke、render、plan 或手动验证 |
| 错误不传播 | 当前任务失败不会污染后续任务输入 |

重要区别：

- checklist item 不是原子任务。
- “引用 REQ/C/DEC ID”不是上下文自包含。
- 真正原子任务必须是 self-contained Atomic Issue。

Atomic Issue 判定：

> 一个 worker 只拿到 `atomic-issues/Txxx.md` 和其中列出的文件路径，就能完成任务、验证结果、且不做新决策。

如果需要读完整 `proposal/spec/plan` 才知道怎么做，该任务不合格。

## SDD Container Principle

SDD 文件只作为容器：

- `proposal.md`: 为什么做、范围、非目标、source inputs。
- `spec.md`: 用户可见行为、REQ/SCN、API/状态/错误语义。
- `plan.md`: 技术方案、决策、考古、迁移、契约、验证矩阵导航。
- `tasks.md`: sealed 任务索引、顺序和初始状态；执行状态、verification log 和 task passed receipt 必须放在 `workflow-state.yaml.task_receipts`、`task-verification-log.yaml` 或 `execution-state.yaml`。

但 AutoMQ AI workflow 的质量标准不受 SDD 轻量模板限制。如果需要更多文件，必须新增：

- `atomic-issues/Txxx.md`
- `contracts/*.md`
- `verification/*.md`
- `archaeology/*.md`
- `frontend-contract/*.md`
- `decision-review.md`

原则：

> SDD defines artifact slots; AutoMQ AI workflow defines artifact quality.

## Major Change Workflow

已有功能大改不能只从新需求直接实现，必须分阶段：

1. 旧设计考古：读代码、读测试、读 git 历史、读文档/注释、可行时跑代码。
2. 新设计：暂时放下旧实现，从需求推导理想模块边界和语义。
3. 差异分析：逐项比较旧/新语义，决定 delete/keep/modify/add。
4. 模块设计与实现：把锁定设计变成 Atomic Issues 并执行。

考古不只是“看代码做什么”，而是挖：

- 为什么这样写。
- 哪些代码看起来能删但不能删。
- 哪些边界处理来自历史 bug。
- 哪些兼容逻辑不能破坏。
- 哪些框架方法语义容易被 AI 误解。

## Connect Multi-Tenant Case Study

Connect 多租改造提供了反例证据。

29 个收敛 commit 分类：

| Category | Count | Interpretation |
|---|---:|---|
| 编译/测试修复 | 3 | N1，可通过每步短验证捕获 |
| Task 管道 Bug | 2 | N1，框架语义未显式化 |
| 数据读写链路不一致 | 4 | N2 或 contract-miss |
| override.policy 设计反复 | 3 | AIP/contract 决策缺口 |
| 前端 i18n/UI 修复 | 7 | N1，前端 pattern/微决策未锁 |
| API/权限/VO 修复 | 4 | archaeology/contract/pattern miss |
| 关键 Bug | 1 | 跨模块契约漏列 |
| 重构清理 | 4 | migration diff 不完整 |
| code review 修复 | 1 | pattern/quality checklist 缺口 |

结论：

- 大约 8 个属于跨模块语义约束相关收敛，接近 N2。
- 其余大量是 N1 avoidable。
- 这些不该靠“实现后反复修”解决，而要反哺 skill：考古、契约、Atomic Issue、验证矩阵、前端契约。

## Connect Review Q1-Q21 As Decision Precedence Example

Connect 多租评审清单的意义不是具体答案，而是展示“大需求必须前置决策”的密度。

典型问题：

- 插件集管理策略。
- 插件版本冲突。
- 内部 topic partition。
- 敏感字段加密。
- 容量预检。
- autoscaling 策略。
- IAM 权限聚合。
- Connector 间配置可见性。
- worker_config / override.policy。
- Worker 未就绪时 Connector 创建行为。
- 名称唯一性。
- initial_offsets。
- offset 清理。
- 删除 Worker 集群行为。
- 状态模型分离。
- 指标和日志多租户拆分。
- rebalance 策略。
- 滚动重启期间状态展示。
- 单租到多租 offset 迁移。

这些都是实现阶段不能让 AI 临场决定的问题。任何一个未锁定，都会把执行任务从高 P 的实现题变成低 P 的决策题。

## Common Workflow Failure Modes

| Failure | Category | Fix |
|---|---|---|
| `tasks.md` 每项只有几行 | `atomic-issue-not-self-contained` | 生成 `atomic-issues/Txxx.md` |
| 为了符合 SDD 模板压缩内容 | `sdd-template-overfit` | SDD 只做容器，新增 artifact |
| API 写了 `/connect/templates:match` 但没测最终 URL | `verification-miss` / `contract-miss` | Public API contract + api-route smoke |
| Controller path 拼接导致 404 | `framework-semantics-miss` / `verification-miss` | 考古 Spring path semantics，MockMvc/WebMvcTest 覆盖 exact path |
| 前端 UI 多轮改文案/状态 | `pattern-miss` | frontend-contract 指定参考页面、字段表、状态矩阵 |
| 旧字段/兼容行为漏改 | `archaeology-miss` / `migration-diff-miss` | 旧设计考古 + 旧/新语义对比 |
| 新 mode 创建时被旧表/旧字段必填约束卡死 | `experience-shaped-implicit-constraint-miss` / `migration-diff-miss` / `verification-miss` | 触发 persistent mutation/schema compatibility 审计，锁定 state owner、schema/null/default、writer 和 readback proof |
| auto-create/select-existing 外部资源只做了 selector/validation，没有真实资源创建、ownership 持久化或删除保护 | `experience-shaped-implicit-constraint-miss` / `contract-miss` / `verification-miss` | 触发 Managed Resource Ownership surface，锁定 provider writer、resource identity、owned/existing provenance、runtime consumer、cleanup/protect 和 provider/readback/cleanup proof |
| 测试后补而非前置 | `verification-miss` | Verification Matrix 写入 Atomic Issue |
| 写了“实现事件/进度/mock graph”但没有状态行 | `experience-shaped-implicit-constraint-miss` | 触发 stateful behavior matrix，列 producer/consumer/from/to/terminal/failure/mock fixture |
| 写了“mode-specific UI action”但按钮仍指向旧页面 | `experience-shaped-implicit-constraint-miss` | 前端 action-flow 矩阵必须覆盖 action -> route -> API -> feedback |
| 新 mode 创建成功但 logs/metrics/connector/update/delete 等创建后能力运行时报错 | `decision-surface-discovery-miss` | 触发 Mode Consumer Matrix、Capability Support Matrix 和 Post-Create Consumer Audit，逐 consumer 锁定 supported/hidden/disabled/unavailable/implementation-required |

## Skill Mapping

| Theory | Skill responsibility |
|---|---|
| 产品决策前置 | `product-requirement-design` |
| AIP 工程决策前置 | `aip-readiness-review` |
| 决策不丢失 | `decision-registry` |
| 旧系统事实和框架语义 | `code-archaeology-sdd` |
| 经验型隐式约束识别 | `code-archaeology-sdd` / `frontend-contract-design` / `verification-matrix` / `mock-acceptance-gate` |
| 决策面发现 | `product-requirement-design` / `requirement-readiness-review` / `code-archaeology-sdd` / `frontend-contract-design` / `cross-module-contract-sdd` / `atomic-task-planning` |
| 理想新设计 | `new-feature-design` |
| 旧/新语义差异 | `migration-diff-analysis` |
| 前端微决策 | `frontend-contract-design` |
| N2 显式锁定 | `cross-module-contract-sdd` |
| 验证前置 | `verification-matrix` |
| 原子 issue 生成 | `atomic-task-planning` |
| 原子 issue 执行 | `atomic-execution-sdd` |
| 收敛反哺 | `convergence-retrospective` |

## Review Rule

当用户问“当前产物是否符合我的思想”，不要只检查是否有 `proposal/spec/plan/tasks`。

具体 artifact 标准以 `artifact-completeness-spec.md` 为准；本节只列 review 时必须关注的高层问题。

必须检查：

- 是否有完整 Decision Registry。
- 是否所有 open decisions 已锁定或进入 decision-review。
- 是否完成旧代码考古和隐式约束挖掘。
- 是否完成旧/新语义差异和迁移计划。
- 是否每条跨模块契约有 Trigger/Normal/Failure/Consistency/Timing/Verification。
- 是否每条 verification 有 expected result 和 proves。
- 是否每个任务有 self-contained Atomic Issue。
- 是否 Atomic Issue 不读完整全局文档也能执行。
- 是否 SDD 模板没有限制必要 artifact 的生成。
