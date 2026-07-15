---
name: product-requirement-design
description: 写或补齐产品需求文档。Use before AIP or engineering design when a new feature or major change needs user-facing product semantics, scope, non-goals, configuration, states, errors, permissions, scenarios, acceptance criteria, and product decisions locked before AI coding.
---

# Product Requirement Design

## 定位

这是大需求 workflow 的第一阶段：把“用户视角的产品定义”写清楚。

它不写技术方案，不决定代码结构。它的目标是消除产品层面的模糊决策，避免 AI 在实现阶段替产品做选择。

任何输入都不是最终 PRD。无论用户给的是飞书文档、issue、标题、口头描述、对话上下文、PRD 草稿，还是看起来已经很像 PRD 的文档，都必须先视为 `Propose / Source`：只代表“用户希望做什么”的原始材料。真正的 PRD 必须由本 workflow 读取 source、理解当前项目现状、抽取待决策点、完成用户确认或 AI 授权后重新生成。

执行或评审本阶段时，必须按 `ai-dev-methodology/references/artifact-completeness-spec.md` 的 “Stage 1: Product Requirement / PRD” 检查正交维度、Required Artifacts、Completeness Criteria 和 Exit Gate。

## 需求讨论到 PRD 的决策纪律

用户最初可能只给几句话。不能把几句话直接润色成完整 PRD；必须先主动枚举产品待决策点，并让用户确认或授权 AI 采用推荐决策。

对话输入也必须纳入 Source Intake Ledger，按一句或一组相关描述抽取 propose statement、确定事实、推断事实和未知事实。不得因为“这是用户刚刚说的”就跳过 source trace。

需求讨论阶段是唯一允许产品语义不确定的阶段。PRD 完成后，所有产品决策必须为 `locked`，不得把产品 open question 留给 AIP、设计或实现阶段。

如果用户给的是已有需求文档、飞书文档、issue 或 PRD 草稿，不能直接把原文当作合格 PRD。必须先读取原文，做 PRD normalization：按本 skill 的结构重写成新的完整 PRD，保留原文 source trace，并单独抽取缺失决策。

如果用户同时提供补充设计文档、AIP、Terraform/API 设计、接口草案、历史方案或外部链接，这些不是“可选参考”，而是 PRD normalization 的输入来源。必须读取并纳入 Source Trace / Research Evidence，标明每个补充文档锁定了哪些产品语义、接口语义或部署模式语义。未读取用户提供的补充链接时，不得把相关决策标记为 locked。

如果需求依赖外部事实或领域知识，必须先调研再锁定相关决策。外部事实包括但不限于：飞书文档、GitHub issue/PR、官方文档、第三方 API/云服务限制、竞品/行业行为、现有代码实现、线上或部署环境行为。调研结论必须写入 PRD 或 PRD 决策文档，不能只留在聊天中。

未验证的外部假设不能作为 locked product decision。只能作为 assumption/risk，或形成 open decision 等待确认。

## Propose 到 PRD 的强制流程

本阶段必须按顺序执行：

1. 登记所有输入到 `source-intake-ledger.md`，包括对话输入。
2. 把所有输入都标为 Propose / Source，抽取 “要做什么” 和 “为什么要做”。
3. 在写 PRD 前，对当前项目中与 propose 相关的产品现状和代码现状做一次范围内完整了解。
4. 基于 source + 当前现状，使用 `ai-dev-methodology/templates/decision-surface-discovery.md` 枚举 Decision Surface Discovery，先发现所有需要决策的 surface，再枚举 PRD 完整度维度和待决策点。
5. 如果用户没有明确授权 AI 做产品决策，必须把每个待决策点交互式给用户确认；不能自行锁定。
6. 用户确认或授权 AI 决策后，生成 workflow-owned PRD。
7. 对生成的 PRD 执行 PRD Completeness Gate；不通过则继续补 source、代码理解或用户决策。

### 当前项目现状理解门禁

PRD 写作前必须按 `ai-dev-methodology/templates/code-scope-discovery.md` 读取与 propose 相关的当前项目实现，产出 `Code Scope Discovery` 和 `Current Product/Code Understanding`。这不是完整 code archaeology，也不替代后续 `code-archaeology-sdd`；它只回答“当前产品已经怎么做、用户现状是什么、哪些行为不能在 PRD 中凭空定义”。

