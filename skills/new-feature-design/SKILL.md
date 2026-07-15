---
name: new-feature-design
description: 从需求和 AIP 出发设计新功能模块边界和模块语义。Use for new AutoMQ features or ideal-state redesigns before implementation, producing domain entities, module boundaries, alternative approaches, decision matrix, module 21-question semantics, scenarios, and cross-module contract inputs mapped into specs/changes.
---

# New Feature Design

## 定位

用于“全新能力”或“大改动中的新理想设计”。

它不读取旧代码细节来复制结构；旧代码约束由 `code-archaeology-sdd` 提供，之后再通过 `migration-diff-analysis` 对齐。

执行或评审本阶段时，必须按 `ai-dev-methodology/references/artifact-completeness-spec.md` 的 “Stage 4: New Feature Design” 检查正交维度、Required Artifacts、Completeness Criteria 和 Exit Gate。

本阶段产生的模块边界、实体、不变量、流程和方案取舍决策，必须写入 `specs/changes/<change-id>/decision-reviews/design-decisions.md`，使用或等价满足 `ai-dev-methodology/templates/stage-decision-document.md`，并同步进入 Decision Registry。AI 可以做不改变产品语义的工程决策，但必须记录 alternatives、reason、product alignment、impact 和 verification。

本阶段必须维护 `Semantic Consumption Matrix`：消费 PRD/AIP 的 `REQ/SCN/PDEC/ADEC/DEC`，派生子需求、领域过程、不变量、实体、模块边界和设计决策。任何 PRD 语义不能只在 spec 中存在而未进入设计消费矩阵。

如果存在 `mechanism-design-model.md`，本阶段必须把其中所有影响实现的 `MECH/OPSEQ/EXTAPI/EVT/RMM/RLM/FCM/MIM` 行消费到领域过程、不变量、模块边界、contract candidate、verification input、locked N/A 或 blocked backflow。设计阶段不能只消费 AIP 摘要；机制行是比 AIP 叙述更接近实现的设计事实。

## 输入

- 已通过门禁的需求文档。
- 已通过门禁的 AIP。
- `external-capability-research.md`，当本设计依赖外部系统、官方 API、云/K8s/Terraform/IAM/runtime/autoscaling/scheduling/lifecycle 或 mock/playground 外部边界时必需；缺失或有 blocked/unknown fact 时不得进入模块设计。
- `mechanism-design-model.md`，当 AIP/readiness 触发云 API、K8s/HPA、ASG、metrics、IAM、runtime、日志、存储、外部 adapter、资源 lifecycle、progress/change/event 或跨 mode 行为时必需；缺失或只有摘要行时不得进入模块设计。
- `design-context-pack.md` 或 `plan.md#Design Context Rehydration`。如果使用 `automq-ai-dev-workflow-contextpack`，本阶段必须先读取该 context pack；缺失或仅包含 ID/摘要时阻塞本阶段，回流补 PRD/AIP/source/decision。
- Decision Registry，且无阻塞本阶段的 open product/architecture decision。
- 目标 `specs/changes/<change-id>/`。
- 如有：已通过 PRD gate 的 `proposal.md` / `spec.md`，不得消费候选草稿。
- `Semantic Consumption Matrix`，如已存在则更新；不存在则按模板创建。

Context pack 必须至少覆盖：Source Rehydration Ledger、Semantic Index、Decision And Constraint Pack、PRD/AIP scope/non-goals、Current Product/Code Understanding、External Capability Research facts/constraints（如适用）、工程约束和 Downstream Coverage Map。任何 `REQ/SCN/PDEC/ADEC/DEC` 或影响设计的外部 `Fact ID` / `Constraint ID` 只存在于聊天、压缩摘要或 AIP 调研段中时，不得进入模块设计。

## 流程

### Step 1: 子需求分解

先建立或更新：

```markdown
### Semantic Consumption Matrix - New Feature Design

| Upstream object | Required by design? | How consumed | Derived object | Copied semantics | Dropped semantics | Drop reason / decision | Verification / gate | Status |
|---|---:|---|---|---|---|---|---|---|
```

