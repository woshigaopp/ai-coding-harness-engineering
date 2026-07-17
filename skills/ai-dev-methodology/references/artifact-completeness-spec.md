# Artifact Completeness Specification

本规格把 AutoMQ AI coding 方法论落实为每个阶段必须产出的正交、完备、可验证 artifact。

SDD 的 `proposal/spec/plan/tasks` 只是文件入口；本规格定义 artifact quality。任何阶段如受 SDD 模板限制，必须新增辅助文件并在 `plan.md` 或 `tasks.md` 中引用。

## Contents

- [Global Rules](#global-rules)
- [Representation Catalog](#representation-catalog)
- [Stage 0: Source Intake](#stage-0-source-intake)
- [Stage 1: Product Requirement / PRD](#stage-1-product-requirement--prd)
- [Stage 2: AIP / Engineering Design](#stage-2-aip--engineering-design)
- [Stage 3: Code Archaeology](#stage-3-code-archaeology)
- [Stage 4: New Feature Design](#stage-4-new-feature-design)
- [Stage 5: Migration Diff](#stage-5-migration-diff)
- [Stage 6: Frontend Contract](#stage-6-frontend-contract)
- [Stage 7: Cross-Module Contract](#stage-7-cross-module-contract)
- [Stage 8: Verification Matrix](#stage-8-verification-matrix)
- [Stage 9: Atomic Task Planning](#stage-9-atomic-task-planning)
- [Stage 10: Atomic Execution](#stage-10-atomic-execution)
- [Stage 11: Deployment / Runtime Smoke](#stage-11-deployment--runtime-smoke)
- [Stage 12: Convergence Retrospective](#stage-12-convergence-retrospective)

## Global Rules

### Stage Construction Completeness Means

Contextpack workflow 的阶段完整度从构造前开始，而不是只在 artifact 完成后判断。schema v2 或显式启用 `stage-construction-v1` 的 change，在写当前阶段 canonical artifact 前必须运行 `workflowctl.py prepare-stage <stage>`，生成：

```text
stage-construction/<stage>-obligations.yaml
stage-construction/<stage>-execution-pack.md
```

Review rule:

- obligation 集合必须来自 `templates/stage-construction-contracts.yaml` 的 always rules 和当前需求 signal，不得由 agent 自行删减。
- closure 草稿完成后必须先运行只读 `preflight-stage-closures` 集中修复 construction errors；不得逐条调用 `validate-obligation` 才发现同类格式/引用缺口。
- `mechanism-design-model.md` 对应 canonical model table 的定义行中，`MECH/OPSEQ/EXTAPI/EVT/RMM/RLM/FCM/MIM` 必须是唯一 row identity；同一 ID 定义两次，即使字段都非空，也必须在 AIP preflight 阻断。Local Audit、mapping 或其他表中的引用不算 canonical 定义。
- Current Architecture evidence 只从包含 `Area / Current architecture / Evidence path / Engineering implication / Gap` 完整签名的 canonical table 提取；readiness audit、proof 或 mapping 表的通用 `Evidence` 列不得触发 AIP materialization。
- 下游阶段的 `plan.md` 必须保留最近已通过 plan snapshot 中生成分隔线 `---` 之后的 accepted plan body 作为完整前缀，不得复制 snapshot wrapper/header；`preflight-stage-closures` 和常规 stage `validate` 必须在 review 前阻断 upstream rewrite，不能等 `pass-stage` 才发现。
- 每个 obligation 必须先在 canonical artifact 中闭合，再用 `validate-obligation` 写入 fresh row-level receipt。
- 当前阶段产生新 surface、mode、mutation、runtime、mock 或 frontend action signal 时，必须重跑 `prepare-stage`，不能等最终 gate 临时补字段。
- `validate-stage-construction` 必须在 deterministic stage validator 和 readonly review 之前通过。
- stage receipt 必须封存 obligation ledger 与 execution pack；contract、upstream receipt、trigger profile、closure 或 canonical artifact hash 变化会使其 stale。
- 已知机械缺口只在最终 gate 暴露时，必须登记 `late_detection_defect` 并前移到 machine contract、preflight 或 incremental validator；不得把“最终 validator 能挡住”视为工作流质量合格。
- obligation ledger 只是 canonical artifact 的闭合索引，不得成为新的产品、架构或契约 source of truth。

### Language Policy Means

AutoMQ workflow 持久化文档默认使用中文，包括 `proposal.md`、`spec.md`、`plan.md`、`tasks.md`、`decision-reviews/*.md`、`atomic-issues/Txxx.md` 和验收报告。

例外仅限：

- 代码标识、类名、字段名、API path、命令、错误码、枚举值、日志原文。
- 用户明确要求英文。
- 外部资料原文短摘录，但必须用中文说明其决策含义。

Review rule:

- 如果主要叙述是英文，不合格。
- 如果同一决策在中文 PRD 和英文 Atomic Issue 中发生语义压缩，不合格。
- 模板标题可以中英混用，但正文的产品语义、工程决策和任务上下文必须中文优先。

### Decision Closure Means

每个阶段的 artifact 不仅要描述结论，还要显式记录该阶段产生的决策。

决策必须按层级处理：

| Layer | Who may decide | Closure requirement |
|---|---|---|
| Product | 用户确认，或用户明确授权 AI 采用推荐决策 | PRD 完成后必须 locked；不得留给 AIP/设计/实现 |
| Engineering | AI 可在 locked PRD/AIP 约束下自主决策 | 必须记录 alternatives、reason、product alignment、impact、verification |
| Implementation | 不允许 | 发现缺口时生成 decision gap，回到对应阶段 |

每个产生决策的阶段必须产出独立决策文档：

```text
specs/changes/<change-id>/decision-reviews/<stage>-decisions.md
```

并同步进入 Decision Registry。若有 Feishu/Lark 写权限，必须同步为飞书文档并回写链接。

Review rule:

- 如果一个选择只出现在正文段落里，而没有进入阶段决策文档和 Decision Registry，不合格。
- 阶段决策文档必须逐决策展开；禁止 `PDEC-001..022`、`ADEC-001..004`、`C-001..C-006` 这类 range 合并。
- Decision Summary 中的每个决策 ID 必须有一个独立 `### <ID>` 详情段。
- 每个决策详情必须包含 rejected alternatives、reason、affected modules、verification 和 downstream Atomic Issue impact。
- 每个 active locked 决策必须有稳定 `Decision key`；同一 key 不能有冲突 active locked 结论。
- 修改 locked 决策时必须 supersede 旧决策，并触发 Backflow Invalidation Matrix。
- 如果 `Decided by=ai-engineering` 的决策改变了用户可见行为、scope、默认值、错误、权限或兼容语义，不合格；必须升级回 product decision。
- 如果 PRD 后仍有 product open decision，不得进入 AIP 或工程设计。
- 如果实现阶段需要做新决策，Atomic Issue 不合格。

### Source Intake Closure Means

任何入口输入都必须先进入 `source-intake-ledger.md`，再进入 PRD/AIP/design/contract/task。入口输入包括用户提供的文档、飞书链接、issue、补充设计、Terraform/API 草案、历史方案、代码路径、运行时证据和 workflow 发现的关键 source。

Review rule:

- `Source Inventory` 必须覆盖所有 user-provided 或 workflow-discovered sources。
- behavior-affecting source 不允许处于 `unread` / `blocked` 状态后继续生成设计、契约或 Atomic Issue。
- `Source To Semantic Object Map` 必须说明每个 source 产生或影响哪些 REQ/SCN/DEC/C/MIG/VER/T。
- `Source Conflict Matrix` 中的 open conflict 阻塞 Atomic Task Planning 和实现。

### Decision Consistency Means

Decision Registry 不只是列表，还必须证明全局没有自相矛盾。

Review rule:

- 每个决策有 `Decision key`，表达它回答的稳定问题。
- `Decision Consistency Matrix` 必须列出同 key 决策之间是否冲突。
- 冲突不能通过“后文覆盖前文”解决；必须 supersede、拆 key 或回到对应阶段重决策。
- active Atomic Issue 不得引用 superseded DEC/C/VER。

### Backflow Invalidation Means

任何阶段发现 gap、决策变化、契约变化、验证变化或产品验收问题时，必须重算失效范围。

Review rule:

- 必须记录 Backflow Trigger、Invalidation Matrix、Supersession Record。
- 被失效的 Atomic Issue 必须标为 blocked/pending-rewrite/pending-rerun。
- 被失效的 verification 必须重跑或进入 Not Run risk。
- P0/P1 回流触发未关闭时，不得宣布需求 done。

### Semantic Consumption Means

每个阶段都必须证明没有丢失上游语义。PRD 是源头，不是后续阶段的隐式上下文。后续阶段必须把需要的语义消费、派生、复制、验证或明确丢弃。

最低结构：

| Upstream object | Consuming stage | Required by stage? | How consumed | Derived object | Copied semantics | Dropped semantics | Drop reason / decision | Verification / gate | Status |
|---|---|---:|---|---|---|---|---|---|---|

Review rule:

- 每个 `REQ/SCN/PDEC/DEC/C/MIG/VER` 必须出现在 Semantic Consumption Matrix。
- `Required by stage?=yes` 的对象必须有 derived object、copied semantics、verification/gate 或 blocked。
- `Dropped semantics` 只有在 `Drop reason / decision` 引用 locked decision 或 explicit N/A 时允许存在。
- `Status=blocked` 阻塞下一阶段。
- Atomic Issue 可引用 PRD ID 作审计，但不能依赖 PRD 文本作执行语义。

### Decision Surface Discovery Means

决策前置只有在“决策面已经被发现”时才成立。purpose、高层目标或已有 PRD/AIP 不保证 AI 已经想到所有需要决策的点；必须先把可能需要决策的 surface 枚举出来。

最低结构使用 `templates/decision-surface-discovery.md`：

- Decision Surface Inventory
- Mode Consumer Matrix
- Capability Support Matrix
- Post-Create Consumer Audit
- Frontend Action Surface Graph
- Operation Mutability Matrix
- Surface Obligation Projection Matrix
- Owner Assignment Gate

Review rule:

- 新增/修改 mode、资源类型、生命周期、创建后能力、外部依赖、managed/generated/select-existing external resource、mock acceptance / repo-specific acceptance runtime、持久化 mutation、operation mutability 或用户只给 purpose 时，缺 `decision-surface-discovery.md` 不合格。
- 每个 surface 必须有 owner stage、required decision、locked decision/contract/verification、owner issue 或 locked N/A。
- `needs-decision`、无 owner、无 verification、只写在 source/context/appendix 中，均阻塞 task planning。
- 创建类需求必须有 post-create consumer 行；不能用 create flow smoke 覆盖 logs/metrics/workers/connectors/update/delete 等创建后能力。
- 前端 action surface 必须进入 action-route/component 矩阵；不能只写“详情页按 mode 分支”。
- auto-create/default-created/generated/select-existing external resource 必须有 managed-resource-ownership surface；不能用 selector/default/resolvedConfig 行替代 provider writer、resource identity、owned/existing provenance、cleanup/protect 和 verification。
- create/update/edit/save/resize/delete/recreate/migrate 复用同一对象、同一 config 或同一 readback 字段时，必须有 Operation Mutability Matrix；不能用 create 表单字段、readback VO 或 active branch payload 证明字段可在 update/edit 中修改。每个相关字段必须决策为 editable/read-only/hidden/disabled/unsupported/recreate-required/migrate-required，或保持 blocked。
- Product acceptance 发现某能力运行时报错或旧 mode 页面泄漏时，优先检查是否为 `decision-surface-discovery-miss`，再判断是否是 contract/implementation bug。

### External Capability Research Means

PRD 可以锁定用户要什么，但不能证明外部系统真实允许怎么做。任何依赖外部系统能力的工程方案，都必须在 AIP/design 锁定前完成外部能力调研。

最低结构使用 `templates/external-capability-research.md`：

- Research Source Inventory
- External Capability Fact Matrix
- Capability Support / Non-Support Matrix
- External Mechanism Decision Matrix
- External Constraint Matrix
- Design Implication Matrix
- Mock / Acceptance Runtime External Boundary Map
- Research Consumption Gate

Review rule:

- 涉及云资源、K8s/Helm/Terraform/IAM/network/storage/compute/runtime、第三方 API/SDK、官方协议、autoscaling/scheduling/lifecycle、metrics/logs/events 或 mock acceptance / repo-specific acceptance runtime 外部依赖时，缺 `external-capability-research.md` 不合格。
- 关键 ADEC/C/VER 不能由非官方材料单独支撑；必须有官方文档、SDK/API reference、标准规范、真实 adapter/source 或真实响应样例。
- `unknown-blocking`、`unread`、`blocked`、`open` 的外部 fact 不能进入 AIP/design/contract/task planning。
- 每个影响产品语义的外部机制必须在 External Mechanism Decision Matrix 中写清产品语义、官方机制/API/resource、AutoMQ 字段映射、不等价/不支持语义、失败/权限/指标缺失行为，以及 DEC/C/VER/owner task。只写“外部系统支持 X”不合格。
- 每个影响设计的 Fact/Constraint/Mechanism 必须消费到 ADEC/DEC、C、VER、semantic carrier / packet，或 locked N/A / Not Run risk。
- 只写在 AIP 调研论证、source excerpt、context pack 或 research 文档里，不算被实现阶段消费。
- mock acceptance / repo-specific acceptance runtime fixture 的字段、状态、错误和时序必须能追溯到外部 fact、真实 adapter/source 或 locked contract；不得由 mock 反推真实外部语义。

### Source Normalization Means

已有需求文档、飞书文档、issue、标题、对话输入或 PRD 草稿不是天然合格输入。它们必须先被视为 Propose / Source，再由 workflow normalized into PRD。真正的 PRD 必须由 workflow 重新生成，并通过 PRD Completeness Gate。

Normalization 必须产出 source trace：

| Original source | Original statement | Normalized PRD section | Interpretation | Gap/decision |
|---|---|---|---|---|

Review rule:

- 禁止把外部文档、飞书标题、issue 或聊天输入直接标记为 accepted/final PRD。
- 对话输入也必须有 source trace 或 Propose Extraction。
- 原文中的明确事实必须能 trace 到新 PRD 章节。
- 原文中的模糊词必须转成具体行为或 open decision。
- 原文没有覆盖的标准 PRD 维度不能被省略。
- 原文冲突不能静默选择；必须进入 Product Decision。

### Current Product/Code Understanding Means

PRD 不是脱离当前项目写产品想象。写 PRD 前必须先理解与 propose 相关的当前产品和代码现状，产出 `Current Product/Code Understanding`。

最低结构：

| Area | Current behavior | Evidence path / command | Product implication | Gap / decision |
|---|---|---|---|---|

Review rule:

- 必须覆盖与 propose 相关的页面、API、配置、状态、错误、权限、运行时能力。
- 用户说“参考/类似/复用/沿用/改造/优化”的对象必须有当前实现 evidence。
- Evidence 必须具体到 repo path、类/页面/API/配置文件或命令摘要。
- 当前实现和 propose 冲突时，必须生成 PDEC 或 open question。
- 没有 Current Product/Code Understanding，不得生成 locked PRD。

### Research Evidence Means

当需求依赖外部事实或领域知识时，必须先调研，再锁定决策。

外部事实包括：飞书文档、GitHub issue/PR、官方文档、第三方 API/云服务限制、竞品/行业行为、现有代码、线上或部署环境行为。

Research evidence 必须结构化：

| Evidence ID | Source type | URL/path | Fact extracted | Applies to decision/section | Confidence | Notes |
|---|---|---|---|---|---|---|

Review rule:

- 用户提供的链接必须读取内容，不能只看标题或凭记忆推断。
- 会随时间变化的事实必须用当前来源验证。
- 未验证外部假设不能成为 locked decision，只能成为 assumption/risk/open decision。
- Evidence 必须进入 PRD 或阶段决策文档，不能只留在聊天中。

### Orthogonal Means

一个阶段的输出应按互不替代的维度枚举，不允许用一个泛化段落覆盖多个维度。

例如：

- “权限已处理”不合格；必须分 API denied behavior、UI hidden/disabled behavior、permission constant、test。
- “参考现有创建流程”不合格；必须分 UI 字段、API param、backend derivation、task/cloud request、DB/current data。

### Complete Means

完备不是文档长，而是没有会让实现阶段重新做选择的空洞。

检查方式：

- 是否每个 REQ/SCN/DEC/Contract/Migration 都有 owner artifact。
- 是否每个跨模块边都有 Trigger/Normal/Failure/Consistency/Timing/Verification。
- 是否每个实现任务都能生成 self-contained Atomic Issue。
- 是否无法验证的行为被写入风险，而不是忽略。

### Verifiable Means

每个重要行为必须能回答：

| Question | Required answer |
|---|---|
| What proves it? | unit/integration/api-route/frontend/runtime/manual/docs |
| Exact command/step? | 可执行命令或可重复人工步骤 |
| Expected result? | status/body/DB row/no grep match/rendered UI/plan diff/log metric |
| What does it prove? | 对应 REQ/SCN/DEC/Contract/Migration |

### Representation Means

每个维度必须选择能准确表达其语义结构的媒介。不要默认用自然语言段落，也不要默认用图。

原则：

> Artifact 的表达媒介由信息结构决定，而不是由 SDD 模板或写作者习惯决定。

媒介选择标准：

| Information structure | Recommended representation | Why |
|---|---|---|
| 分类/属性/字段 | Table / matrix | 易于发现缺字段、空值、权限、状态遗漏 |
| 取舍和反选 | Decision matrix | 能同时表达方案、反选、理由、影响 |
| 方向性依赖 | Dependency graph / Mermaid + edge table | 图表达方向，表表达证据和语义 |
| 生命周期 | State machine diagram or transition table | 能表达状态、进入条件、允许动作、终止态 |
| 时序交互 | Sequence diagram or call-flow table | 能表达顺序、调用方、失败点 |
| 数据流 | Data flow diagram/table | 能表达 producer、consumer、path、owner |
| 跨模块约束 | Contract table | 固定回答 trigger/normal/failure/consistency/timing |
| 覆盖关系 | Traceability / coverage matrix | 能证明 REQ/SCN/DEC/Contract/Migration 没漏 |
| 可证明性 | Verification matrix | 能表达 proof、expected result、risk |
| 可执行任务 | Atomic Issue template | 能表达执行上下文闭包 |

Review rule:

- 如果一个维度只用一段自然语言描述，必须判断是否丢失了结构。
- 如果一个图没有配套表格，必须判断是否缺少 evidence、owner、failure、verification。
- 如果一个表格不能暴露遗漏，必须补 coverage / traceability 列。
- 如果某个 artifact 不能被下游阶段直接消费，说明媒介不合适或粒度不够。

## Representation Catalog

| Artifact | Best for | Required columns / elements | Review questions |
|---|---|---|---|
| User Scenario Table | 用户任务和痛点 | user, goal, pain, desired outcome | 是否覆盖所有目标用户和关键使用路径？ |
| Scope / Non-goals Table | 产品边界 | item, in/out, reason, decision | 是否把未决问题伪装成 non-goal？ |
| State Matrix | 用户可见状态 | state, meaning, entered by, allowed action, terminal | 每个状态是否有进入条件和用户动作？ |
| Error Matrix | 错误语义 | scenario, behavior, status/message, recovery | 用户是否知道如何恢复？ |
| Permission Matrix | 权限和可见性 | action/view, permission, API denied, UI denied | API 和 UI 是否一致？ |
| Decision Matrix | 方案取舍 | decision, selected, alternatives, reason, impact | 是否有反选方案和拒绝理由？ |
| Module Boundary Table | 模块职责和边界 | module, responsibility, owned state/data/resources, writer evidence, included files/resources, interfaces, interaction count, boundary evidence | 模块是否按 writer 所有权/状态机/独立性划分？ |
| Dependency Graph + Edge Table | 模块依赖方向 | caller, callee, interface, scenario, evidence | 方向是否正确，证据是否具体？ |
| Module Contract Graph | 模块契约图 | module, responsibility, owned state/data/resources, provided contracts, consumed contracts, boundary evidence | issue 是否能绑定模块并声明 consumed/provided contract？ |
| Module Boundary Validation | 模块划分验证 | module, ownership/writer evidence, state-machine evidence, change-independence evidence, interface count, interaction count, too-large/small risk, decision | 模块划分是否有证据，是否能产出契约闭包 issue？ |
| Module Composition Verification | 模块组合验证 | REQ/SCN, composition path, provider contracts, consumer assumptions, verification, expected result | 模块组合后是否满足用户需求？ |
| Source Intake Ledger | 输入完整性 | source id, type, path/url, read status, read method, semantic map, conflicts | 是否有漏读或未映射的输入？ |
| Code Scope Discovery | 当前项目现状理解范围 | seed, search coverage, evidence path/command, stop condition | PRD/AIP/design 前是否读到足够现状？ |
| User Decision Interaction | 用户产品决策确认 | authority, question, recommendation, alternatives, user response, final status | 产品决策是否真的由用户确认或授权？ |
| Engineering Propose Intake | 工程输入归一化 | engineering propose, current architecture, decision completeness | AIP/草案是否被直接当 final design？ |
| Semantic Consumption Matrix | 跨阶段语义搬运 | upstream object, consuming stage, derived object, copied/dropped semantics, gate, status | 上游语义是否被消费、派生、复制或明确丢弃？ |
| Verification Feasibility Gate | 验证可执行性 | verification, environment/fixture, available, setup owner, fallback, blocks done | 验证是否能在实现前被真实执行？ |
| Version Branch Alignment Matrix | 多仓版本分支一致性 | component, repo, branch/version, evidence, aligned, risk/action | 多仓/版本/模板是否一致？ |
| Artifact Rubric Scorecard | 语义质量评分 | artifact, rubric, dimension, score, evidence, fix required | 结构校验外是否做了 0/1/2 质量门禁？ |
| Decision Consistency Matrix | 决策一致性 | decision key, active decision, possible conflict, supersession, status | 是否存在冲突 active locked 决策？ |
| Contract Discovery Coverage Matrix | 契约发现覆盖 | source area, evidence reviewed, contract candidates, locked contracts, residual risk | 是否系统性覆盖所有可能产生 N2 的来源？ |
| Task DAG | 任务依赖排序 | nodes, edges, topological order, parallel groups | 顺序是否由契约、文件 ownership 和验证 gate 决定？ |
| Backflow Invalidation Matrix | 回流失效 | trigger, invalidated artifacts/DEC/C/T/VER, rerun, status | 变化是否使受影响产物失效并重写/重跑？ |
| Not Run Risk Table | 未验证风险 | check, source, severity, reason, risk, owner/approval, blocks done | 未跑验证是否阻塞完成？ |
| Data Ownership Table | 数据归属 | data/resource, owner module candidate, writer, reader, mutation rule, evidence | 是否存在多 owner 或隐式写入方？ |
| Managed Resource Ownership Matrix | 外部资源自动创建/选择已有/托管归属 | resource, selection mode, create timing, provider writer, identity, provenance owner, runtime consumer, update, cleanup/protect, idempotency/failure, verification | 是否把 selector 误当成资源 lifecycle？是否能证明 owned 资源清理、existing 资源保护？ |
| External Side Effect Contract Matrix | 外部副作用和 no-cloud/playground 替代边界 | effect, external system, production owner/call, substitute boundary, minimum proof, failure semantics, readback consumer, contract, verification, owner issue | 是否把 mock/no-cloud 误解为可跳过生产 provider/runtime side effect？ |
| Runtime Test Topology Matrix | runtime proof/build/test 拓扑 | production path, proof module/file, fixture files, freshness step, staleness risk, command, expected, owner issue | 是否提前锁定 proof owner 文件和跨模块构建新鲜度？ |
| Existing Object-Action-Consumer Graph | 旧对象/action/readback/post-create consumer 继承 | object/entity, action/mutation, entry point, existing variant, producer chain, state owner/storage, readback API/VO, consumer surface, hidden old-variant assumption, evidence | 新实现形态是否复用同一个对象/action/入口/readback/consumer？旧 consumer assumption 是否被看见？ |
| Variant Impact Matrix | 新实现形态/变体对旧 consumer 的影响 | new variant candidate, object/action, shared entry/readback, old consumer surface, must satisfy, new producer/behavior, contract candidate, verification | 新形态是否必须满足旧 consumer？不支持是否有 locked decision？ |
| Progress / Change Producer Chain Matrix | progress/change/last-change 生产写入链 | mutation entrypoint, canonical writer, state owner/table, task/event producer, correlation key, last-change readback, change detail readback, frontend/mock consumer, terminal/failure, verification, owner issue | 是否证明生产 writer -> state owner -> readback -> consumer 的同一对象 id 闭环？ |
| State Machine / Transition Table | 生命周期 | entity/resource, from, event, guard/precondition, to, side effect, external dependency, contract candidate | 状态转换是否闭合？ |
| Change Independence Table | 变更独立性 | file group, evidence source, co-change count or future-change reason, shared data/state, shared state machine, module candidate, risk | 是否有 git 共改或未来独立变更证据？ |
| Data Flow Table | 数据路径 | data, producer, consumer, path, storage, evidence | 数据是否有 source of truth？ |
| Hidden Constraints Table | 旧系统隐式知识 | constraint, source, consequence, location, handling | 违反后果是否清楚？ |
| Framework Semantics Table | 框架/API 易错语义 | method/config, semantics, misuse, reference | 是否能防止 AI 误用？ |
| Pattern Reference Table | “照着谁做” | scenario, reference path, pattern, must follow | 是否具体到文件/组件/方法？ |
| Semantic Diff Matrix | 旧新差异 | dimension, old, new, diff, decision, verification | 每个差异是否有处理决策？ |
| Contract Table | N2 语义约束 | trigger, normal, failure, consistency, timing, verification | 正常/失败路径是否都明确？ |
| API Contract Table | API 边界 | method, exact path, query/body, handler, auth, errors | 是否覆盖最终外部 URL 和鉴权 smoke？ |
| Frontend Field Table | UI 字段展示 | field, source, i18n, format, empty, permission | 字段 source of truth 是否唯一？ |
| Verification Matrix | 可证明性 | source, behavior, type, step, expected, proves, risk | 是否能证明每个 source？ |
| Atomic Issue | 执行上下文闭包 | goal, scope, context, decisions, contracts, refs, steps, verification, prohibited, done | worker 是否能独立执行？ |
| Stage Decision Document | 阶段决策闭包 | source inputs, decision summary, final decision, decided by, alternatives, reason, product alignment, impact, verification, Lark URL | 决策是否从正文中抽离，且下游可消费？ |
| Source Trace Table | 原始需求到标准 PRD 的映射 | original source, original statement, normalized section, interpretation, gap/decision | 新 PRD 是否忠实覆盖原始输入？ |
| Research Evidence Table | 外部事实依据 | evidence id, source type, URL/path, fact, applies to, confidence, notes | 决策依据是否可追溯和可验证？ |

## Stage 0: Source Intake

### Goal

确保所有输入被读取、登记、映射和冲突处理，防止 workflow 从不完整上下文生成看似完备的 Atomic Issues。

### Orthogonal Dimensions

- Source inventory.
- Read status.
- Read method.
- Semantic object mapping.
- Source conflict.
- Downstream invalidation.

### Required Artifacts

| Artifact | Required content |
|---|---|
| `source-intake-ledger.md` | Source Inventory, Source To Semantic Object Map, Source Conflict Matrix |

### Dimension Representation Map

| Dimension | Representation | Why this medium |
|---|---|---|
| Source inventory | Source Inventory table | 输入必须逐条列出，避免漏读用户提供材料 |
| Read status | status column | `read/unread/blocked/irrelevant/superseded` 必须可审查 |
| Read method | method column | 证明 source 是通过文件、lark-cli、browser、rg、command 等方式读取 |
| Semantic mapping | Source To Semantic Object Map | source 必须落到 REQ/SCN/DEC/C/MIG/VER/T，不能只留在聊天里 |
| Conflict | Source Conflict Matrix | 冲突必须进入决策，不能静默选择 |
| Downstream invalidation | Backflow link | source 后读或重读改变语义时必须触发回流 |

### Completeness Criteria

- Every user-provided URL/path/document/issue/code reference appears in Source Inventory.
- Every behavior-affecting source is `read`, `irrelevant` with reason, or `superseded` with record.
- No `unread` / `blocked` source is used as source of truth.
- Every source maps to semantic objects or has explicit ignored reason.
- Every source conflict has locked DEC before Atomic Task Planning.

### Exit Gate

Design, contract, verification, task planning and execution cannot proceed from unregistered or unread behavior-affecting input.

## Stage 1: Product Requirement / PRD

### Goal

锁定产品语义，消灭产品层临场决策。

### Orthogonal Dimensions

- Propose extraction.
- Current product/code understanding.
- 用户与场景。
- 产品对象模型。
- Scope / Non-goals。
- 用户可见配置。
- 配置和云资源参数归属。
- 用户可见状态。
- 用户可见错误和降级。
- 权限和可见性。
- 兼容语义。
- 验收场景。
- 产品决策。
- PRD completeness gate.
- Source trace。
- Research evidence。

### Required Artifacts

| Artifact | Required content |
|---|---|
| Propose Extraction Table | Source ID, propose statement, explicit fact, inferred fact, unknown/decision needed, target PRD dimension |
| Code Scope Discovery | discovery seeds, search coverage, evidence path/command, stop condition |
| Current Product/Code Understanding | Area, current behavior, evidence path/command, product implication, gap/decision |
| User Decision Interaction | authority, pending PDEC, recommendation, alternatives, user response, final status |
| User Scenario Table | User, goal, current pain, desired outcome |
| Product Object Model | Object, user-facing meaning, key properties, lifecycle/state |
| Scope / Non-goals | Explicit in/out; no hidden decisions in non-goals |
| Config Ownership Matrix | Config/resource, ownership, default/derivation source, missing behavior, error shown |
| State Matrix | State, meaning, entered by, allowed action, terminal |
| Error Matrix | Scenario, product behavior, status/error shown, recovery |
| Permission Matrix | Action/view, required permission, API denied behavior, UI denied behavior |
| Scenario Acceptance | Given/When/Then/Acceptance |
| Product Decision Registry Seed | PDEC, alternatives, reason, status |
| PRD Completeness Gate | dimension, complete, evidence section, open decision, blocks next stage |
| Source Trace Table | Original source, original statement, normalized PRD section, interpretation, gap/decision |
| Research Evidence Table | Evidence ID, source type, URL/path, fact extracted, applies to decision/section, confidence |
| PRD Decision Document | Original input, clarification process, PDEC details, user-confirmed or AI-authorized final decisions, rejected alternatives, downstream constraints, Lark URL if available |
| Source Intake Ledger | Source Inventory, Source To Semantic Object Map, Source Conflict Matrix |
| Semantic Consumption Matrix Seed | REQ/SCN/PDEC inventory, core semantics, required downstream |

### Dimension Representation Map

| Dimension | Representation | Why this medium |
|---|---|---|
| Propose extraction | Propose Extraction Table | 区分原始意图、明确事实、推断事实和未知决策，避免把输入当 PRD |
| 当前产品/代码理解 | Current Product/Code Understanding table | PRD 必须受当前项目现状约束，不能凭空定义产品行为 |
| 用户与场景 | User Scenario Table | 表格能并列用户、任务、痛点和目标结果，暴露遗漏用户群 |
| 产品对象模型 | Product Object Model table | 对象、属性、生命周期必须结构化，否则容易和代码对象混淆 |
| Scope / Non-goals | In/Out decision table | 防止把待决策项写成 non-goal |
| 用户配置 | Config table | 配置需要类型、默认值、校验、可见位置等多列同时表达 |
| 云资源参数归属 | Config Ownership Matrix | ownership/source/missing/error 必须逐字段闭合 |
| 用户状态 | State Matrix or state diagram | 状态必须表达进入条件、可操作性和终止态 |
| 错误和降级 | Error Matrix | 错误必须绑定场景、用户可见信息和恢复动作 |
| 权限和可见性 | Permission Matrix | API denied 和 UI hidden/disabled 必须并排对齐 |
| 验收场景 | Given/When/Then blocks | 验收必须可执行、可复现 |
| 产品决策 | Product Decision Registry | 决策必须有 alternatives/reason/status，防止丢失 |
| PRD completeness | PRD Completeness Gate | 明确哪些维度完整、哪些 open decision 阻塞后续阶段 |
| Source trace | Source Trace Table | 保证已有需求文档被完整、忠实、可审查地重写 |
| External research | Research Evidence Table | 保证外部事实可追溯，防止未验证假设进入决策 |

### Completeness Criteria

- Every user-visible behavior has REQ/SCN or explicit non-goal.
- Every input source has Propose Extraction; no external document or conversation is accepted as final PRD.
- Current Product/Code Understanding exists before PRD locking and includes evidence path/command.
- Code Scope Discovery has stop condition evidence for every required area.
- User Decision Interaction exists unless AI product-decision authority is explicitly granted.
- Every configurable field has ownership and missing behavior.
- Every state/error/permission has user-visible semantics.
- No product decision remains implicit for AIP or implementation.
- Every product decision is user-confirmed or explicitly AI-authorized.
- Every user-provided source appears in Source Intake Ledger before PRD normalization.
- Existing requirement docs are normalized with source trace before being treated as PRD.
- PRD Completeness Gate has no `Complete?=no` row with `Blocks next stage=yes`.
- No PDEC remains open unless PRD is explicitly blocked and does not enter AIP/design.
- Semantic Consumption Matrix seed lists every REQ/SCN/PDEC that downstream stages must consume.
- External facts used by decisions have research evidence with source and confidence.
- Unverified external assumptions are not locked as product decisions.
- `decision-reviews/prd-decisions.md` exists and is linked from Decision Registry.

### Exit Gate

Implementation cannot ask: “用户看到什么、允许什么、失败怎么表达、默认值是什么、是否支持这个行为？”

AIP/design cannot ask product questions either; if they need to, PRD is incomplete.

If the so-called PRD was not generated by this workflow, or lacks Propose Extraction, Current Product/Code Understanding, or PRD Completeness Gate, it cannot enter AIP/design/contract/task planning.

## Stage 2: AIP / Engineering Design

### Goal

锁定工程方案，防止实现阶段做架构选择。

### Orthogonal Dimensions

- Problem and timing.
- Goals / Non-goals.
- Selected architecture.
- Rejected alternatives.
- Interface changes.
- Data/state/task/event changes.
- Deployment/cloud/IAM changes.
- Observability.
- Compatibility and rollback.
- Verification strategy.

### Required Artifacts

| Artifact | Required content |
|---|---|
| Engineering Propose Intake | engineering propose extraction, current architecture understanding, engineering decision completeness gate |
| Architecture Decision Matrix | Decision, selected option, rejected alternatives, reason, impact |
| Interface Change Table | API/DB/event/task/Terraform/frontend interface, compatibility |
| Data/State Model | DB/state machine/event/task lifecycle changes |
| Deployment/IAM Plan | K8s/Helm/cloud/IAM/resources |
| Observability Plan | metrics/logs/events/alerts/dashboard/runbook |
| Compatibility Matrix | new install, existing data, upgrade, rollback, old API/field |
| Verification Strategy | behavior, verification type, expected proof |
| AIP Decision Document | Architecture/interface/compatibility/observability/verification decisions, alternatives, reason, product alignment, impact, verification, Lark URL if available |
| Mechanism-Level Design Closure Matrix | design question, selected mechanism, rejected alternatives, current code evidence, external fact/constraint, interface impact, state/runtime impact, failure behavior, verification, downstream C/VER |
| Mechanism Design Model | `MECH-*` operation/surface rows plus `OPSEQ-*`, `EXTAPI-*`, `EVT-*`, `RMM-*`, `RLM-*`, `FCM-*`, `MIM-*` rows covering production sequence, external API parameters, event state, runtime materialization, resource lifecycle, failure consistency, and module interface semantics |
| AIP Narrative Materialization Gate | source design object, AIP section, narrative requirement, materialized/locked N/A/blocked status |
| AIP Narrative Document | AutoMQ standard AIP headings with human-readable design narrative that consumes ADEC/DEC, MECH/FACT/CONSTRAINT, current architecture, interface, state/runtime, compatibility, alternatives, and verification |

### Dimension Representation Map

| Dimension | Representation | Why this medium |
|---|---|---|
| 问题和时机 | Problem statement + constraints table | 明确为什么现在做，以及哪些约束驱动方案 |
| Goals / Non-goals | Goals table | 防止工程目标和产品目标混淆 |
| 架构方案 | Architecture Decision Matrix | 方案取舍必须同时展示 selected/rejected/reason/impact |
| 反选方案 | Alternative matrix | 没有反选就不是决策 |
| 接口变化 | Interface Change Table | API/DB/event/task/Terraform/frontend 必须逐接口表达 |
| 数据/状态/任务/事件 | State/data/task model tables or diagrams | 生命周期和状态转移需要结构化表达 |
| 部署/云/IAM | Deployment/IAM Plan table | 资源、权限、owner、环境差异必须逐项列出 |
| 观测 | Observability Plan table | metrics/logs/events/alerts/dashboard/runbook 不能混写 |
| 兼容/回滚 | Compatibility Matrix | 新装/存量/升级/回滚/旧字段必须分维度 |
| 验证策略 | Verification Strategy table | 设计阶段必须能输入 verification matrix |
| 机制级设计闭合 | Mechanism-Level Design Closure Matrix | 把概念级 ADEC 降到 operation/surface、owner、字段/状态/runtime、失败和验证 |
| 机制设计模型 | `mechanism-design-model.md` | 把“怎么实现”拆成 sequence、external parameters、events、runtime、resources、failure consistency 和 module interface，防止 Atomic Issue 变成小需求 |
| AIP 正文物化 | AIP Narrative Materialization Gate + AIP standard sections | 防止决策只在 sidecar 中存在，人读 AIP 仍然单薄 |

### Completeness Criteria

- Every architecture option with meaningful tradeoff has a recorded decision.
- AIP/interface/Terraform/API drafts are normalized as Engineering Propose and not accepted directly as final design.
- Current Architecture Understanding includes evidence paths/commands.
- Engineering Decision Completeness Gate has no blocking incomplete rows.
- Mechanism-Level Design Closure Matrix exists and every key design question is expressed as one operation/surface-level row with selected mechanism, rejected alternatives, evidence, interface impact, state/runtime impact, failure behavior, verification, and downstream C/VER.
- `mechanism-design-model.md` exists when the feature touches external systems, cloud/K8s/ASG/HPA/metrics/IAM/runtime/logs/storage/resources/events/progress/cross-mode behavior; every implementation-affecting `MECH-*` row has concrete `OPSEQ-*`, `EXTAPI-*`, `EVT-*`, `RMM-*`, `RLM-*`, `FCM-*`, and `MIM-*` coverage or locked N/A.
- Mechanism design rows explain actual production mechanisms, parameter meanings, event names/fields, resource lifecycle, runtime carriers, failure ordering, idempotency/retry, and verification; one-line support statements are not acceptable.
- External mechanism facts and constraints that affect design are consumed into mechanism-level design rows; sidecar-only research does not satisfy AIP/design completeness.
- AIP Narrative Materialization Gate exists and proves every locked ADEC/DEC plus design-affecting MECH/FACT/CONSTRAINT/current architecture/interface/state/runtime/compatibility/verification object is materialized in a standard AIP section, locked N/A, or blocked.
- `aip.md` keeps the AutoMQ standard headings and contains a readable design narrative; engineering matrices may be inserted as subsections but cannot replace the AIP document.
- Every new/changed interface has compatibility semantics.
- Every deployment or cloud resource field has ownership/source.
- Verification strategy is specific enough to feed Verification Matrix.
- Every AIP-stage engineering decision is recorded in `decision-reviews/aip-decisions.md`.
- No engineering decision changes product semantics without returning to PRD.

### Exit Gate

Implementation cannot choose: architecture, interface shape, persistence strategy, task/event semantics, compatibility, observability, verification approach, provider API/resource mechanism, external parameter mapping, runtime materialization carrier, progress/change/event fields, resource cleanup/protect behavior, or failure consistency policy.

Contract/task-planning also cannot ask: which external mechanism/API/resource is used, which owner writes state/runtime/resource, where metrics/logs/events come from, how unsupported/permission/metric-missing cases fail, how create/update/delete/autoscaling/progress events are named and shaped, or where the AIP decision is explained to a human reviewer.

## Stage 3: Code Archaeology

### Goal

把旧系统事实、隐式约束和框架语义显式化，防止 archaeology-miss。

### Orthogonal Dimensions

- Module boundary.
- Data ownership.
- State machine.
- Dependency graph.
- Data flow.
- Tests and fixtures.
- Git history and bugfixes.
- Comments/docs/workarounds.
- Defensive checks.
- Framework semantics.
- Existing patterns.
- Reference implementation field matrix.
- Persistent mutation / schema compatibility.
- Existing object-action-consumer inheritance.
- Variant impact / old consumer parity.
- Progress/change producer chain candidate discovery.
- Runtime proof/build topology discovery.
- Semantic consumption.

### Required Artifacts

| Artifact | Required content |
|---|---|
| Data Ownership Evidence | data/resource, writer(s), reader(s), mutation rule, owning module candidate, evidence |
| State-Machine Boundary Evidence | entity/resource, transition, guard/precondition, external dependency, internal module candidate, contract candidate, evidence |
| Change Independence Evidence | file group, evidence source, co-change count/future-change reason, shared data/state, shared state machine, module candidate, risk |
| Module Boundary Map | module, type, responsibility, owned state/data/resources, writer evidence, files/resources, interfaces, external interaction count, evidence |
| Module Boundary Validation | ownership/writer evidence, state-machine evidence, change-independence evidence, interface count, interaction count, external deps enumerable, provided contracts enumerable, too-large risk, too-small risk, decision |
| N1/N2 Impact Table | Item, classification, reason |
| Dependency Graph | Caller, callee, interface/resource, scenario, evidence |
| Data Flow Table | Data/state, producer, consumer, path, evidence |
| Hidden Constraints Table | Constraint, source, consequence, code/location, decision needed |
| Framework Semantics Table | API/config, semantics, common misuse, reference |
| Pattern Reference Table | Scenario, pattern, reference, must follow |
| Reference Implementation Field Matrix | Field/resource, reference behavior, user selectable, backend auto-create, derived/fixed source, hidden, new decision, evidence |
| Persistent Mutation / Schema Compatibility Audit | mutation, mode/variant, authoritative state owner, writer path, schema/mapper/API/VO path, existing required field/resource, old assumption, new null/default/derived/forbidden rule, readback consumers, contract candidate, verification |
| `existing-object-action-consumer-graph.md` | Existing Object-Action-Consumer Graph, Existing Consumer Assumption Matrix, Local Audit |
| `variant-impact-matrix.md` | Variant Detection Matrix, Old Consumer Parity Matrix, Variant Gap Backflow Matrix |
| `progress-change-producer-chain-matrix.md` | Required when old/new consumer surfaces include progress/change/last-change/change detail/task step/event step; archaeology may seed candidate producer rows and contract stage must lock them |
| `runtime-materialization-parity.md` | Runtime Mode Change Classification, Product Capability Parity Matrix, Runtime Materialization Mapping, Runtime Parity Negative Assertions |
| `runtime-test-topology-matrix.md` | Runtime Test Topology Matrix, Proof Owner File Matrix, Freshness Local Audit |
| Semantic Consumption Matrix | upstream REQ/SCN/PDEC/DEC/DESIGN-DEC, how consumed by archaeology, derived old-system fact/constraint/pattern/contract candidate, copied/dropped semantics, gate/status |
| Archaeology Decision Document | Pattern/hidden-constraint/framework/reference decisions, alternatives, reason, product alignment, impact, verification, Lark URL if available |

### Dimension Representation Map

| Dimension | Representation | Why this medium |
|---|---|---|
| Module boundary | Boundary table + dependency graph | 表格表达 owner/writer/interfaces/interaction count/evidence，图表达依赖方向 |
| Data ownership | Data Ownership Evidence | 多 owner、隐式 writer、source of truth 只能逐数据项检查 |
| State machine | State diagram or transition table | 生命周期是否闭合必须看状态转移 |
| Change independence | Change Independence Evidence | 旧代码用 git 共改，新设计用未来独立变更假设 |
| Dependency graph | Mermaid graph + edge evidence table | 图看方向，表看 scenario/evidence |
| Data flow | Data Flow Table | producer/consumer/path/storage 必须结构化 |
| Tests and fixtures | Test Evidence Table | 测试揭示的边界需要 source 和 implication |
| Git history / bugfixes | Git Evidence Table | 历史 bug 要记录 commit、原因、保留/修改影响 |
| Comments/docs/workarounds | Documentation Evidence Table | 注释和 workaround 需要来源和违反后果 |
| Defensive checks | Defensive Check Table | Preconditions/assert/异常分支要转成约束 |
| Framework semantics | Framework Semantics Table | 方法语义和常见误用必须一一对应 |
| Existing patterns | Pattern Reference Table | “照着谁做”必须指向文件/方法/页面 |
| Reference implementation | Reference Implementation Field Matrix | 参考实现必须沿 UI/API/backend/task/cloud/DB 全链路逐字段 |
| Persistent mutation / schema compatibility | Persistent Mutation / Schema Compatibility Audit | 新 mode 或 mutation 会让旧 required 字段/资源失效，必须追 writer、schema/resource constraint 和 readback |
| Existing object-action-consumer inheritance | Existing Object-Action-Consumer Graph | 变体不是关键词问题；必须从代码证明是否复用同一 object/action/entry/readback/post-create consumer |
| Variant impact / old consumer parity | Variant Impact Matrix | 旧 consumer assumption 默认需要新形态满足，除非 locked N/A；必须逐 consumer surface 做支持/不支持决策 |
| Progress/change producer discovery | Progress / Change Producer Chain Matrix candidate rows | progress/change/last-change 是生产写入链，不是 UI fixture；考古阶段必须发现旧 writer、state owner、readback 和 consumer |
| Runtime materialization parity | Runtime Materialization Parity | 新 runtime mode、substrate 或 bootstrap/plugin/config/secret 注入路径必须证明产品能力物化等价，不能用资源存在替代 |
| Runtime proof/build topology | Runtime Test Topology Matrix | 跨模块测试、本地 SNAPSHOT、packaged playground 或 runtime proof owner 必须先建模，否则 allowlist 会在执行期回流 |
| Semantic consumption | Semantic Consumption Matrix | 防止 PRD/AIP 语义绕过考古，或考古事实未传给契约/迁移 |

### Completeness Criteria

- Boundary is based on writer ownership, state-machine self-containment, and change independence.
- Data Ownership Evidence lists writer(s), reader(s), mutation rule, and evidence for every core data/resource.
- State-Machine Boundary Evidence checks every important transition guard/precondition and marks external dependencies as contract candidates.
- Change Independence Evidence uses recent relevant git history, preferably about 50 commits, or records why an alternative evidence source is used.
- Module Boundary Validation proves each core module is neither obviously too large nor too small using interface count, interaction count, class/resource count, state-machine count, and contract-closed issue fit.
- Hidden constraints come from tests, git history, comments/docs, and defensive checks.
- Existing pattern answers “照着谁做” with specific files.
- If requirement says “参考/类似/复用 existing X”, field matrix covers UI -> API -> backend -> task/cloud -> DB/current data.
- If requirement adds a mode/resource type/lifecycle or changes a persistent mutation, Persistent Mutation / Schema Compatibility Audit covers old required fields/resources, writer path, authoritative state owner, null/default/derived/forbidden rule, and readback consumers.
- If the new requirement adds or changes an implementation shape while reusing an old object/action/entrypoint/readback/post-create consumer, `existing-object-action-consumer-graph.md` exists and is derived from code paths, not from requirement keywords.
- If any Existing Object-Action-Consumer row has a new implementation shape, `variant-impact-matrix.md` exists and every old consumer surface has `Must new variant satisfy?` plus new producer/behavior, contract candidate, verification, or locked N/A.
- If any old consumer surface reads progress/change/last-change/change detail/task step/event step/terminal polling, `progress-change-producer-chain-matrix.md` exists or archaeology explicitly records a locked N/A reason; fixture/frontend-only rows do not satisfy this criterion.
- If any runtime/deployment mode, runtime substrate, bootstrap, plugin/config/secret injection path, or execution environment changes, `runtime-materialization-parity.md` exists and classifies the change before design/task planning.
- If runtime proof crosses modules, depends on local SNAPSHOT/package/image/browser freshness, or needs a proof file outside the primary implementation module, `runtime-test-topology-matrix.md` exists and names proof file, freshness step, staleness risk, verification command, and owner issue.
- Any archaeology-stage decision is recorded in `decision-reviews/archaeology-decisions.md`.
- Any archaeology finding that changes product semantics is escalated to PRD instead of silently decided.
- Semantic Consumption Matrix covers every upstream object relevant to old-system behavior, with no blocked or unjustified dropped rows.

### Exit Gate

Implementation cannot be surprised by old behavior, hidden compatibility, framework semantics, or reference implementation fields.

## Stage 4: New Feature Design

### Goal

从需求推导理想模块语义，不被旧实现牵引。

### Orthogonal Dimensions

- Sub-requirements.
- Domain process.
- Invariants.
- Domain entities.
- Module boundary.
- Alternatives.
- Scenario walkthroughs.
- Module 21-question semantics.
- Convergence budget.
- Semantic consumption.

### Required Artifacts

| Artifact | Required content |
|---|---|
| Sub-Requirement Table | ID, requirement, acceptance, source |
| Domain Process Table | process, start/end, participants, observable result |
| Invariant Table | invariant, applies to, violation behavior, source |
| Domain Entity Table | entity, lifecycle/state, owned data/resource, writer, reader |
| Data Ownership Design | data/resource, writer module candidate, reader modules, mutation rule, source/reason |
| State-Machine Boundary Design | entity/resource, transition, guard/precondition, external dependency, internal module candidate, contract candidate |
| Future Change Independence Design | behavior/file group candidate, future independent change, shared data/state, shared state machine, module candidate, risk |
| Module Boundary Design | module, responsibility, owned data/resources, writer evidence, included files/resources, interfaces, external interaction count, boundary basis, external deps |
| Module Boundary Validation | module, ownership/writer evidence, state-machine evidence, contract enumerability, interface count, interaction count, too-large/small risk, decision |
| Mechanism Design Model Consumption | upstream `MECH/OPSEQ/EXTAPI/EVT/RMM/RLM/FCM/MIM` rows consumed into processes, invariants, module boundaries, contract candidates, locked N/A, or blocked backflow |
| Alternative Decision Matrix | option, pros/cons, decision, reason |
| Scenario Walkthrough | Given/When/Then, module interaction |
| Module 21Q Semantics | identity/input/output/behavior/constraints/dependencies/edge cases |
| Convergence Budget | N1 tasks, N2 candidates, locked decisions, open decisions |
| Semantic Consumption Matrix | upstream REQ/SCN/PDEC/ADEC/DEC, derived sub-requirement/process/invariant/entity/module/design decision, copied/dropped semantics, status |
| Design Decision Document | Module boundary/entity/invariant/process decisions, alternatives, reason, product alignment, impact, verification, Lark URL if available |

### Dimension Representation Map

| Dimension | Representation | Why this medium |
|---|---|---|
| Sub-requirements | Sub-Requirement Table | 每个子需求必须能 trace 到 REQ/SCN |
| Domain process | Process table or sequence diagram | 过程要表达 start/end/participants/result |
| Invariants | Invariant Table | 不变量需要 applies-to、violation behavior、source |
| Domain entities | Domain Entity Table | 实体、状态、数据所有权、writer/reader 需要并列 |
| Data ownership | Data Ownership Design | 新功能也必须先判断 writer module，而不是凭 UI/目录切分 |
| State machine | State-Machine Boundary Design | 外部前置条件必须变成 contract candidate |
| Change independence | Future Change Independence Design | 新功能没有 git history 时，用未来独立变更假设替代 |
| Module boundary | Module Boundary Design table + graph | 职责/所有权/writer/接口/交互点/依赖方向需要组合表达 |
| Mechanism consumption | Mechanism Design Model Consumption | 设计阶段必须证明 AIP/readiness 机制对象进入模块、过程、不变量和契约候选 |
| Alternatives | Alternative Decision Matrix | 设计取舍必须记录反选 |
| Scenarios | Scenario walkthrough + sequence | 场景要看 Given/When/Then 和模块交互 |
| Module semantics | 21Q table per module | 模块语义必须按固定问题闭包 |
| Convergence budget | N1/N2 budget table | 明确哪些收敛应被消除，哪些进入 contract |
| Semantic consumption | Semantic Consumption Matrix | 证明 PRD/AIP 语义被设计阶段完整消费并派生为设计对象 |

### Completeness Criteria

- Every sub-requirement maps to REQ/SCN.
- Every invariant has a verification or contract candidate.
- Every cross-module interaction is marked as contract candidate.
- Module Boundary Validation exists and every core module is keep/split/merge with reason; no `needs-contract-review` remains.
- Every module boundary decision uses writer ownership, state-machine evidence, and change-independence/future-change evidence.
- Every `MECH/OPSEQ/EXTAPI/EVT/RMM/RLM/FCM/MIM` row that affects implementation is consumed into a process, invariant, module boundary, contract candidate, verification input, locked N/A, or blocked backflow.
- Design-stage module semantics include enough production mechanism detail that task planning does not need to choose provider API, external parameter mapping, runtime carrier, event/state fields, resource cleanup/protect, or failure consistency.
- Too-large/too-small checks cover class/resource count, interface count, interaction count, independent state machines, and single-caller interface risk.
- Every core module has enough semantics to write unit tests.
- Every design-stage decision is recorded in `decision-reviews/design-decisions.md`.
- Design decisions do not change PRD product semantics.
- Semantic Consumption Matrix covers every upstream REQ/SCN/PDEC/ADEC/DEC, with no blocked or unjustified dropped rows.

### Exit Gate

Implementation cannot invent module responsibility, lifecycle, failure behavior, idempotency, boundary conditions, provider/resource call chains, event definitions, runtime materialization carriers, resource lifecycle rules, or failure consistency policy.

## Stage 5: Migration Diff

### Goal

对齐旧/新语义，防止“第一次没做干净”。

### Orthogonal Dimensions

- Old/new module mapping.
- 21Q semantic diff.
- Hidden constraint handling.
- Persistent mutation migration.
- Delete/keep/modify/add/rename.
- Compatibility.
- Execution order.
- Risk and rollback.

### Required Artifacts

| Artifact | Required content |
|---|---|
| Old/New Module Mapping | old, new, relationship, decision |
| Semantic Diff Table | dimension, old, new, difference, decision, verification |
| Hidden Constraint Handling | constraint, still needed, preserve/modify/retire/replace, reason, verification |
| Persistent Mutation Migration Matrix | mutation, mode/variant, state owner, writer, old required field/resource, new rule, migration action, compatibility/readback impact, verification, decision ID |
| Migration Action Table | delete/keep/modify/add/rename/compatibility items |
| Execution Order Table | step, prerequisites, blocked follow-ups, verification |
| Risk/Rollback Table | risk, mitigation, rollback impact |
| Migration Decision Document | Delete/keep/modify/add/rename/compatibility decisions, alternatives, reason, product alignment, impact, verification, Lark URL if available |

### Dimension Representation Map

| Dimension | Representation | Why this medium |
|---|---|---|
| Old/new module mapping | Mapping table | 每个旧模块必须映射到新语义或删除 |
| 21Q semantic diff | Semantic Diff Matrix | old/new/diff/decision/verification 必须逐维度对齐 |
| Hidden constraint handling | Constraint Handling Table | 每条旧约束必须有 preserve/modify/retire/replace |
| Persistent mutation migration | Persistent Mutation Migration Matrix | 旧 required 字段/资源在新 mode 下如何 nullable/derived/defaulted/forbidden/retired 必须成为迁移决策 |
| Delete/keep/modify/add/rename | Migration Action Table | 行动类型必须分开，避免“后面清理” |
| Compatibility | Compatibility Matrix | 旧输入/旧数据/旧 API 必须逐项说明 |
| Execution order | Execution Order Table | 依赖和阻塞关系需要结构化 |
| Risk/rollback | Risk/Rollback Table | 风险必须绑定缓解和回滚影响 |

### Completeness Criteria

- Every old module maps to keep/rename/split/merge/replace/remove.
- Every hidden constraint has a handling decision.
- Every persistent mutation affected by old required fields/resources has a migration decision, readback impact, and verification.
- Every delete/rename/modify has safety condition and verification.
- No `needs-human-decision` remains.
- Every migration-stage decision is recorded in `decision-reviews/migration-decisions.md`.
- Any migration decision that affects user-visible compatibility is aligned to PRD/AIP or escalated.

### Exit Gate

Implementation cannot later “discover” old fields, names, sync/async behavior, compatibility, or cleanup tasks that should have been planned.

## Stage 6: Frontend Contract

### Goal

消灭 UI 微决策和前后端自然语言歧义。

### Orthogonal Dimensions

- Page/route.
- Reference page/component.
- Field display.
- Interaction/action.
- Action route/source/landing component closure.
- Mode-specific field display and old-mode leakage prevention.
- Form active/inactive/submit participation.
- Loading/empty/error/disabled states.
- Permissions.
- i18n.
- API call exact shape.
- Browser/render verification.

### Required Artifacts

| Artifact | Required content |
|---|---|
| Page Structure Table | route, purpose, reference, layout pattern |
| Field Display Contract | field, source of truth, label/i18n, format, empty/unknown, permission |
| Interaction Matrix | action, visible/enabled when, API called, success/failure |
| Frontend Action Inventory | action id, user intent, reachable from, side effect/API, success/failure, owner issue |
| Frontend Route Component Matrix | `UI-ACT-*`, visible action, source component, handler/route builder, final route/API, router definition, landing component/file, mode branch, forbidden inherited UI/API, verification, owner issue |
| Frontend Reference Pattern Matrix | required when source says reference/follow/like existing UI; reference id, target surface/action, reference source, reference file/component, must reuse/adapt, must not inherit, visual/layout obligation, interaction/state obligation, browser/visual proof, owner issue |
| Frontend Mode Field Display Matrix | surface, mode/state, data source, must show, must hide, fixture, assertion, owner issue |
| Frontend Form State Matrix | form/step, mode/state, active fields, inactive/hidden fields, reset/default, validation trigger, submit participation, error location |
| Frontend Leakage Negative Matrix | surface/action, forbidden DOM/text, forbidden payload, forbidden route/API, assertion method, owner issue |
| State Matrix | loading, empty, error, disabled, user action |
| i18n Contract | text, key pattern, file, notes |
| API Call Contract | purpose, method, final path, query/body, frontend caller, backend handler, unauth status, verification |
| Browser Verification Plan | route, viewport/session, expected visible behavior |
| Frontend Browser Verification Matrix | user task id, action id, browser steps, network assertions, DOM assertions, screenshot/trace, negative assertions, fixture refs |
| Frontend Decision Document | Layout/reference/field/action/i18n/API-route decisions, alternatives, reason, product alignment, impact, verification, Lark URL if available |

### Dimension Representation Map

| Dimension | Representation | Why this medium |
|---|---|---|
| Page/route | Page Structure Table | 路由、目的、参考、布局必须一行一页 |
| Reference page/component | Frontend Reference Pattern Matrix | “参考现有 UI”必须具体到文件/组件、复用/适配点、不可继承点、视觉/交互 proof 和 owner issue |
| Field display | Field Display Contract | source/i18n/format/empty/permission 需要逐字段 |
| Interaction/action | Interaction Matrix | visible/enabled/API/success/failure 必须并排 |
| Action route closure | Frontend Route Component Matrix | 用户点的 action 必须追到真实 source、handler/router、landing component 和 owner issue |
| Mode field display | Frontend Mode Field Display Matrix | 新旧 mode must show/must hide 需要逐 surface 验证 |
| Form state | Frontend Form State Matrix | 隐藏字段是否仍参与校验/提交必须可审计 |
| Leakage prevention | Frontend Leakage Negative Matrix | 旧 mode DOM/payload/route 泄漏必须有负向断言 |
| Loading/empty/error/disabled | State Matrix | 状态组合多，表格能暴露遗漏 |
| Permissions | Permission Matrix | UI 和 API 行为需要对齐 |
| i18n | i18n table | key/file/text pattern 需要可检查 |
| API call exact shape | API Call Contract table + exact request examples | 防止 path/query/body/auth 语义漂移 |
| Browser verification | Browser Verification Plan | 可见行为必须绑定路由、session、viewport、预期 |
| Row-level browser proof | Frontend Browser Verification Matrix | 每个 `UI-ACT-*` 必须有 click/network/DOM/screenshot-or-trace proof |

### Completeness Criteria

- Every visible field has source of truth and empty/null behavior.
- Every action has visible/enabled/success/failure behavior.
- Every `UI-ACT-*` has concrete source component, handler/route builder, router definition or explicit file-based route ownership, landing component/file, owner issue, and browser verification row.
- Owner Atomic Issue files include all source/handler/router/landing files referenced by its frontend action rows.
- Detail action dropdown, update-config, resize/capacity, progress/change, events/metrics/logs/workers are independent user surfaces; create smoke cannot close them.
- Every mode-specific surface has must-show and must-hide fields plus DOM/payload/route negative assertions.
- Every form mode/step states active fields, inactive/hidden fields, reset/default behavior, validation trigger, submit participation, and error location.
- Every API call uses exact frontend-visible path/query/body.
- Build/lint/typecheck/payload helper proof is supporting evidence only; it cannot close frontend action-flow. Not-run browser proof must backflow or bind to concrete mock frontend case id.
- UI reference is concrete; absent reference becomes open decision.
- If any source/PRD/AIP says reference/follow/like an existing UI, `frontend-reference-pattern-matrix.md` exists and every row is copied into owner packet `reference_ui_patterns`; field/payload/selector assertions alone cannot close visual/reference parity.
- Every frontend-stage decision is recorded in `decision-reviews/frontend-decisions.md`.
- UI decisions do not change product-visible behavior unless returned to PRD.

### Exit Gate

Implementation cannot decide UI layout, field visibility, button behavior, i18n key, API URL, or auth/empty/error handling.

## Stage 7: Cross-Module Contract

### Goal

锁定 N2，把问题域固有耦合变成可实现、可验证契约。

### Orthogonal Dimensions

- Candidate extraction from REQ/SCN/plan/archaeology/migration/AIP.
- Module contract graph.
- Provider/consumer ownership.
- Contract materialization source.
- Existing object/action variant consumer parity.
- Progress/change producer chain.
- External side-effect production/substitute boundary.
- Contract type.
- Trigger.
- Normal path.
- Failure path.
- Consistency.
- Timing.
- Verification.
- Conflict detection.
- Semantic consumption.

### Required Artifacts

| Artifact | Required content |
|---|---|
| Contract Candidate Table | candidate, source, modules/resources, scenario, needs contract |
| Locked Contract Detail | source, decision, trigger, normal, failure, consistency, timing, verification |
| Module Contract Graph | module, responsibility, owned state/data/resources, provided contracts, consumed contracts, boundary evidence |
| Provider/Consumer Assumption Matrix | contract, provider module, consumer module, consumer assumption, provider guarantee, mismatch decision |
| Contract Materialization Source Matrix | contract, provider guarantee facts, consumer assumption facts, field/state/error/timing details, preconditions for consumer tasks, obligations for provider tasks, forbidden interpretations |
| Contract Discovery Coverage Matrix | source area, evidence reviewed, contract candidates, locked contracts, residual risk, verification/not-run |
| Type-Specific Details | API fields, async semantics, DB migration, cloud, derived config, observability |
| DB/Migration Contract Detail | authoritative state owner, writer path, old required constraints, null/default/derived/forbidden/compat rule, write proof, readback proof, consumers |
| `existing-object-action-consumer-graph.md` | consumed archaeology evidence for old object/action/readback/post-create consumers |
| `variant-impact-matrix.md` | old consumer parity decisions; required consumer assumptions; contract candidates |
| `progress-change-producer-chain-matrix.md` | Progress / Change Producer Chain Matrix, Producer Chain Equivalence Matrix, Producer Chain Local Audit |
| `runtime-materialization-parity.md` | runtime mode classification; product capability baseline; runtime artifact/config/plugin/secret/bootstrap/readback obligations |
| `external-side-effect-contract-matrix.md` | External Side Effect Contract Matrix, Side Effect Alternative Decision Matrix, Side Effect Local Audit |
| Contract Conflict Matrix | conflict, contracts, options, decision, reason, verification |
| Contract List | ID, contract, type, source, modules, decision, verification, status |
| Contract-to-Atomic-Issue Map | contract, atomic issue, excerpt included, verification |
| Semantic Consumption Matrix | upstream REQ/SCN/PDEC/DEC/MIG/contract candidate, derived C-xxx/provider-consumer assumption/verification input, copied/dropped semantics, status |
| Contract Decision Document | N2 contract/failure/consistency/timing/conflict decisions, alternatives, reason, product alignment, impact, verification, Lark URL if available |

### Dimension Representation Map

| Dimension | Representation | Why this medium |
|---|---|---|
| Candidate extraction | Candidate Table | 每个候选必须有 source/modules/scenario/needs-contract |
| Module contract graph | Module Contract Graph | Atomic Issue 必须从模块 consumed/provided contract 生成 |
| Provider/consumer ownership | Provider/Consumer Assumption Matrix | 防止 consumer 假设没有 provider，或 provider 语义不满足 consumer |
| Contract materialization source | Contract Materialization Source Matrix | 确保契约能直接复制为 Atomic Issue 的前提、consumed snapshot、provided obligation 和禁止解释 |
| Contract executable obligation | Contract Executable Obligation Matrix | 把每条 contract 降解成 `edge type + edge + operation + surface + semantic type + canonical owner + fields/resource/state + failure + verification` 的最小可执行义务行，避免 task-planning 临场猜 owner |
| Contract discovery coverage | Contract Discovery Coverage Matrix | 防止只从显眼 API 找契约，漏掉共享数据、异步任务、cloud/runtime、observability 和 migration diff |
| Existing object/action variant consumer parity | Variant Impact Matrix + Provider/Consumer Assumption Matrix | 旧 consumer assumption 必须变成新形态 provider guarantee 或 locked N/A，不能只写 mode-specific |
| Progress/change producer chain | Progress / Change Producer Chain Matrix | progress/change/last-change 必须锁定生产 writer、state owner、task/event producer、correlation key、readback API、终态/失败和 owner issue |
| External side-effect production/substitute boundary | External Side Effect Contract Matrix | 锁定真实生产 owner/call、no-cloud/playground 替代边界、最低可接受 proof、failure/readback 语义 |
| Contract type | Type classification table | 不同类型有不同特化问题 |
| DB/Migration contract | DB/Migration Contract Detail | “persisted” 必须展开为 state owner、writer、schema/resource constraint 和 readback proof |
| Trigger | Contract detail table | 触发条件是契约入口，不能混在描述里 |
| Normal path | Contract detail table or sequence | 正常路径要表达两边状态变化 |
| Failure path | Failure matrix inside contract | 失败、不可用、超时必须逐类回答 |
| Consistency | Contract detail table | 一致性机制必须显式 |
| Timing | Timing/idempotency row | 顺序、并发、重试必须可审查 |
| Verification | Contract-to-verification map | 每条契约必须可证明 |
| Conflict detection | Contract Conflict Matrix | 契约间冲突必须记录 options/decision |
| Semantic consumption | Semantic Consumption Matrix | 证明上游语义已进入契约或明确 N/A/blocker |

### Completeness Criteria

- Every cross-module behavior from REQ/SCN and archaeology is handled.
- Module Contract Graph exists and every module has provided/consumed contracts or explicit N/A.
- Every consumed contract is matched to a provider contract; mismatches are decisions, not implementation TODOs.
- Provider guarantee satisfies consumer assumption for normal, failure, timing, and consistency semantics.
- Contract Materialization Source Matrix exists and every locked contract has provider facts, consumer facts, field/state/error/timing details, consumer preconditions, provider obligations, and forbidden interpretations.
- Contract Executable Obligation Matrix exists and every locked contract has explicit Edge type, Edge, Semantic type, Operation/surface, Canonical owner, Owner module, Fields/resource/state, Provider guarantee, Consumer assumption, Failure/timing, Verification proof, and actionable Split hint rows. The Markdown table must have exactly the canonical 16 columns; edge type values must not drift into Sub-obligation type, Semantic type, Operation/surface, Canonical owner, or Owner module. Owner module must be a concrete `MOD-*`, not `VER-*`, `Txxx`, proof text, or a semantic role.
- `contracts.yaml.contracts[C-xxx].provider_module` is owner-single. Multi-owner values such as slash/comma/and/or joined modules are invalid; coarse `C-xxx` may be a composition index, but executable provider ownership must live in owner-single obligations.
- `contracts.yaml.contracts[C-xxx].executable_obligations[]` is isomorphic with the Markdown matrix and includes `edge` as well as `edge_type`; YAML cannot rely on Markdown to supply missing Edge.
- Every locked contract can be copied into Atomic Issues without relying on ID-only references or global-doc context.
- Contract Discovery Coverage Matrix covers REQ/SCN, module dependency edges, shared data/resource, async task/event, frontend/API, deployment/cloud/runtime, observability, and migration diff sources.
- Every `variant-impact-matrix.md` row with `Must new variant satisfy?=yes` has a provider guarantee in Provider/Consumer Assumption Matrix and Contract Materialization Source Matrix.
- Every required old consumer assumption is either satisfied by the new variant, mapped to proof-only regression, or rejected by locked decision; unsupported-by-omission is invalid.
- Every progress/change/last-change/change-detail/task-step/event-step consumer has a `progress-change-producer-chain-matrix.md` row with canonical production writer, state owner/table, task/event producer, correlation key, last-change readback, change-detail readback, terminal/polling rule, failure behavior, verification, and owner issue.
- Producer chain rows prove same-object/same-created-id correlation from mutation API to last-change and change detail; an ID-only reference such as `VER-xxx id` is not enough.
- Mock/frontend/fixture rows may mirror producer output but cannot replace the production writer/readback chain.
- Every `runtime-materialization-parity.md` row has provider guarantees for product capability inputs and consumer assumptions for runtime readback/observability; resource-exists-only proof is invalid.
- Every external side effect has `external-side-effect-contract-matrix.md` row naming production side-effect owner, required production call/resource mutation, physical dependency policy, no-cloud/playground substitute boundary, minimum acceptable proof, failure/partial failure semantics, state/readback consumer, verification, and owner issue.
- No external side-effect contract can be closed by DB-only state, fixture-only event, frontend-only rendering, log-only hook, or compile/build proof unless a locked alternative decision explicitly says so and records product/ops impact.
- DB/Migration contracts for persistent mutations name state owner, writer, old required constraints, mode-specific null/default/derived/forbidden/compat rule, and readback consumers.
- Any residual risk from contract discovery enters Verification Matrix or Not Run Risk Table.
- No contract remains non-locked.
- Every locked contract enters Verification Matrix and at least one Atomic Issue.
- Every locked contract has provider module and consumer module.
- Public API contracts lock exact method/path/query/body/handler/auth smoke.
- Every contract-stage decision is recorded in `decision-reviews/contract-decisions.md`.
- Contract decisions must cite the PRD/AIP/archaeology source that constrains them.
- Semantic Consumption Matrix covers every upstream cross-module semantic object and contract candidate, with no blocked or unjustified dropped rows.

### Exit Gate

Implementation cannot infer module responsibility, provider/consumer assumptions, cross-module ordering, failure behavior, consistency, idempotency, or API route semantics.

## Stage 8: Verification Matrix

### Goal

验证前置，不让测试成为实现后的补救。

### Orthogonal Dimensions

- REQ coverage.
- SCN coverage.
- DEC coverage.
- Contract coverage.
- Migration coverage.
- API route coverage.
- Frontend/browser coverage.
- Runtime/representative fixture.
- Progress/change production chain proof.
- Old consumer parity proof for new variants.
- External side-effect proof.
- Runtime/test topology proof.
- Module boundary validation.
- Module composition verification.
- Not Run risk.
- Semantic consumption.

### Required Artifacts

| Artifact | Required content |
|---|---|
| Verification Matrix | source, behavior, type, command/manual step, required, risk |
| Verification Feasibility Gate | verification, source, required, environment/fixture, available, setup owner/command, fallback, blocks done |
| Expected Result Table | check, expected status/body/DB/UI/grep/plan/log result |
| Representative Fixture Table | source object, real-ish fields, missing-field case, verification, risk |
| Progress / Change Producer Chain Verification | mutation API, same object id, production writer proof, state owner proof, last-change readback proof, change detail readback proof, frontend/API consumer proof |
| Old Consumer Parity Verification | variant row, old consumer surface, new producer/behavior proof, negative/locked N/A proof, expected result |
| External Side Effect Verification | effect id, production owner/call, substitute boundary, proof command, expected readback/event/resource assertion, failure assertion |
| Runtime Test Topology Verification | topology id, proof file, freshness step, verification command, expected result, staleness risk |
| Runtime Smoke Plan | environment, exact request/action, expected, proves |
| Module Boundary Validation Matrix | module, boundary risk, validation type, step, expected, risk |
| Module Composition Verification Matrix | REQ/SCN, composition path, provider contracts, consumer assumptions, verification, expected, proves |
| Not Run Risk Table | check, source, severity, reason, risk, owner/approval, blocks done |
| Semantic Consumption Matrix | upstream REQ/SCN/PDEC/DEC/C/MIG, derived VER-xxx/not-run/N/A, copied/dropped semantics, status |
| Verification Decision Document | Test type/fixture/runtime/manual/not-run decisions, alternatives, reason, product alignment, impact, verification, Lark URL if available |

### Dimension Representation Map

| Dimension | Representation | Why this medium |
|---|---|---|
| REQ coverage | Traceability matrix | 每个 REQ 必须至少一个 proof |
| SCN coverage | Scenario-to-verification matrix | 场景级行为要能复现 |
| DEC coverage | Decision-to-verification matrix | 决策不能只记录不证明 |
| Contract coverage | Contract-to-verification matrix | 每条 N2 必须有 proof |
| Migration coverage | Migration verification table | delete/modify/compat 必须有安全证明 |
| API route coverage | API-route smoke table | exact URL/status/body 能防 404 和 path drift |
| Frontend/browser coverage | Browser verification table | 路由和用户可见状态需要可重复步骤 |
| Runtime/fixture | Representative Fixture Table | mock 不足以证明真实配置完整性 |
| Progress/change production chain | Progress / Change Producer Chain Verification | 证明 mutation API -> production writer/task/event -> state owner -> last-change -> change detail -> consumer 的同一对象 id 闭环 |
| Old consumer parity for new variants | Old Consumer Parity Verification | 旧 mode 的 post-create/progress/detail/list/logs/metrics 等 consumer 要么被新形态满足，要么有 locked N/A 和负向 proof |
| External side-effect proof | External Side Effect Verification | 证明真实产品路径跨过 provider/operator/API/runtime 边界，且 no-cloud 替代没有替代业务逻辑 |
| Runtime/test topology proof | Runtime Test Topology Verification | 证明 proof owner 文件、freshness step 和跨模块测试命令在实现前已可执行 |
| Module boundary validation | Boundary validation matrix | 防止模块划分错误导致所有 issue 局部正确但整体错误 |
| Module composition verification | Composition verification matrix | 证明 provider/consumer 契约组合后满足 REQ/SCN |
| Not Run risk | Not Run Risk Table | 未验证行为必须显式承担风险 |
| Semantic consumption | Semantic Consumption Matrix | 证明每个上游语义有 proof、Not Run 或 locked N/A |

### Completeness Criteria

- Every REQ/SCN/DEC/Contract/Migration maps to proof.
- Every required verification has feasibility checked before Atomic Task Planning.
- Every core module boundary risk maps to proof or Not Run risk.
- Every critical REQ/SCN has at least one module-composition verification.
- Every consumed contract has a provider contract and at least one verification proving provider output satisfies consumer assumption.
- Every API route has exact route smoke if frontend or external caller uses it.
- Every cloud/derived/deployment behavior has representative fixture or runtime smoke.
- Every progress/change producer chain has producer proof and readback proof for the same object id; frontend fixture, final state, or DB-only row is supporting proof only.
- Every old consumer parity row required by `variant-impact-matrix.md` has a verification row proving new producer behavior satisfies the old consumer assumption or proving locked N/A behavior.
- Every `external-side-effect-contract-matrix.md` row has verification proving the minimum acceptable production side-effect proof and locked failure/readback behavior.
- Every `runtime-materialization-parity.md` mapping row has verification proving materialized artifact/config/plugins/secrets/bootstrap/readback, or a locked product/API/UI unsupported expression.
- Every `runtime-test-topology-matrix.md` row has verification command and required freshness/build step; proof files must be marked for task allowlist consumption before task planning.
- Every verification can be copied into Atomic Issue with expected result and proves.
- Every verification-stage decision is recorded in `decision-reviews/verification-decisions.md`.
- Not Run choices are explicit decisions with owner/risk, not omissions.
- P0/P1、核心 REQ/SCN、关键跨模块契约、组合验证、runtime lifecycle 或 `Blocks done=yes` 的 Not Run 阻塞完成声明。
- Semantic Consumption Matrix covers every upstream REQ/SCN/PDEC/DEC/C/MIG, with no blocked or unjustified dropped rows.

### Exit Gate

Implementation cannot complete with “works by inspection” or “tests later”.

## Stage 9: Atomic Task Planning

### Goal

把全局设计转成可独立派发的 Atomic Issues。

### Orthogonal Dimensions

- Task index.
- Atomic Issue body.
- Module contract closure.
- Module-to-issue coverage.
- Contract closure coverage.
- Contract materialization.
- Semantic carrier projection.
- Contract executable obligation ownership.
- Contract owner legitimacy.
- Existing object/action consumer inheritance.
- Variant parity task ownership.
- Progress/change producer task ordering.
- External side-effect task ownership.
- Proof owner allowlist.
- Semantic load split.
- Requirement composition coverage.
- Source intake closure.
- Decision consistency.
- Task DAG.
- Backflow invalidation.
- Semantic consumption.
- Source context excerpt.
- Decision excerpt.
- Contract excerpt.
- Code references.
- Files to change.
- Implementation steps.
- Verification expected result.
- Prohibited changes.
- Done criteria.

### Required Artifacts

| Artifact | Required content |
|---|---|
| `tasks.md` | sealed task index, dependency order, initial status, links to Atomic Issues |
| `workflow-state.yaml.task_receipts` / `task-verification-log.yaml` / `execution-state.yaml` | execution admission, task status, verification log, not run, decision gaps |
| `atomic-issues/Txxx.md` | self-contained issue with all sections |
| Atomic Issue Coverage Map | REQ/SCN/DEC/Contract/Migration -> Txxx |
| Module-to-Issue Map | module -> issue -> consumed contracts -> provided contracts |
| Contract Closure Coverage Map | contract -> provider issue -> consumer issue -> composition verification -> excerpt copied |
| Contract Materialization Coverage Map | contract -> provider facts copied -> consumer facts copied -> preconditions copied -> obligations copied -> forbidden interpretations copied |
| Semantic Carrier Projection Matrix | dense `REQ/SCN` -> `SCP-xxx` owner slice -> owner module -> owner task -> packet carrier row -> excluded sibling owner semantics |
| Obligation Row To Task Map | `Contract Executable Obligation Matrix` row ID -> decomposed edge -> provider/consumer decision -> merge/split decision -> task-dag task -> packet execution section -> verification |
| Owner Legitimacy Matrix | decomposed edge row -> row kind -> edge type -> canonical owner module -> proposed provider task -> task primary module -> valid-owner / carrier-only / proof-only / invalid-backflow |
| Provider Ownership Propagation Check | Txxx -> task-dag provides/provides_obligations -> packet provided_contract_obligations -> compiled issue provider claims -> carrier/proof refs moved out of provider sections |
| Mechanism Row To Task Map | `MECH/OPSEQ/EXTAPI/EVT/RMM/RLM/FCM/MIM` row -> contract obligation -> verification -> task-dag task -> packet execution section -> owner/proof |
| Existing Object-Action-Consumer Consumption Map | `existing-object-action-consumer-graph.md` row -> derived contract/task/proof/locked N/A |
| Variant Parity Task Map | `variant-impact-matrix.md` parity row -> provider task -> consumer task or proof-only -> verification |
| Progress / Change Producer Task Map | `progress-change-producer-chain-matrix.md` chain row -> writer task -> readback verification -> frontend/API consumer task/proof -> DAG edge |
| Runtime Materialization Task Map | `runtime-materialization-parity.md` mapping row -> runtime materialization provider task -> consumer/readback proof -> DAG edge |
| External Side Effect Task Map | `external-side-effect-contract-matrix.md` row -> provider/runtime owner task -> failure/readback proof -> consumer task/proof -> DAG edge |
| Proof Owner Allowlist Matrix | verification row -> owner task -> proof file -> packet files_to_change -> task-dag files -> freshness step |
| Semantic Load Split Matrix | candidate Txxx -> module/layer/provider/state/consumer/verification counts -> split decision/backflow |
| Frontend Reference Pattern Packet Map | reference pattern row -> frontend owner issue -> `reference_ui_patterns` execution section -> browser/visual proof |
| Requirement Composition Coverage Map | REQ/SCN -> module composition path -> provided contracts -> verification -> issue |
| Source Intake Closure Summary | behavior-affecting sources read/mapped, conflicts locked, no blocked source |
| Decision Consistency Matrix | decision key, active locked decision, conflicts, supersession status |
| Task DAG | DAG Nodes, DAG Edges, Topological Execution Order, Parallel Groups |
| Backflow Invalidation Matrix | trigger, invalidated DEC/C/T/VER, affected issues, verification rerun, new status when any backflow exists |
| Semantic Consumption Matrix | upstream REQ/SCN/PDEC/DEC/C/MIG/VER, derived Txxx, copied semantics into issue, dropped semantics reason, status |
| Verification Feasibility Gate | required verification copied into tasks/issues with environment/fixture/setup owner |
| Version Branch Alignment Matrix | cross-repo/version/template assumptions if relevant |
| Artifact Rubric Scorecard | required dimensions scored 0/1/2 with evidence/fix |
| Atomicity Re-Splitting Review | candidate task, primary closure, action-flow/stateful operation/provided contract/verification loop counts, split candidates considered, strong merge rationale, owner issue/backflow |
| Task Planning Decision Document | Task boundary/dependency/scope/prohibited-change decisions, alternatives, reason, product alignment, impact, verification, Lark URL if available |

### Dimension Representation Map

| Dimension | Representation | Why this medium |
|---|---|---|
| Task index | `tasks.md` index table/checklist | 只表达顺序、状态、依赖和链接 |
| Atomic Issue body | Atomic Issue template | 执行上下文必须完整闭包 |
| Module contract closure | Module closure table | issue 必须绑定一个模块并声明 consumed/provided contracts |
| Module-to-issue coverage | Module-to-Issue Map | 防止模块没有 owner issue 或多个 issue 暗中跨模块 |
| Contract closure coverage | Contract Closure Coverage Map | 防止契约只在全局文档存在，没有进入 provider/consumer issue |
| Contract materialization | Contract Materialization Coverage Map + issue sections | 防止 Atomic Issue 只有契约引用，没有执行前提、可依赖事实和交付义务 |
| Semantic carrier projection | Semantic Carrier Projection Matrix + `semantic-objects.yaml.semantic_carrier_projections` | 防止全局 `REQ/SCN` dense carrier 被整段塞给每个 task；每个 task 只拿 owner-specific `SCP-xxx` |
| Contract executable obligation ownership | Obligation Row To Task Map | 防止 `Contract Executable Obligation Matrix` 的最小义务行只停留在 contract 阶段，或在 task-planning 被粗 `C-xxx` / owner closure 压扁 |
| Contract owner legitimacy | Owner Legitimacy Matrix | 防止 API/DTO/frontend/proof carrier task 被误建模成 runtime/resource/external side effect 的 semantic provider；先证明 owner 合法，再允许合并 |
| Mechanism row ownership | Mechanism Row To Task Map | 防止设计阶段机制行在 task-planning 被 owner 合并压缩，导致任务仍需实现期考古 |
| Existing object/action consumer inheritance | Existing Object-Action-Consumer Consumption Map | 防止旧 consumer assumption 只停留在考古文档，没有进入 owner packet |
| Variant parity task ownership | Variant Parity Task Map | 每个 must-satisfy old consumer row 必须有 provider task、consumer task 或 proof-only，而不是让实现阶段自行发现 |
| Progress/change producer ordering | Progress / Change Producer Task Map + Task DAG | 生产 writer/readback 必须先于 progress/change consumer；fixture/frontend proof 不能替代 producer issue |
| External side-effect task ownership | External Side Effect Task Map | 外部副作用 provider/runtime owner 先于 service/readback/UI consumer；no-cloud proof 不替代生产 owner |
| Proof owner allowlist | Proof Owner Allowlist Matrix | Verification proof 文件必须从验证矩阵自动进入 packet/task-dag allowlist，避免执行期手工 recovery |
| Semantic load split | Semantic Load Split Matrix | 多模块、多层、多 producer/consumer、多验证闭环的任务默认拆分，弱合并理由无效 |
| Requirement composition coverage | Requirement Composition Coverage Map | 防止所有 issue 局部正确但 REQ/SCN 组合路径未证明 |
| Source intake closure | Source Intake Ledger summary | 防止漏读输入后生成错误任务 |
| Decision consistency | Decision Consistency Matrix | 防止冲突决策同时进入 issue |
| Task DAG | Task DAG | 任务顺序必须由 provider/consumer、文件 ownership、verification gate 证明 |
| Backflow invalidation | Backflow Invalidation Matrix | 回流后必须使旧 DEC/C/T/VER 失效并重写/重跑 |
| Semantic consumption | Semantic Consumption Matrix | 证明所有上游语义最终进入 issue 或被 locked N/A/blocker |
| Source context excerpt | Source Context section | worker 不能只拿 ID |
| Decision excerpt | Locked Decisions table | 防止实现阶段重新做选择 |
| Contract excerpt | Contract Excerpts table | 跨模块语义要进入 issue 本体 |
| Execution preconditions | Execution Preconditions table | worker 必须知道执行前世界已经成立的事实和证据 |
| Consumed contract snapshot | Consumed Contract Snapshot table | worker 必须拿到可直接依赖的 provider/consumer 事实、字段、状态、错误、时序 |
| Provided contract obligation | Provided Contract Obligation table | worker 必须知道当前任务给下游交付什么可观察保证 |
| Invariant carryover | Invariant Carryover table | 旧语义、兼容性、权限、错误和状态约束必须被保留 |
| Preconditions failure handling | Preconditions Failure Handling table | 前提不成立必须停止回流，不能实现阶段补猜 |
| Code references | Existing Code References table | 明确照哪个文件/方法/页面 |
| Files to change | Files To Change table | 控制 scope 和 ownership |
| Implementation steps | Ordered step list | 让 worker 不重新拆方案 |
| Verification expected result | Verification table | 命令、预期、证明对象必须闭合 |
| Atomicity review | `atomicity_review` sidecar + compiled issue section | 防止把“同模块/同页面/相关工作”误当成原子任务 |
| Prohibited changes | Prohibited Changes list | 防止顺手重构和 scope 扩张 |
| Done criteria | Done checklist | 明确完成标准 |

### Completeness Criteria

- Every task has one Atomic Issue.
- Every implementation issue has an `atomicity_review` proving one primary closure: one user action-flow, one stateful operation, one provided contract, or one short verification loop.
- Any issue with multiple action rows, multiple stateful operations, multiple verification loops, broad title/scope, or cross-layer bundle has a strong merge rationale; weak reasons such as same module/page/related work/task count are not accepted.
- Candidate task groups such as `post-create consumers`, `frontend UX`, `fixture graph`, `representative acceptance`, `完整前端` are split before execution unless `atomicity_review` proves one inseparable closure.
- Every implementation issue has one primary module, except pure verification issues.
- Every implementation issue states consumed contracts assumed true and provided contracts implemented/preserved.
- Every non-document issue contains Execution Preconditions, Consumed Contract Snapshot, Provided Contract Obligation, Invariant Carryover, and Preconditions Failure Handling with executable facts, not IDs or summaries.
- Every dense `REQ/SCN` that feeds multiple owner modules or multiple tasks has `semantic_carrier_projections` with `SCP-xxx`, owner module, owner task, operation/surface, semantic type, owner-specific semantics, excluded sibling owner semantics, verification, and packet carrier row.
- Every `task-dag.yaml.tasks[Txxx].semantic_carriers` entry that references `SCP-xxx` resolves to a projection owned by that Txxx, and the owner packet carries the same `projection_id`.
- No task is required to copy the full global `REQ/SCN` dense carrier merely because it lists that source in `sources`; validator must check the task-local owner slice.
- Every consumed contract snapshot includes provider task/module, consumer-usable assumption, field/state/error/timing details, and forbidden interpretations.
- Every provided contract obligation includes downstream consumer, observable output/state, and verification proving the obligation.
- Every issue states what to do if preconditions are false: stop, classify the gap, update backflow, and return to the missing upstream stage.
- No implementation issue redefines module boundaries or cross-module contracts.
- Every core module in Module Contract Graph appears in Module-to-Issue Map or is explicitly N/A with reason.
- Every locked contract has provider issue, consumer issue or explicit N/A, and composition verification.
- Every active `Contract Executable Obligation Matrix` row has an owner mapping by row ID: decomposed edge row, provider/consumer decision, merge/split decision, task-dag task, owner packet execution section, and verification. Coarse `C-xxx` consumption alone is insufficient.
- `task-dag.yaml.tasks[Txxx].provides` may list coarse `C-xxx` only when the same task owns and lists every `semantic_contract_edge` `C-xxx-OBL-yyy` under that contract. Otherwise coarse `C-xxx` remains a composition index, and owner tasks list only their `provides_obligations`.
- `task-dag.yaml.tasks[Txxx].provides_obligations` may list only active owner-single `semantic_contract_edge` rows. Carrier, prerequisite, proof-only, fixture, browser harness, build freshness, and acceptance proof rows are not provider obligations.
- Every provider guarantee row passes Owner Legitimacy Matrix before merge/split: proposed provider task primary module matches the canonical owner module that owns the state/schema/resource writer/external adapter/event producer/UI action/proof that makes the guarantee true.
- Carrier/order rows such as API wire shape, DTO, request carrier, route handoff, proof file, fixture, build freshness, or browser harness are represented as `carrier_order_edge`, `verification_prerequisite_edge`, or `proof_only_edge`; they are not counted as semantic contract `provides`.
- Provider ownership propagation is exact across `task-dag.yaml`, `atomic-issue-packets.yaml`, and compiled `atomic-issues/Txxx.md`: a packet or issue cannot say `owns/provides/guarantees/implements C-xxx` unless the same Txxx lists that contract or canonical obligation in task DAG `provides/provides_obligations`. Carrier/proof/consumer tasks may mention those contracts only as consumed assumptions, prerequisites, carriers, or proof targets.
- Any task DAG provider/consumer rewrite invalidates old packet provider text. The affected packet must be regenerated from scratch; stale `provided_contract_obligations`, `primary_closure`, scope, module responsibility, and done criteria from the previous owner assignment are blocker defects.
- A provider guarantee has exactly one semantic provider task owner. Additional tasks may be consumers, carriers, prerequisites, or proof-only tasks, but they cannot share the same provider obligation unless the contract was decomposed into separate owner rows.
- Task Merge Split Decision Matrix only admits merge rows whose Owner Legitimacy Matrix result is valid for every candidate row; merge is an exception after owner proof, not a mechanism to repair owner mismatch.
- Any high-risk obligation row touching external side effects, runtime materialization/parity, managed resource cleanup/protect, HPA/autoscaling/scaling policy, progress/change/event producers, or failure consistency/residual cleanup is split by default unless the merge rationale proves same primary module, same semantic type, same operation/surface, and same short verification loop for each row ID.
- Every `existing-object-action-consumer-graph.md` row is consumed by Atomic Planning Context Pack and mapped to contract/task/proof/locked N/A.
- Every `variant-impact-matrix.md` parity row with `Must new variant satisfy?=yes` is decomposed into provider obligation and consumer implementation/proof decision.
- Every `progress-change-producer-chain-matrix.md` row is decomposed into production writer/readback owner task and consumer/proof task when needed; packets carry `change writer`, `last-change`, `change detail`, `correlation`, and `progress/change producer` semantics in execution sections.
- Task DAG has explicit edge from runtime/change producer to progress/change consumer; related runtime side effect tasks must unlock producer proof before consumer proof can pass.
- Every `external-side-effect-contract-matrix.md` row is decomposed into production side-effect owner task and failure/readback/consumer proof; packets carry `external_side_effects`, production call/mutation, substitute boundary, minimum proof, and failure semantics.
- Every `runtime-materialization-parity.md` row is decomposed into runtime materialization owner task and readback/consumer proof; packets carry mode classification, product capability baseline, artifact/config/plugin/secret/bootstrap/entrypoint/readback obligations, and negative shortcut assertions.
- Every `runtime-test-topology-matrix.md` proof file marked required appears in owner packet `files_to_change` and `task-dag.yaml.files`; required freshness/build step appears in verification/precondition.
- Semantic Load Split Matrix exists and any candidate with multiple primary modules, provider side-effect owners, state/event/progress producers, readback/consumer owners, verification loops, or cross-module build/test is split unless a strong merge rationale proves same primary module, same semantic type, same operation/surface, and same short verification loop.
- Every critical REQ/SCN has Requirement Composition Coverage; module-local unit tests are not enough.
- Source Intake Ledger has no behavior-affecting unread/blocked source and no open source conflict.
- Decision Consistency Matrix has no active conflict.
- Task DAG includes every task as a node, every dependency edge has reason, and topological order is valid.
- Parallel groups have disjoint files, disjoint contracts, and no shared verification pollution.
- If any DEC/C/T/VER was superseded, Backflow Invalidation Matrix exists and no active Atomic Issue references old objects.
- Semantic Consumption Matrix maps every required upstream object to Txxx or locked N/A/blocker.
- Verification Feasibility Gate has no unavailable required verification that is treated as done.
- Version Branch Alignment Matrix is present and aligned when multi-repo/version/template assumptions exist.
- Artifact Rubric Scorecard has no required dimension scored 0.
- Atomic Issue can be executed without reading full global docs.
- Atomic Issue contains exact source/decision/contract excerpts, not only IDs.
- Atomic Issue can be copied into a GitHub issue and independently assigned.
- Atomic Issue Source Context includes behavior details and boundary conditions needed for implementation.
- Atomic Issue Files To Change uses exact repo-relative paths or precise new-file rules; no vague "new helper under ..." scope.
- Atomic Issue Verification includes failure meaning / Not Run risk, not only expected pass.
- Verification includes command/step, expected result, proves.
- No execution-facing section treats planned rows as completed proof. Phrases such as planned browser action, rows do not execute tests yet, score 2 planned, or future Playwright cannot close an executable task.
- P0/P1 or `Blocks done=yes` Not Run cannot be treated as done.
- Scope and prohibited changes prevent opportunistic refactor or local decisions.
- Every task-planning decision is recorded in `decision-reviews/task-planning-decisions.md`.
- Task boundaries do not hide missing design or contract decisions.

### Exit Gate

A worker can take any Txxx independently and finish without asking product/architecture/module-boundary/contract questions.

## Stage 10: Atomic Execution

### Goal

只执行，不决策。

### Orthogonal Dimensions

- Pre-execution issue completeness check.
- Scoped file reads.
- Implementation.
- Short-loop verification.
- Verification log.
- Decision gap handling.
- Not Run risk.
- Backflow invalidation.
- Task DAG adherence.

### Required Artifacts

| Artifact | Required content |
|---|---|
| Updated Atomic Issue | progress/blocker if needed |
| Task receipts and execution log | `workflowctl.py begin-execution/admit-task/validate-task-diff/pass-task` receipts, `task-verification-log.yaml`, not run, decision gaps, DAG/blocker status |
| Backflow Invalidation Matrix | new trigger and invalidated DEC/C/T/VER when execution discovers gap |
| Code diff | only scoped files unless issue updated |

### Dimension Representation Map

| Dimension | Representation | Why this medium |
|---|---|---|
| Issue completeness check | Pre-execution checklist | 先阻断不合格 issue |
| Scoped file reads | Files-read log or issue notes | 确保不扩大上下文和 scope |
| Implementation | Code diff | 实际变更必须可 review |
| Short-loop verification | `task-verification-log.yaml` row plus `pass-task` receipt | 每步结果要 fresh |
| Decision gap | Decision Gap table | 新决策必须停下并回写 |
| Not Run risk | Not Run table | 未跑验证必须显式风险 |
| Backflow invalidation | Backflow Invalidation Matrix | 执行中发现 gap 必须让受影响任务失效 |
| Task DAG adherence | DAG predecessor check | provider/verification predecessor 未完成时不能执行 consumer |

### Completeness Criteria

- Every executed issue passes its own verification or records Not Run risk.
- New decisions stop execution and update Decision Registry.
- Contract/source/verification changes update Backflow Invalidation Matrix before continuing.
- Execution follows Task DAG; consumer task cannot run before provider and verification predecessor.
- Missing context is classified as `atomic-issue-not-self-contained`, not silently guessed.
- Missing contract materialization is classified as `contract-materialization-gap`; execution stops and backflows to contract/task planning before code changes continue.
- P0/P1 or `Blocks done=yes` Not Run blocks done unless explicitly risk-accepted by user/owner.

### Exit Gate

No task is marked done without fresh verification result, no active backflow invalidation, and no unaccepted blocking Not Run risk.

## Stage 11: Deployment / Runtime Smoke

### Goal

证明真实或拟真环境中的边界，而不是只证明编译和单测。

### Orthogonal Dimensions

- Version/image/commit identity.
- Root health/login redirect.
- Changed exact API routes.
- Auth/permission smoke.
- Frontend route smoke.
- Representative runtime fixture.
- Logs/metrics if relevant.
- Backflow invalidation after runtime finding.

### Required Artifacts

| Artifact | Required content |
|---|---|
| Deployment Record | branch, commit, workflow run, image, host/container |
| Runtime Smoke Table | exact URL/action, expected, actual, proves |
| Not Verified Runtime Risk | skipped smoke, source, severity, reason, risk, owner/approval, blocks done |
| Runtime Backflow Record | runtime finding, invalidated contracts/tasks/verification, rerun status |

### Dimension Representation Map

| Dimension | Representation | Why this medium |
|---|---|---|
| Version/image/commit identity | Deployment Record table | 证明部署的是哪份代码 |
| Root health/login redirect | Health check row | 只证明服务起来，不证明功能 |
| Changed exact API routes | Runtime Smoke Table | exact URL/status/body 防止 404 和路由漂移 |
| Auth/permission smoke | Auth smoke rows | 登录保护 API 应返回鉴权错误而非 404 |
| Frontend route smoke | Browser/manual route table | UI 变更必须证明可见路径正常 |
| Representative runtime fixture | Fixture smoke table | 证明真实/拟真数据能跑 |
| Logs/metrics | Observability smoke table | 观测变更必须有证据 |
| Runtime backflow | Backflow Invalidation Matrix | 真实环境发现的语义变化必须回流而不是只修代码 |

### Completeness Criteria

- Every changed API route has exact external URL smoke.
- Login-protected API returns auth error, not 404.
- Frontend route is reachable and not blank if UI changed.
- Runtime smoke is reported separately from root health.
- Runtime P0/P1 Not Run or failed smoke blocks done.
- Runtime findings that change DEC/C/VER/T trigger Backflow Invalidation Matrix.

### Exit Gate

“部署成功” cannot mean only container is up; changed behavior must be smoke-tested.

## Stage 12: Convergence Retrospective

### Goal

把返工变成 workflow 改进。

### Orthogonal Dimensions

- Convergence item classification.
- N1/N2 split.
- Root cause.
- Should-have-caught-by stage.
- Workflow fix.
- Skill/current/pattern update.
- Metric trend.
- Source intake / decision consistency / Task DAG / backflow / Not Run closure.

### Required Artifacts

| Artifact | Required content |
|---|---|
| Convergence Classification | item, symptom, category, root cause, should-have-caught-by, workflow fix |
| Metrics Table | total, N2 expected, N1 avoidable, gaps by type |
| Retrospective Actions | action, target skill/current/pattern, reason, owner |
| Backflow/Closure Fixes | source intake fix, decision consistency fix, Task DAG fix, backflow invalidation fix, Not Run blocking fix |

### Dimension Representation Map

| Dimension | Representation | Why this medium |
|---|---|---|
| Convergence item classification | Classification table | 每个问题必须归类和定位 |
| N1/N2 split | Metrics table | 判断是否接近理论下限 |
| Root cause | Root cause column | 不能只描述现象 |
| Should-have-caught-by | Stage mapping column | 明确哪个阶段 artifact 缺失 |
| Workflow fix | Workflow fix column | 每个 N1 必须有改进动作 |
| Skill/current/pattern update | Retrospective Actions table | 复盘必须落地 |
| Metric trend | Metrics table across runs | 后续验证 workflow 是否改进 |
| Closure fixes | Backflow/Closure Fixes table | 防止复盘只解释现象，不修 workflow 闭环 |

### Completeness Criteria

- Every convergence item classified.
- Every N1 avoidable has actionable workflow fix.
- `atomic-issue-not-self-contained` records missing issue section.
- `sdd-template-overfit` records artifact that should be added or expanded.
- `source-intake-miss` records missed source and affected semantic objects.
- `decision-conflict` records conflicting Decision key and supersession fix.
- `task-dag-miss` records missing/incorrect edge and corrected topological order.
- `backflow-invalidation-miss` records invalidated DEC/C/T/VER and rerun status.
- `not-run-completion-leak` records blocked check and corrected done/risk status.

### Exit Gate

No retrospective ends with explanation only; it must update or prescribe updates to skill/current/pattern/verification.