必需通过结构：

```markdown
## Current Product/Code Understanding

| Area | Current behavior | Evidence path / command | Product implication | Gap / decision |
|---|---|---|---|---|
```

必须覆盖：

- 现有页面、API、配置、状态、错误、权限、运行时能力中与 propose 相关的部分。
- 与新需求同类的已有 mode / feature / resource 的当前用户行为。
- 用户说“参考、类似、复用、沿用、改造、优化”的对象。
- 如果当前代码中找不到对应实现，必须记录查找方式和结论，不能假设不存在。

规则：

- 只允许读取与 propose 相关的代码和文档；不要在 PRD 阶段做完整模块设计。
- 代码理解必须具体到 repo path、类/页面/API/配置文件或命令输出摘要。
- 不能只写“参考现有实现”；必须写当前现有行为对 PRD 决策的影响。
- 如果当前实现和 propose 冲突，必须形成 PDEC 或 open question。
- 每个 required area 必须有 `Stop condition met?=yes`，或记录 blocker。
- 没有 Current Product/Code Understanding，不得生成 locked PRD。

### 用户决策交互门禁

如果用户没有明确授权 AI 做产品决策，必须使用 `ai-dev-methodology/templates/user-decision-interaction.md` 产出 `User Decision Interaction`。

规则：

- “你来决定/按推荐方案/默认你判断”才算 AI 授权；普通需求描述不算授权。
- 每个 PDEC 必须有推荐方案、备选方案、推荐理由、用户影响和验证方式。
- 用户确认后，必须把确认内容写回 PDEC 详情和 Decision Registry。
- 用户回答模糊、跳过或未响应时，PDEC 保持 `open`，阻塞 PRD 完成。
- 一次交互只问当前 PRD locking 必需的最小问题集，避免把工程细节问题提前甩给用户。

### Decision Surface Discovery 门禁

PRD locking 前必须生成或更新：

```text
specs/changes/<change-id>/decision-surface-discovery.md
```

如果只是 purpose / 目标描述，不能假设 AI 已经自然想到所有决策点。必须用该 artifact 强制枚举：

- mode consumer：新/改 mode 会被哪些页面、API、任务、下游对象、mock/playground 消费。
- capability：logs、metrics、workers、connectors、update-config、resize、delete、events 等能力在每个 mode 下是支持、隐藏、禁用、unavailable 还是需要实现。
- frontend action：每个可见按钮、下拉项、tab action、wizard submit 的落点和 mode 分支。
- post-create consumer：对象创建成功后，哪些消费者会读取或操作它。
- persistent mutation：哪些旧 required 字段/资源在新 mode 下可能不再必然存在。
- runtime lifecycle、observability、permission、compatibility、mock/playground。

规则：

- `needs-decision` 阻塞 locked PRD，除非用户明确授权 AI 按推荐方案决策。
- 产品层能决定的支持/不支持/隐藏/禁用/unavailable 必须转成 PDEC。
- 工程层才能决定的 provider/contract/verification 必须进入后续 AIP/readiness/contract，不得在 PRD 中假装已解决。
- 该文件后续必须被 `requirement-readiness-review`、`code-archaeology-sdd`、`frontend-contract-design` 和 `atomic-task-planning` 消费；不能只作为附录。

### 决策确认流程

1. 从所有 Propose / Source 中提取确定事实、推断事实和未知事实。
2. 如果输入包含已有需求文档，逐条映射原文到标准 PRD 维度，标记缺失、冲突、模糊和不可验证项。
3. 完成 Current Product/Code Understanding，识别当前产品行为对 PRD 的约束。
4. 如果需求依赖外部知识，先完成必要调研，记录 evidence、source URL/path、可信度和影响的决策。
5. 按用户、场景、对象、scope/non-goals、配置、状态、错误、权限、兼容、验收逐维度枚举待决策点。
6. 对每个待决策点给出推荐决策、备选方案、推荐理由、影响范围和验证方式。
7. 如果用户没有明确授权 AI 做产品决策，必须先暂停 PRD locking，向用户确认每个待决策点。
8. 用户确认，或用户明确授权 AI 按推荐决策锁定后，才能写 locked PRD。
9. 写 PRD 时只能使用已确认、已授权或已有证据支撑的 locked product decisions。
10. PRD 完成后，单独产出 PRD 决策文档，并执行 PRD Completeness Gate。