要求：

- 每个 `REQ/SCN/PDEC/ADEC/DEC` 必须出现；当存在 `external-capability-research.md` 时，每个影响设计的 `Fact ID` / `Constraint ID` 也必须出现。
- 当存在 `mechanism-design-model.md` 时，每个影响实现的 `MECH/OPSEQ/EXTAPI/EVT/RMM/RLM/FCM/MIM` 行必须出现。
- `Derived object` 可以是子需求、Process、Invariant、Entity、Module、DESIGN-DEC。
- `Dropped semantics` 必须为空，除非引用 locked decision 或 N/A 原因。
- 如果某个 surface / DEC / ADEC 的 owner stage 是 `design` 或本阶段承接了上游 `routed-to-design`，本阶段结束前必须关闭为 locked design decision、module/process/invariant、contract candidate、locked N/A 或 blocked backflow；不得在 design `passed` 后继续留下 `routed-to-*` / `stage-owned`。
- `Status=blocked` 阻塞模块设计。

将需求拆成可验证子需求：

```markdown
| ID | 子需求 | 用户可见验收条件 | 来源 |
|---|---|---|---|
| R1 |  | 当...时，系统... | Requirement/AIP |
```

每个子需求必须能映射到后续 `spec.md` 的 REQ / SCN / SC。

### Step 2: 领域过程与不变量

先描述业务过程，而不是直接跳到模块：

```markdown
| Process | Start condition | End condition | Participants | Observable result |
|---|---|---|---|---|
```

如果流程来自机制模型，必须额外输出 operation sequence 对齐：

```markdown
### Mechanism Operation Sequence Consumption

| Mechanism row | Operation sequence row | Domain process / scenario | Module participants | State/resource/event produced | Failure branch consumed | Contract candidate | Verification candidate | Status |
|---|---|---|---|---|---|---|---|---|
```

规则：

- 每个 `OPSEQ-*` 必须映射到领域过程或场景；不能只留在 AIP/readiness。
- 如果 sequence 中有外部调用、状态写入、事件、readback 或 failure branch，本阶段必须把它分配到 module participant 和 contract candidate。
- `Status=blocked/open/TBD` 阻塞模块边界设计。

列出不能被实现细节破坏的不变量：

```markdown
| Invariant ID | Statement | Applies to | Violation behavior | Source |
|---|---|---|---|---|
| INV-001 |  |  |  | Requirement/AIP |
```

跨实体不变量通常是 `N2` 候选，必须输入 `cross-module-contract-sdd`。

### Step 3: 领域实体识别

列出实体、状态、数据所有权候选：

```markdown
| 实体 | 状态/生命周期 | 拥有的数据/资源 | 可能写入方 | 可能读取方 | 备注 |
|---|---|---|---|---|---|
```

### Step 4: 模块边界设计

按三个性质和三个信号设计模块：

**模块性质**
1. 内部错误不传播到外部。
2. 内部上下文可自包含。
3. 跨模块交互可枚举。

**判定信号**
1. 数据所有权：先问 writer 归谁，reader 只能通过接口消费。
2. 状态机自洽性：逐个状态转换检查 guard/precondition 是否只依赖自身数据。
3. 变更独立性：新功能没有 git history 时，用“未来独立修改哪些行为”替代。

必须先输出三张设计证据表：

```markdown
### Data Ownership Design

| Data/resource | Writer module candidate | Reader module(s) | Mutation rule | Source / reason |
|---|---|---|---|---|

### State-Machine Boundary Design

| Entity/resource | State transition | Guard / precondition | External dependency? | Internal module candidate | Contract candidate if external |
|---|---|---|---|---|---|

### Future Change Independence Design

| Behavior/file group candidate | Likely future independent change | Shared data/state? | Shared state machine? | Module candidate | Risk |
|---|---|---|---|---|---|
```