### PRD Normalization

当输入是已有文档时，输出的新 PRD 必须包含 source trace：

```markdown
| Original source | Original statement | Normalized PRD section | Interpretation | Gap/decision |
|---|---|---|---|---|
```

规则：

- 原文中已明确的事实可以进入 PRD，但必须标明来源。
- 原文中的模糊词，如“支持”“优化”“快速”“友好”“类似”“默认”“必要时”，必须转成具体行为或决策点。
- 原文冲突时，不得自行选择；必须列为 open product decision，除非用户授权 AI 按推荐方案决策。
- 原文没有覆盖的标准 PRD 维度不能省略，必须补齐或写入缺失决策。

### External Research Evidence

当需求依赖外部知识时，PRD 或 PRD 决策文档必须包含：

```markdown
| Evidence ID | Source type | URL/path | Fact extracted | Applies to decision/section | Confidence | Notes |
|---|---|---|---|---|---|---|
```

Source type 可包括：

- `feishu-doc`
- `feishu-api-design`
- `terraform-api-design`
- `github-issue`
- `github-pr`
- `official-doc`
- `third-party-doc`
- `codebase`
- `runtime`
- `competitor`
- `user-provided`

调研规则：

- 用户显式给出的飞书/GitHub/外部链接必须读取；链接内容不得只凭标题或记忆推断。
- 用户显式补充的 API/Terraform/部署设计文档必须作为 evidence 进入 PRD，不得只在 AIP 或代码考古阶段才处理。
- 涉及会随时间变化的事实，如 API、云服务限制、版本能力、竞品行为、法规或价格，必须使用当前来源验证。
- 对 OpenAI 等官方产品信息，只能优先使用官方文档来源。
- 外部调研只能作为决策依据，不能替代用户对产品语义的确认，除非用户授权 AI 决策。

### PRD 决策文档

PRD 完成时必须额外生成：

```text
specs/changes/<change-id>/decision-reviews/prd-decisions.md
```

如果当前环境有 `lark-cli` 写权限，必须同步创建飞书文档，并把链接回写到 `proposal.md`、`spec.md` 或 Decision Registry 的 Decision Document Index。

```bash
lark-cli docs +create --title "<需求名> PRD 决策记录" --markdown @specs/changes/<change-id>/decision-reviews/prd-decisions.md --wiki-space "7460028547143417875" --as user
```

PRD 决策文档必须包含：

| Section | Required content |
|---|---|
| 原始需求输入 | 用户最初描述、飞书/issue 链接、明确事实 |
| Source Trace | 原始文档语句到新 PRD 章节的映射 |
| Research Evidence | 外部调研来源、事实、适用决策、可信度 |
| 需求澄清过程 | 用户确认的问题、AI 被授权决策的问题 |
| 决策清单 | 每个 PDEC 单独列出 |
| 推荐和最终决策 | 推荐方案、最终 locked 方案、是否用户确认/AI 授权 |
| 备选和拒绝原因 | 不采用的方案和原因 |
| 产品影响 | 用户行为、scope、状态、错误、权限、兼容性影响 |
| 下游约束 | AIP/设计/契约/验证必须遵守的约束 |
| 验证方式 | 哪些验收场景证明该决策正确 |

如果用户没有确认且没有授权 AI 决策，相关 PDEC 必须保持 `open`，并阻塞进入 AIP/工程设计。

## Local Audit Gate: PRD Source And Semantics Audit

候选 PRD 写出后、锁定 PRD 前，主 agent 必须本地二次审计本阶段产物。本地审计只复核 source、产品语义和当前现状证据，不锁定 PDEC，不替主 agent 写最终 PRD。候选 PRD 不能被 AIP、设计、考古、契约或任务规划消费；只有 PRD Completeness Gate 和本地审计均通过后，才允许标记为 locked。

输入：

- Source Intake Ledger、Propose Extraction、Source Trace。
- External Research Evidence。
- Current Product/Code Understanding。
- PRD 各产品维度、PDEC、PRD 决策文档草稿。

输出写入 PRD 或 `decision-reviews/prd-decisions.md`：

```markdown
### PRD Local Audit Report

| Audit scope | Finding | Severity | Evidence | Required backflow | Blocks PRD lock |
|---|---|---|---|---|---:|
```

必须审计：

- 用户提供的飞书、issue、设计草案、接口草案、历史方案和对话输入是否全部登记、读取、映射。
- Current Product/Code Understanding 是否有具体路径/命令证据和停止条件。
- `参考/复用/沿用/类似` 是否已经转成当前产品行为影响和 PDEC，而不是自然语言继承。
- mode、运行时能力、创建后操作、参数归属、错误、权限、验收是否有明确产品语义。
- Decision Surface Discovery 是否覆盖 mode consumer、capability、frontend action、post-create consumer、persistent mutation、runtime lifecycle 和 mock/playground；是否每个 surface 都有产品决策、后续 owner stage 或 locked N/A。
- AI 自主产品决策是否有用户明确授权；没有授权时是否保持 open。

阻塞条件：

- behavior-affecting source 未读或未映射。
- PRD 当前现状理解缺 evidence path / command。
- PDEC open 但 PRD 标为 locked。
- 新增/修改 mode 缺同级模式差异矩阵。
- 缺 Decision Surface Discovery，或其中 `needs-decision` / `Blocks next stage=yes` 未关闭。
- 运行时能力、创建后操作或自动调节声明支持，但缺 acceptance evidence。
- 外部事实未验证却进入 locked product decision。

任何阻塞项必须回流到本阶段继续补 source、现状理解、用户决策或 PRD 语义；不得进入 AIP、设计、考古或实现。

## 输入

- 用户口头需求、飞书讨论、issue、PRD 草稿、客户/内部反馈。
- 如果已有 AIP，只能用来反查产品语义，不要让技术方案倒灌产品需求。

所有输入进入本阶段时统一称为 Propose / Source。禁止在输入清单中把任何外部文档标为 `final PRD` 或 `accepted PRD`；最多标为 `prd-draft source`。

## 输出位置

如果使用 `automq-workspace`：

- 产品行为进入 `specs/changes/<change-id>/spec.md`。
- 产品背景、scope、non-goals 进入 `proposal.md`。
- 产品决策进入 Decision Registry。

也可以先产出独立需求文档，但必须被 `proposal.md/spec.md` 引用。

## 必填结构

### 0. Source Intake, Propose Extraction, Current Understanding

必须先给出 Propose Extraction：

```markdown
| Source ID | Propose statement | Explicit fact | Inferred fact | Unknown / decision needed | Target PRD dimension |
|---|---|---|---|---|---|
```

如果输入包含已有文档、对话或外部链接，必须给出 Source Trace：

```markdown
| Original source | Original statement | Normalized PRD section | Interpretation | Gap/decision |
|---|---|---|---|---|
```

如果使用了外部调研，必须给出：

```markdown
| Evidence ID | Source type | URL/path | Fact extracted | Applies to decision/section | Confidence | Notes |
|---|---|---|---|---|---|---|
```

必须给出 Current Product/Code Understanding：

```markdown
| Area | Current behavior | Evidence path / command | Product implication | Gap / decision |
|---|---|---|---|---|
```

### 1. 用户与场景

```markdown
| User | Goal | Current pain | Desired outcome |
|---|---|---|---|
```

### 2. 产品对象模型

列出用户感知的对象，不写代码对象。

```markdown
| Object | User-facing meaning | Key properties | Lifecycle/state |
|---|---|---|---|
```

### 3. 功能范围

```markdown
## In Scope
- 

## Non-Goals
- 
```

Non-Goals 必须具体，不能只写“暂不支持高级能力”。

### 4. 用户可见配置

```markdown
| Config | Meaning | Type/range | Default | Required? | Validation | Visible where |
|---|---|---|---|---|---|---|
```

### 4.1 云资源参数归属

如果需求涉及云资源、部署模式、托管资源或“参考现有创建流程”，必须把每个参数的产品归属写清楚，不能直接写成 no-goal。

```markdown
| Resource/parameter | User meaning | Ownership | User operation | Default/derivation source | Missing behavior | Error shown | Decision |
|---|---|---|---|---|---|---|---|
```

`Ownership` 只能使用：

- `user-select`: 用户从候选列表选择已有资源。
- `backend-auto-create`: 后端自动创建并管理。
- `derive-from-existing-resource`: 从已选实例、环境或已有资源继承。
- `fixed-by-env`: 环境级固定配置，用户不可改。
- `not-supported`: 明确不支持，必须写原因。