如果存在机制模型，必须额外输出：

```markdown
### Mechanism Design Consumption Matrix

| Mechanism row | Consumed design model row | Required by design? | Consumed as | Owner module candidate | Contract candidate | Verification candidate | Dropped / N/A reason | Status |
|---|---|---:|---|---|---|---|---|---|
```

要求：

- `Consumed design model row` 必须覆盖影响实现的 `MECH-*`、`OPSEQ-*`、`EXTAPI-*`、`EVT-*`、`RMM-*`、`RLM-*`、`FCM-*`、`MIM-*`。
- `Consumed as` 可以是 process、invariant、entity state、module owned resource、provided contract candidate、consumed contract candidate、verification input、locked N/A。
- 不能把 `MECH-*` 统一写成“交给 contract/task-planning”；必须指明 owner module candidate 和具体 contract/verification candidate。
- 如果某机制行需要选择 provider API、runtime carrier、event fields、cleanup/protect 或 failure consistency，本阶段必须回流 AIP/readiness，不得在 design 自行猜。

如果子需求包含 auto-create、default-created、generated resource、managed resource、select-existing 或 existing external resource，必须额外输出：

```markdown
### Managed Resource Ownership Design

| Resource | Selection mode | Create timing | Owner module | Provider writer contract | Resource identity rule | Provenance state owner | Runtime consumer | Update rule | Delete cleanup/protect rule | Failure/idempotency rule | Verification candidate |
|---|---|---|---|---|---|---|---|---|---|---|---|
```

规则：

- 这张表回答资源生命周期，不回答 UI 如何选择候选；不能被 selector 字段表替代。
- `Owner module` 必须是生产代码中负责维护资源 ownership 的模块。
- `Provider writer contract` 必须描述真实 provider/API/operator/resource writer，而不是 mock/no-cloud adapter。
- `Delete cleanup/protect rule` 必须区分 owned resource cleanup 与 existing resource protect。
- 如果自动创建不是本需求职责，必须写 locked N/A 和谁负责；不能留给 Atomic Issue worker 判断。

输出：

```markdown
| 模块 | 职责 | Owned data/resources | Writer evidence | 包含的类/资源候选 | 对外接口 | 外部交互点数量 | 边界依据 | 外部依赖 |
|---|---|---|---|---|---|---:|---|---|
```

同时标记收敛影响：

```markdown
| Interaction | From | To | N type | Why |
|---|---|---|---|---|
|  |  |  | N1 internal / N2 contract candidate |  |
```

### Step 4.1: N2 交互语义类型标注

每条 `N2 contract candidate` 不能只写“模块 A 调模块 B”。必须先标注这条边承载的主语义类型，再交给 `cross-module-contract-sdd`。同一条边可有多个类型，但必须选出 primary type。

```markdown
### Interaction Semantic Type Matrix

| Interaction | From -> To | Primary semantic type | Secondary types | Data/state/resource carried | Canonical owner candidate | Decisions still forced before task planning | Verification candidate |
|---|---|---|---|---|---|---|---|
```

类型至少从下面选择：

| Semantic type | 触发信号 | 设计阶段必须交给契约阶段的问题 |
|---|---|---|
| Wire/API shape | HTTP/API client/DTO/VO/query/body/schema、payload、兼容字段 | method/path/query/body、canonical 字段路径、allowed/forbidden fields、legacy mapping、重复语义路径冲突 |
| State machine | lifecycle、task、progress、terminal、retry、polling | from/to state、trigger、guard、terminal、failure reason、retry/idempotency |
| Error/warning | field error、warning、unreachable、unknown、permission、validation | block vs allow、error code、field location、warning persistence/readback、用户恢复路径 |
| Resource ownership | auto-create、default-created、generated、select-existing、external resource | writer、identity、owned/existing provenance、cleanup/protect、idempotency、failure |
| External side effect | cloud/K8s/provider/Connect REST/runtime adapter mutation | real adapter/API/resource call、desired/actual result、allowed mock boundary、drift guard |
| Readback/observability | detail/list/progress/event/log/metric/dashboard | producer、readback field/event/log/metric shape、empty/error/unavailable semantics |
| UI action closure | button/menu/route/form/tab/wizard/action | reachable state、enabled rule、API side effect、feedback、next visible state、no-network cases |
| Permission | permission domain、guard、denied behavior | frontend disabled/hidden、backend guard location、no mutation/no network proof |
| Compatibility/migration | old payload/schema/data/read path | old->new mapping、mode-scoped nullability/defaults、retired/forbidden fields、readback |
| Acceptance/mock | playground/no-cloud/mock/fixture/packaged runtime | production path that remains real、mocked boundary only、fixture graph、drift proof |