如果 `Ownership=derive-from-existing-resource`，必须说明源对象缺少字段时产品行为是阻塞创建、要求用户补选，还是后端自动创建。空 payload 是否合法也必须有明确产品决策。

### 4.2 同级模式差异矩阵

当需求新增或修改 `deployment mode`、`runtime mode`、`compute mode`、`storage mode`、`network mode` 等模式时，必须把新模式当作同级产品形态重新建模，不能默认继承已有模式的 UI、事件、状态、日志、资源和验证语义。

必须输出：

```markdown
| Product capability | Existing mode behavior | New mode behavior | Same/Different | User-visible decision | Unsupported/Unavailable behavior | Evidence |
|---|---|---|---|---|---|---|
```

覆盖范围至少包括：

- 创建/更新/删除流程事件
- 表单配置项和默认值
- 规格语义，例如 K8s CPU/Mem 与 EC2 instance type
- 状态和状态文案
- 错误与恢复动作
- 日志、Worker、Endpoint、Metrics、插件加载
- 权限和可见性
- 云资源参数：网络、权限、计算规格、镜像、密钥、模板、资源组、标签等 mode-specific 资源

规则：

- “沿用现有流程/页面/事件”必须逐项证明可沿用；不能概括性继承。
- 只要某能力在新模式下不可用，必须定义 UI 行为：隐藏、禁用、展示 unavailable，或给出替代入口。
- 同名字段在不同模式下语义不同，必须拆成不同产品配置；不得复用一个用户标签掩盖不同含义。
- 如果补充设计文档已定义模式差异或 Terraform/API 形态，必须在本矩阵中引用对应 evidence。

### 4.3 运行时能力与生命周期矩阵

当需求涉及部署模式、云资源、异步任务、控制面创建流程、观测或自动调节能力时，PRD 不能只定义“创建成功”。必须把用户会继续使用的运行时能力逐项锁定。

必须输出：

```markdown
| Capability | User-visible operation | Existing mode behavior | New mode behavior | Supported? | UI behavior if unsupported | Backend/API behavior | Runtime/cloud behavior | Acceptance evidence |
|---|---|---|---|---|---|---|---|---|
```

覆盖范围至少包括：

- 创建、更新部署配置、扩缩容、删除、失败恢复、重试。
- 详情页配置摘要、进度/change tracking、操作按钮。
- 日志、Worker、Endpoint、Metrics、插件加载和健康检查。
- 自动调节能力的触发条件、调整阈值、冷却时间、用户可观察状态、负载触发验收方式。
- 云资源完整生命周期：创建、绑定、漂移、删除、清理失败、残留资源对用户的表达。

规则：

- 没有出现在本矩阵中的运行时能力，不得在后续 UI 中作为可用能力展示。
- 如果新 mode 暂不支持某能力，必须定义隐藏、禁用、unavailable 文案或替代入口，不能让用户点击后才报内部错误。
- 更新和删除不能默认继承创建流程；必须分别定义产品语义、事件文案、失败恢复和验收证据。
- 自动调节能力不能只写“支持”；必须定义用什么运行时信号证明它生效。若验收必须通过 CPU 压力或等价负载触发，PRD 必须写成 acceptance evidence。
- Metrics 不能只定义“页面展示”；必须定义数据来源、缺数据时展示、0 值语义，以及新 mode 是否应与旧 mode 使用同一指标接入机制。

### 5. 用户可见状态

```markdown
| State | Meaning | When entered | User action allowed | Terminal? |
|---|---|---|---|---|
```

### 6. 用户可见错误和降级

```markdown
| Scenario | Product behavior | Error/status shown | Recovery action |
|---|---|---|---|
```

### 7. 权限和可见性

```markdown
| Action/view | Required permission | API behavior if denied | UI behavior if denied |
|---|---|---|---|
```

### 8. 场景与验收

```markdown
### PR-SCN-001: <name>

- Given:
- When:
- Then:
- Acceptance:
```

### 9. 产品决策

所有产品选择必须进入 Decision Registry。

```markdown
| Decision ID | Product decision | Alternatives | Reason | Status |
|---|---|---|---|---|
| PDEC-001 |  |  |  | locked/open |
```

### 10. PRD Completeness Gate

PRD 必须包含自检结果：