阻塞条件：

- 任一 N2 interaction 没有 semantic type。
- `Wire/API shape` 边没有 canonical owner candidate，或没有列出需要契约阶段锁定的 field/path 决策。
- `External side effect` / `Resource ownership` 边没有真实 provider/resource writer candidate。
- `UI action closure` 边没有真实 route/API/action source candidate。

这些阻塞必须进入 `Design Local Audit Report`，不得用“后续契约细化”跳过；契约阶段只能锁定这些问题，不能重新发现它们是否存在。

### Step 4.5: 模块边界验证

模块边界设计后必须验证，不得只输出模块表。输出：

```markdown
### Module Boundary Validation

| Module | Owned state/data/resource evidence | State-machine self-contained? | External deps enumerable as contracts? | Provided contracts enumerable? | Too large risk | Too small risk | Decision |
|---|---|---|---|---|---|---|---|
```

要求：

- `Too large risk` 必须检查是否混入多个独立状态机、上下文不可自包含、核心文件/资源超过约 10 个、对外接口超过约 15 个。
- `Too small risk` 必须检查是否只有 1-2 个核心类/资源、契约过密、交互点超过 5 个、接口只被一个调用方使用、无法独立产生 contract-closed issue。
- 合适模块通常应满足 3-8 个核心类/资源、对外接口 3-10 个、交互点 1-3 个、状态机自洽或只有 1-2 个外部前置条件；偏离时必须解释。
- `Decision` 只能是 `keep`、`split`、`merge`、`needs-contract-review`。
- 任何 `needs-contract-review` 都阻塞 `atomic-task-planning`。
- split/merge/keep 是设计决策，必须进入 `decision-reviews/design-decisions.md`。

### Local Audit Gate: Design Boundary And Scenario Audit

Module Boundary Validation 和候选场景写出后，主 agent 必须本地二次审计设计证据。本地审计不决定 split/merge/keep，只判断证据是否足以支撑后续 contract-closed issue。候选场景在本地审计通过前不能进入 contract 或 task planning。

输入：

- Semantic Consumption Matrix - New Feature Design。
- 子需求、领域过程、不变量、实体。
- Data Ownership Design / State-Machine Boundary Design / Future Change Independence Design。
- Module Boundary Validation。
- 场景和 Convergence Budget 候选内容。

输出：

```markdown
### Design Local Audit Report

| Audit scope | Finding | Evidence | Risk type | Required backflow | Blocks contract/task planning |
|---|---|---|---|---|---:|
```

必须审计：

- 每个 REQ/SCN/PDEC/ADEC/DEC 是否被消费成子需求、过程、不变量、实体或模块边界。
- 每个外部 Fact/Constraint 是否被消费成设计规则、模块边界、外部依赖 contract candidate、mock/playground rule 或 locked N/A。
- 每个 `MECH/OPSEQ/EXTAPI/EVT/RMM/RLM/FCM/MIM` 是否被消费成 process、invariant、module owner、contract candidate、verification input、locked N/A 或 blocked backflow。
- 模块是否有 owned state/data/resource、状态机自洽和可枚举 external deps。
- split/merge/keep 是否有 alternatives、reason、verification，而不是目录直觉。
- 每个用户场景是否能映射到模块交互和 N2 contract candidate。
- Convergence Budget 是否把 N1/N2 区分清楚，未把跨模块约束留给执行阶段。

阻塞条件：

- Module Boundary Validation 缺 ownership/state/dependency evidence。
- 任何模块 `Decision=needs-contract-review` 未处理。
- 子需求或场景无法映射到模块提供契约。
- N2 candidate 未输出给 cross-module-contract-sdd。
- 机制模型行未消费，或仍需要在 task-planning/implementation 阶段决定 provider API、runtime 物化方式、event fields、resource lifecycle、failure consistency。
- 设计决策未进入 Decision Registry / design decision doc。

### Step 5: 备选方案与决策

至少列出两个关键方案，除非 AIP 已锁定且说明不再比较。

```markdown
| 方案 | 核心思路 | 优点 | 缺点 | 决策 |
|---|---|---|---|---|
```

决策原则至少覆盖：

- 正确性
- 简单性
- 可测试性
- 可维护性
- 可扩展性
- AutoMQ 特定约束：BYOC/Software/Open Source、部署、权限、观测、兼容性

### Step 6: 验证场景

每个子需求至少有一个场景：

```markdown
### SCN-001: <名称>

- Covers: R1, R2
- Given:
- When:
- Then:
- Module interaction:
```

### Step 7: 模块语义 21 问

每个核心模块必须回答：

| 区域 | 问题 |
|---|---|
| 身份 | Q1 核心职责；Q2 明确不做什么 |
| 输入 | Q3 输入和约束；Q4 调用方和场景；Q5 非法输入响应 |
| 输出 | Q6 输出和保证；Q7 消费方；Q8 失败类型 |
| 行为 | Q9 转换规则；Q10 条件分支；Q11 状态变迁 |
| 约束 | Q12 性能；Q13 并发/幂等；Q14 顺序；Q15 一致性 |
| 依赖 | Q16 依赖模块；Q17 每个依赖不可用时怎么办 |
| 边界 | Q18 空输入；Q19 极值；Q20 部分失败；Q21 超时 |

### Step 8: Convergence Budget

输出预期收敛边界：

```markdown
| Item | Count / list | How controlled |
|---|---|---|
| N1 module-internal tasks |  | boundaries/patterns/verification |
| N2 contract candidates |  | cross-module-contract-sdd |
| Locked decisions |  | decision-registry |
| Remaining open decisions | must be empty before tasks |  |
```

目标是让实现阶段的错误不来自 N1。

### Step 9: 产物映射

将结果写入：

- `spec.md`: REQ、SCN、成功标准、用户可见行为。
- `plan.md`: 模块边界、方案取舍、模块语义摘要、验证策略。

不要只生成 `docs/design`。

## 退出检查

- [ ] 每个子需求有验收条件。
- [ ] Semantic Consumption Matrix 覆盖所有输入 REQ/SCN/PDEC/ADEC/DEC，无 blocked 或无理由 dropped 行。
- [ ] 领域过程和不变量已列出。
- [ ] 模块边界按数据所有权/状态机/独立性推导。
- [ ] 已完成 Module Boundary Validation，证明模块不明显过大/过小，且能生成 contract-closed issue。
- [ ] 每个跨模块交互都能作为 `cross-module-contract-sdd` 输入。
- [ ] 每个核心模块有 21 问语义。
- [ ] 每个设计决策进入 Decision Registry。
- [ ] 已生成或更新 `decision-reviews/design-decisions.md`，有飞书写权限时已同步飞书并回写链接。
- [ ] Convergence Budget 区分 N1 和 N2。
- [ ] 已完成 Design Local Audit Report；无 `Blocks contract/task planning=yes` 项。
- [ ] 结果已映射到 `specs/changes`。
- [ ] 已满足 artifact-completeness-spec Stage 4 的 Sub-Requirement、Domain Process、Invariant、Domain Entity、Module Boundary、Alternative Decision、Scenario Walkthrough、21Q、Convergence Budget artifact 要求。