```markdown
| Dimension | Complete? | Evidence section | Open decision | Blocks next stage |
|---|---:|---|---|---:|
| Propose extraction | yes/no |  | PDEC-xxx/N/A | yes/no |
| Current product/code understanding | yes/no |  | PDEC-xxx/N/A | yes/no |
| User/scenario | yes/no |  | PDEC-xxx/N/A | yes/no |
| Product object model | yes/no |  | PDEC-xxx/N/A | yes/no |
| Scope/non-goals | yes/no |  | PDEC-xxx/N/A | yes/no |
| Configuration | yes/no |  | PDEC-xxx/N/A | yes/no |
| State | yes/no |  | PDEC-xxx/N/A | yes/no |
| Error/degradation | yes/no |  | PDEC-xxx/N/A | yes/no |
| Permission/visibility | yes/no |  | PDEC-xxx/N/A | yes/no |
| Compatibility | yes/no |  | PDEC-xxx/N/A | yes/no |
| Runtime lifecycle, if applicable | yes/no/N/A |  | PDEC-xxx/N/A | yes/no |
| Acceptance scenarios | yes/no |  | PDEC-xxx/N/A | yes/no |
| Product decisions locked | yes/no |  | PDEC-xxx/N/A | yes/no |
```

任何 `Complete?=no` 且 `Blocks next stage=yes` 的行都阻塞 AIP、设计、考古、契约、验证和任务规划。不能用后续阶段补 PRD 产品语义。

## 退出检查

- [ ] 所有输入都作为 Propose / Source 处理，没有把外部文档或对话直接视为最终 PRD。
- [ ] 对话输入已进入 Source Intake Ledger 和 Propose Extraction。
- [ ] 已完成 Current Product/Code Understanding，覆盖与 propose 相关的当前页面/API/配置/状态/错误/权限/运行时能力。
- [ ] Code Scope Discovery 中每个 required area 有搜索证据和停止条件。
- [ ] 当前代码/产品现状与 propose 的冲突已进入 PDEC 或 open question。
- [ ] 如果输入是已有需求文档，已完成 PRD normalization，并保留 source trace。
- [ ] 如果用户提供了补充设计文档、Terraform/API 设计或飞书链接，已读取并纳入 Source Trace / Research Evidence；未读取的链接没有被当作 locked 决策依据。
- [ ] 如果需求依赖外部事实，已完成必要调研，并把 evidence 写入 PRD 或 PRD 决策文档。
- [ ] 未把未验证外部假设写成 locked decision。
- [ ] 用户、场景、对象模型明确。
- [ ] In Scope / Non-Goals 明确。
- [ ] 配置、状态、错误、权限、验收场景明确。
- [ ] 涉及云资源/部署模式时，云资源参数归属已明确，未把待决策字段误写成 Non-Goal。
- [ ] 涉及新增/修改 mode 时，已完成同级模式差异矩阵，并逐项锁定新模式是否继承、替换或禁用旧模式能力。
- [ ] 涉及部署模式/云资源/观测/自动调节能力时，已完成运行时能力与生命周期矩阵，覆盖创建、更新、删除、失败恢复、指标、日志和自动调节验收证据。
- [ ] 不存在未证明可沿用却默认继承的旧模式 UI、事件、状态、日志、资源或验证语义。
- [ ] 产品决策已由用户确认，或用户明确授权 AI 按推荐方案锁定。
- [ ] 未获得 AI 产品决策授权时，所有待决策点已交互式向用户确认。
- [ ] User Decision Interaction 已写回 PDEC 详情和 Decision Registry；模糊/未响应的 PDEC 保持 open。
- [ ] 产品决策进入 Decision Registry，且 PRD 阶段无 `open` 产品决策。
- [ ] PRD Completeness Gate 中没有 `Blocks next stage=yes` 的 incomplete 维度。
- [ ] 已完成 PRD Local Audit Report；无 `Blocks PRD lock=yes` 项。
- [ ] 已生成 `decision-reviews/prd-decisions.md`，有飞书写权限时已同步飞书并回写链接。
- [ ] 没有会让工程/AIP 阶段替产品做选择的 open question。
- [ ] 已满足 artifact-completeness-spec Stage 1 的 User Scenario、Product Object Model、Config Ownership、State/Error/Permission、Scenario Acceptance、Product Decision artifact 要求。
