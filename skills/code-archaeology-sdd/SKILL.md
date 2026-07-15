---
name: code-archaeology-sdd
description: SDD 对齐版代码考古。Use before major existing-code changes to discover old system facts, module boundaries, hidden constraints, patterns, framework semantics, and cross-module contract candidates, then write or link results into specs/changes plan.md instead of leaving them only in steering docs.
---

# Code Archaeology SDD

## 定位

这是 `code-archaeology` 的 SDD 对齐版。

职责只限于回答：**旧系统事实是什么**。不做新方案决策，不替代 AIP，不直接拆实现任务。

核心目标：

1. 正确圈定模块边界。
2. 把旧代码隐式知识外化。
3. 给 `migration-diff-analysis` 和 `cross-module-contract-sdd` 提供输入。
4. 将结果写入或明确链接到 `specs/changes/<change-id>/plan.md`。

执行或评审本阶段时，必须按 `ai-dev-methodology/references/artifact-completeness-spec.md` 的 “Stage 3: Code Archaeology” 检查正交维度、Required Artifacts、Completeness Criteria 和 Exit Gate。

本阶段产生的 pattern、框架语义、隐式约束处理或参考实现取舍，必须写入 `specs/changes/<change-id>/decision-reviews/archaeology-decisions.md`，使用或等价满足 `ai-dev-methodology/templates/stage-decision-document.md`，并同步进入 Decision Registry。若考古发现会改变产品语义，必须升级回 PRD 决策流程。

本阶段必须维护 `Semantic Consumption Matrix`：消费 PRD/AIP/design 中与旧系统相关的 `REQ/SCN/PDEC/DEC/DESIGN-DEC`，派生旧系统事实、隐式约束、模块边界证据、pattern、framework semantics 和 contract candidates。不得让某个 PRD 语义绕过考古直接进入实现。

## 输入

- 需求文档和 AIP。
- `design-context-pack.md` 或 `plan.md#Design Context Rehydration`，如果使用 contextpack workflow。缺失时不得开始考古；必须先回流补 Source Intake、PRD/AIP 决策、当前产品/代码理解和工程约束。
- Decision Registry，如果已有。
- `specs/changes/<change-id>/proposal.md`，如果已有。
- `decision-surface-discovery.md`，如果已有或需求触发新/改 mode、创建后能力、前端 action、runtime capability、persistent mutation、managed resource ownership、mock/playground。
- 目标仓库和代码范围。
- 旧代码相关文档、测试、历史提交。
- `Semantic Consumption Matrix`，如已存在则更新；不存在则按模板创建。

若存在 Repo Isolation Gate，本阶段只能读取隔离 worktree 内的目标仓库代码和已登记 allowed sources。不得从本地其他分支、其他 worktree 或未授权 patch 中提取旧系统事实、pattern、字段矩阵或实现参考；发现污染必须回流并重写受影响 artifact。

## 输出位置

优先写入：

```text
specs/changes/<change-id>/plan.md
```

建议章节：

```markdown
## Code Archaeology
## Module Boundary
## Hidden Constraints
## Patterns and Framework Semantics
## Cross-Module Contract Candidates
```

如内容过长，可以放辅助文件，但 `plan.md` 必须引用它。不得只写 `.kiro/steering`。

## Phase 0: 模块边界判定

开始考古前必须建立或更新：

```markdown
### Semantic Consumption Matrix - Code Archaeology

| Upstream object | Required by archaeology? | How consumed | Derived object | Copied semantics | Dropped semantics | Drop reason / decision | Verification / gate | Status |
|---|---:|---|---|---|---|---|---|---|
```

要求：

- 每个影响旧系统行为的 `REQ/SCN/PDEC/DEC` 都必须映射到代码搜索、现状事实、隐式约束、模块边界证据或明确 N/A。
- `decision-surface-discovery.md` 中的每个 surface 必须映射到代码搜索、当前消费者、旧 mode assumption、contract candidate、migration input、frontend trace 或明确 N/A。
- 如果某个 surface / DEC / ADEC 的 owner stage 是 `archaeology`，本阶段结束前必须把 `routed-to-archaeology` / `stage-owned` 关闭为旧系统事实、locked archaeology decision、contract candidate、locked N/A 或 blocked backflow；不得在 archaeology `passed` 后继续留下“由考古发现/后续发现”的状态。
- 用户要求“参考/复用/沿用/改造/类似”的语义必须消费到 Reference Implementation Field Matrix 或 Mode Semantic Inheritance Audit。
- auto-create/default-created/generated/select-existing external resource 语义必须消费到 Managed Resource Ownership Archaeology；不能只进入 selector 字段矩阵。
- `Status=blocked` 或 `Dropped semantics` 无 locked reason 时，阻塞契约锁定和任务规划。

模块边界决定 `N1/N2`，未完成 Phase 0 不得进入依赖图。

### 模块必须满足

1. 内部错误不传播到外部。
2. 内部上下文可自包含。
3. 跨模块交互可枚举。

### 三个判定信号

| 信号 | 操作 | 输出 |
|---|---|---|
| 数据所有权 | 列出 DB 表、配置、缓存、内部 topic、云资源、前端状态等存储/资源，找到 writer 和 reader | data/resource -> writer -> owning module |
| 状态机自洽性 | 画出实体/资源生命周期，逐个状态转换标记 guard/precondition 是否依赖外部模块 | 外部前置条件 -> contract candidate |
| 变更独立性 | 用最近约 50 个相关 commit 统计文件共改；新模块用“未来独立修改假设”替代 | 文件组 -> module candidate |

必须输出三张证据表。不得只凭目录、类名或自然语言经验划模块。

```markdown
### Data Ownership Evidence

| Data/resource | Writer(s) | Reader(s) | Mutation rule | Owning module candidate | Evidence |
|---|---|---|---|---|---|

### State-Machine Boundary Evidence

| Entity/resource | State transition | Guard / precondition | Uses external module/data? | Internal module candidate | Contract candidate if external | Evidence |
|---|---|---|---|---|---|---|

### Change Independence Evidence

| File group | Evidence source | Co-change count / future-change reason | Shared data/state? | Shared state machine? | Module candidate | Risk |
|---|---|---|---|---|---|---|
```

旧代码优先用 git history evidence，例如 `git log --name-only` 的最近约 50 个相关 commit；如果历史样本不足，必须写明替代证据和风险。

### 模块类型

模块不限于 Java 类。必须按所有权和状态划分：

- backend domain/service/manager
- DB/schema/migration
- OpenAPI/VO/permission
- async task / pipeline
- Terraform provider/resource
- Helm/K8s/deployment
- cloud resource/IAM/provider-managed compute group
- frontend API client/page/i18n
- observability metrics/events/logs/alerts

### 粒度校验

| 风险 | 信号 | 动作 |
|---|---|---|
| 太大 | >10 个核心类/资源、多个独立状态机、对外接口 >15、上下文装不下 | 拆分 |
| 太小 | 1-2 个核心类/资源且总和另一模块共改、交互点 >5、接口只被一个调用方使用 | 合并或引入稳定接口 |
| 刚好 | 3-8 个核心类/资源、对外接口 3-10、交互点 1-3、状态机自洽或只有 1-2 个外部前置条件 | 保留 |

### Phase 0 输出

```markdown
### Module Boundary

| Module | Type | Responsibility | Owned data/resources | Writer evidence | Included files/resources | Public interfaces | External interaction count | Boundary evidence |
|---|---|---|---|---|---|---|---:|---|

### N1/N2 Impact

| Item | Classification | Reason |
|---|---|---|
|  | N1 internal / N2 contract candidate |  |
```

### Phase 0.5: 模块边界验证

考古阶段必须验证旧系统模块边界是否真实存在，而不是只按目录或类名分组。

输出：

```markdown
### Module Boundary Validation

| Module | Ownership evidence | State-machine evidence | Change-independence evidence | Interface count | External interaction count | External deps enumerable? | Provided contracts enumerable? | Too large risk | Too small risk | Decision |
|---|---|---|---|---:|---:|---|---|---|---|---|
```

要求：

- `Ownership evidence` 指向具体 DB 表、配置、缓存、topic、云资源、前端状态或写入方。
- `State-machine evidence` 指向状态字段、任务流、事件、生命周期代码或测试。
- `Change-independence evidence` 可来自 git history、测试边界、未来独立演进判断。
- `Interface count` 和 `External interaction count` 必须按粒度校验阈值解释。
- `Decision` 只能是 `keep`、`split`、`merge`、`needs-design-review`。
- `needs-design-review` 阻塞后续契约锁定和任务规划。
- 任何 split/merge/keep 都是 pattern/architecture 决策，必须进入 `decision-reviews/archaeology-decisions.md` 或 design decision。

### Local Audit Gate: Module Boundary Evidence Audit

Phase 0.5 完成后，主 agent 必须本地二次复核模块边界证据。本地审计不决定 split/merge/keep，只审计证据是否足够。

输出：

```markdown
### Module Boundary Local Audit Report

| Module | Missing evidence | Over/under-split risk | Contract enumerability risk | Backflow target | Blocks next stage |
|---|---|---|---|---|---:|
```

阻塞条件：

- 任一模块缺 ownership、state-machine 或 change-independence evidence。
- `Decision=needs-design-review` 未处理。
- 外部依赖或 provided contract 不可枚举。
- 模块过大/过小风险没有 split/merge/keep 决策和验证方式。

### Phase 0.6: Stateful Behavior Discovery Gate

当需求或旧代码出现 lifecycle、progress、event、status、terminal、polling、retry、task step、change tracking、mock state graph、用户可见状态推进之一，本阶段必须把“旧系统存在状态机/事件机制”外化成 `Stateful Behavior Inventory`，不能只写“已有 progress/change/event 机制”。

输出：

```markdown
### Stateful Behavior Inventory

| Behavior ID | Source signal | Existing producer | Existing state owner | Existing consumers | Event/status fields | Terminal behavior | Mock/frontend consumers | Evidence |
|---|---|---|---|---|---|---|---|---|
```

必须沿 producer -> persisted/event state -> API/VO -> frontend/mock consumer 追踪：

- 事件或状态是谁生产的：service、task、runtime adapter、controller、scheduler、mock handler。
- 状态或事件存在哪里：DB、entity、change table、in-memory fixture、runtime API、external provider。
- 消费方有哪些：progress page、detail tab、event list、mock fixture、metrics/logs、acceptance case。
- 当前有哪些 operation、event name、status、reason、terminal state、polling stop、retry/idempotency。
- 新需求会新增、替换、禁用哪些旧状态或事件。

如果发现状态机类语义，本阶段必须把输入交给后续 `cross-module-contract-sdd` 的 `stateful-behavior-matrix`。若无法列出现有 producer/consumer/terminal evidence，Stage 3 失败并回流；不得让实现阶段自行命名事件、决定 terminal 行为或选择 mock fixture 覆盖。

### Phase 0.7: Existing Object-Action-Consumer Graph

当需求改变已有对象的 create/update/delete/resize/save/scale/import/bind 等 mutation，或新增/修改 runtime/provider/deployment/compute/storage/network 变体时，本阶段必须先从代码生成 `existing-object-action-consumer-graph.md`。这一步不依赖需求里是否出现 `mode`、`variant`、`deployment mode` 等词，而是看代码结构：同一个对象、同一个入口/action、同一批 readback/post-create consumer 是否被新实现形态继续消费。

必须从旧代码抽出：

- 对象/entity、mutation/action、入口 API/page/controller。
- 已有变体或 discriminator，例如 compute/runtime/provider/deployment/capacity/backend/placement。
- 生产链：service/task/event/provider/repository writer。
- 状态 owner：DB/resource/change/task/event store/cache/external runtime。
- readback API/VO：detail/list/status/progress/change/last-change。
- consumer surface：frontend page/tab/action、mock fixture、acceptance case、downstream service。
- hidden old-variant assumption。

使用模板：`ai-dev-methodology/templates/existing-object-action-consumer-graph.md`。

缺失该图时，不得生成 Mode Semantic Inheritance Audit、cross-module contract 或 Atomic Issue；否则 AI 会把“旧 consumer 仍存在”压缩成一句 mode-aware 文案。

### Phase 0.8: Runtime Test Topology

当行为 proof 需要跨 Maven/Gradle module、runtime task、provider adapter、packaged playground、浏览器 bundle、本地 SNAPSHOT 或代表性 no-cloud fixture 时，本阶段必须生成 `runtime-test-topology-matrix.md`。这不是验证阶段的执行日志，而是代码考古事实：哪个生产路径只能由哪个测试模块/文件证明，以及运行该 proof 前需要什么 build/install/freshness step。

必须锁定：

- production path 与 proof module/package。
- proof file/path 和 fixture/support file。
- 为什么 service-only/unit-only/build-only proof 不够。
- 是否需要 `install`、package、bundle、image build 或其它 freshness step。
- 跳过 freshness step 时的 staleness risk。
- proof file 是否必须进入 owner Txxx 的 packet `files_to_change` 和 `task-dag.yaml` files allowlist。

使用模板：`ai-dev-methodology/templates/runtime-test-topology-matrix.md`。缺失该矩阵时，后续任务规划不得在执行期临时把 proof 文件加入 allowlist。

## Phase 1: 模块依赖图

输出：

```markdown
### Module Dependency Graph

| Caller | Callee | Interface / resource | Scenario | Evidence |
|---|---|---|---|---|

### Data Flow

| Data/state | Producer | Consumer | Path | Evidence |
|---|---|---|---|---|
```

验证：

- 对核心接口做 find usages / rg 反向验证。
- 对云资源、Terraform、前端调用、API path 做 schema/path 搜索。
- 若无法全量验证，记录抽样范围和风险。

## Phase 1.5: 参考实现字段矩阵

当需求出现“参考现有 X 实现 / 与 X 类似 / 复用 X 模式 / 从 X 推导配置”时，本阶段强制执行。不能只读 service 代码，必须沿 UI -> API param/VO -> backend service/manager -> async task/cloud SDK -> DB/entity/current data 全链路追踪。

本阶段的产物是硬门禁，不是辅助说明。只写“复用某页面 / 复用 provider API / 参考某组件”不算完成；必须把参考实现逐字段拆成可验证事实。若不能完成字段矩阵，必须停止并把缺口写入 `plan.md` 的 blocker，不得进入 contract locking、task planning 或 implementation。

输出：

```markdown
### Reference Implementation Field Matrix

| Field/resource | Reference behavior | User selectable? | API path/params | Param source | Null/empty behavior | Disabled/visibility condition | Backend fallback/default | Backend auto-create? | Derived/fixed source | Hidden by product? | Runtime/current data sample | New feature decision | Evidence |
|---|---|---:|---|---|---|---|---|---:|---|---:|---|---|---|
```

证据要求：

- `Evidence` 必须指向具体文件、接口、页面、测试、历史提交或运行时样本。
- `API path/params` 必须写出前端实际调用的路径和关键 query/body 字段；不能只写“provider API”。
- `Param source` 必须写清每个参数来自表单字段、选中对象、全局 metadata/profile context、环境默认值、后端推导，还是固定常量。
- `Null/empty behavior` 必须写清空字符串、null、undefined、空数组在前端和后端分别表示什么。
- `Disabled/visibility condition` 必须写清 UI 控件禁用/隐藏/loading/empty 的条件，并标明这些条件是否来自参考实现。
- `Backend fallback/default` 必须写清后端在参数缺失时是否 fallback 到默认环境、默认 profile、DB 字段、metadata 或报错。
- `Runtime/current data sample` 必须包含至少一个真实或本地可复现样本：API 响应片段、DB 非敏感字段、fixture、mock 数据或运行时日志。若不能访问运行时，必须写明替代样本和风险。
- 对云资源字段，至少覆盖网络、权限、镜像/版本、磁盘、密钥、模板、标签、可观测性接入。
- 如果参考实现存在“UI 选择 + 后端自动创建 + 隐藏默认值”的混合模式，必须逐字段写清，不能概括成“后端推导”。
- 如果新功能选择不沿用参考实现，必须进入 Decision Registry。

资源选择类 UI 的额外强制项：

- 对 VPC、Subnet、Security Group、IAM Role、Instance Type、K8s Cluster、Node Group、Bucket、DNS Zone、Image、AMI、KeyPair 等 selector，矩阵必须覆盖 `API path/params`、`Param source`、`Null/empty behavior`、`Disabled/visibility condition`、`Backend fallback/default`、`Runtime/current data sample` 六列。
- 若参考实现的后端允许参数为空并 fallback，前端不得在新实现中仅因该参数为空禁用控件，除非 Decision Registry 明确记录产品/架构决策。
- 若同一个 UI 状态由多个条件决定，例如“模式可选”和“字段可编辑”，必须分别列行；不得把它们合并成一个“eligible”结论。
- 若使用某个实体对象字段驱动 provider/resource API，例如 `selectedInstance.deployProfile`，必须证明该字段在真实列表/详情 API 和当前数据中稳定存在；否则必须记录为 contract candidate 或禁止作为实现前提。

失败条件：

- 缺少 Reference Implementation Field Matrix，但后续文档出现“复用参考实现”“沿用现有模式”“后端推导”“前端隐藏字段”之一，Stage 3 失败。
- 字段矩阵只有参考文件路径，没有逐字段 `API path/params` 和 `Disabled/visibility condition`，Stage 3 失败。
- 涉及资源 selector 但没有 `Runtime/current data sample`，Stage 3 失败。
- `Null/empty behavior` 或 `Backend fallback/default` 为空，却把该字段用于前端禁用条件、必填校验、后端 validation 或 atomic task，Stage 3 失败。

退出规则：参考实现字段矩阵缺失或任一强制列为空时，不得把“前端隐藏字段、后端推导配置、默认 profile、默认环境、资源 selector 行为”作为 locked contract 或实现任务。

### Local Audit Gate: Reference Field Trace Audit

Phase 1.5 完成后，主 agent 必须本地二次 沿 UI -> API -> backend -> task/cloud/runtime -> DB/current sample 抽查参考字段闭环。

输出：

```markdown
### Reference Field Local Audit Report

| Field/resource | Trace finding | Missing column/sample | Contract candidate | Required backflow | Blocks next stage |
|---|---|---|---|---|---:|
```

阻塞条件：

- 文档出现“参考/复用/沿用/后端推导/前端隐藏字段”，但 Reference Implementation Field Matrix 缺失。
- 资源 selector 缺 `API path/params`、`Param source`、`Null/empty behavior`、`Disabled/visibility condition`、`Backend fallback/default` 或 `Runtime/current data sample`。
- 字段用于隐藏、必填、推导或校验，但 source/null/fallback 不明。

### Persistent Mutation / Schema Compatibility Audit

当需求新增 mode、资源类型、生命周期，或改变 create/update/delete/resize/save/scale/import/bind 等持久化 mutation 时，本阶段必须审计旧 schema、DO、mapper、VO/API 和 writer/readback 链路。目标是发现“旧模式下必然存在”的字段或资源，在新模式下是否变成可空、派生、默认、兼容占位或禁止写入；不能只写“持久模型需要支持新字段”。

输出：

```markdown
### Persistent Mutation / Schema Compatibility Audit

| Mutation | Mode/variant | Authoritative state owner | Writer path | Schema/mapper/API/VO path | Existing required field/resource | Old assumption | Valid for new mode? | New null/default/derived/forbidden rule | Readback consumers | Contract candidate | Verification |
|---|---|---|---|---|---|---|---|---|---|---|---|
```

必须覆盖：

- 真实 mutation 入口：HTTP/controller/service/manager/task/repository/resource writer。
- 真实 state owner：DB table/repository、K8s/cloud resource、runtime graph、task/change/event store、cache/topic 等。
- 旧 schema/mapper/DO/VO/API 中的 NOT NULL、required、默认值、枚举、旧 mode 专属字段和旧资源名。
- 新 mode 下旧字段/旧资源的策略：`nullable`、`derived`、`defaulted`、`compat-placeholder`、`forbidden`、`retired` 或 `needs-decision`。
- readback consumer：detail、list、progress、event、worker、metrics/logs、mock fixture、frontend surface。

判定规则：

- `Valid for new mode?=unknown` 或 `needs-decision` 阻塞后续契约。
- 只发现新增字段不够；必须证明旧 required constraint 是否仍成立。
- “persisted / saved / canonical state” 不是证据；必须列出 writer、state owner 和 readback consumer。
- 如果新 mode 合法缺失旧 mode 专属字段，旧 schema/API/VO/mapper 的 required/null/default 约束必须成为 migration decision 和 DB/Migration contract candidate。

### Managed Resource Ownership Archaeology

当需求或旧代码出现 auto-create、default-created、generated resource、managed resource、select-existing、existing resource、自动创建、选择已有外部资源时，本阶段必须考古当前项目如何创建、标识、持久化和清理外部资源。目标是把“选择器/默认值”和“真实资源 ownership 生命周期”分开。

输出：

```markdown
### Managed Resource Ownership Archaeology

| Resource | Current selection/create modes | Provider/API writer path | Identity/tag/name convention | Ownership/provenance state owner | Runtime consumers | Update behavior | Delete cleanup/protect behavior | Failure/idempotency behavior | Existing pattern evidence | Contract candidate |
|---|---|---|---|---|---|---|---|---|---|---|
```

必须覆盖：

- 真实 provider/API/operator/resource writer 路径，不得只写 UI selector 或 DTO 字段。
- resource ID/name/ARN/UID/tag 如何生成、保存、读回。
- owned、existing、generated、derived 的 provenance 存在哪里，哪些消费者读取。
- 删除时 owned resource 如何清理，existing resource 如何保护，部分清理失败如何表达 residual。
- 重试 create/delete/update 时如何避免重复创建或误删。

失败条件：

- 文档出现 auto-create/select-existing/managed resource，但本表缺失，Stage 3 失败。
- 本表只有 selector/API options，没有 provider writer、identity、provenance、cleanup/protect，Stage 3 失败。

### Post-Create Consumer Archaeology

当需求创建或改变一个可被后续操作消费的对象时，本阶段必须追踪创建后的所有消费者。目标是防止“创建成功，但 logs/metrics/workers/connectors/update/delete 等消费者仍然默认旧 mode 或旧资源”。

输出：

```markdown
### Post-Create Consumer Archaeology

| Created/changed object | Consumer | Entry path | Existing old-mode assumption | Data/resource consumed | Valid for new mode? | Required product/contract decision | Owner surface ID | Verification candidate | Evidence |
|---|---|---|---|---|---|---|---|---|---|
```

必须覆盖：

- list/detail/progress/change/event。
- update-config、resize、delete、retry/failure recovery。
- workers、logs、metrics、endpoints、plugins。
- 下游对象创建或状态查询，例如 connector create/status。
- mock/playground fixture 和 packaged acceptance consumer。

判定规则：

- 旧 mode 专属 kubeconfig、namespace、serviceAccount、pod、deployment、cloud resource、runtime endpoint、log source、metric label 等默认 `Valid for new mode?=no/unknown`，除非有 evidence。
- consumer 不支持新对象时，必须进入 PRD/frontend/capability decision：hidden、disabled-with-reason、unavailable-with-reason 或 mode-specific implementation。
- 不能用 create flow smoke 关闭 post-create consumer。

## Phase 1.6: 旧模式语义继承审计

当需求新增或修改 deployment/runtime/compute/storage/network mode 时，本阶段强制执行。目标是证明哪些旧模式语义可以继承，哪些必须替换或禁用。不能只证明“代码里有分支”，必须证明用户可见语义和运行时语义都成立。

本阶段同时必须生成 `variant-impact-matrix.md`。触发条件是结构关系，不是关键词：如果新需求仍使用旧对象的同一个 action/readback/post-create consumer，但替换或新增底层实现形态，即使需求把它叫 deployment type、runtime backend、provider、runner、execution environment、placement、adapter 或其它名字，也必须进入 Variant Impact Matrix。

输出：

```markdown
### Mode Semantic Inheritance Audit

| Existing behavior | Existing mode | Source code/path | Hidden assumption | Valid for new mode? | Replacement/new behavior | Product decision | Evidence |
|---|---|---|---|---|---|---|---|
```

必须覆盖：

- 创建/更新/删除事件步骤和 change tracking
- 表单字段、规格字段、默认值和校验
- 详情页、进度页、列表页、操作按钮
- 日志、Worker、Endpoint、Metrics、插件加载和健康检查
- 后端 service/manager/task 状态机
- DB 状态字段、任务 payload、事件表/变更表
- 云资源：网络、权限、计算规格、镜像、密钥、模板、资源组、标签等 mode-specific 资源

判定规则：

- `Valid for new mode?` 只能是 `yes`、`no`、`partial`、`unknown`。
- `unknown` 不能进入实现；必须回到 PRD/AIP/contract 锁定。
- `partial` 必须拆分成可继承和不可继承的子行为。
- 旧模式专属词汇、资源或状态，例如 Kubernetes、Pod、Container、Deployment、ServiceAccount、Namespace、PVC、Helm，在新 mode 下默认判为 `no`，除非有明确 evidence 证明只是中性抽象。
- 如果补充 Terraform/API 设计把新 mode 定义为与旧 mode 同级，考古必须按同级模式审计，不能把新 mode 当作旧 mode 的子路径。

失败条件：

- 新增 mode 但没有 Mode Semantic Inheritance Audit，Stage 3 失败。
- 事件追踪、日志、Worker/Endpoint、规格语义任一项没有审计，Stage 3 失败。
- 旧模式行为被写入后续契约或任务，但本审计未标 `yes` 且无 evidence，Stage 3 失败。

### Variant Impact Matrix

使用模板：`ai-dev-methodology/templates/variant-impact-matrix.md`。

必须回答：

- 新变体是否仍使用同一个 object/action/API/page。
- 旧变体有哪些 consumer assumption 必须被新变体满足。
- 每个 existing consumer 对新变体是 `yes`、`no`、`partial` 还是 locked N/A。
- `yes` 时新变体的 producer/behavior 是什么；`partial/no` 时产品或架构决策是什么。
- 每行进入哪个 contract candidate 和 verification。

如果 progress/change/last-change 等 consumer 在旧模式存在且新变体需要支持，不能只写“mode-specific progress”；必须继续生成 `progress-change-producer-chain-matrix.md`。

### Local Audit Gate: Mode Inheritance Leak Audit

Phase 1.6 完成后，主 agent 必须本地二次 查旧 mode 语义是否被默认继承。本地审计不能决定新 mode 产品语义，只标记 leakage、unknown 和 decision gap。

输出：

```markdown
### Mode Inheritance Local Audit Report

| Existing behavior | Leakage risk | Evidence | Missing decision | Required backflow | Blocks next stage |
|---|---|---|---|---|---:|
```

阻塞条件：

- 新/改 mode 没有 Mode Semantic Inheritance Audit。
- `Valid for new mode?=unknown` 或 `partial` 未拆分。
- 旧 mode 专属事件、文案、资源、日志、Worker、Endpoint、Metrics 或任务状态机进入后续契约但无 evidence。

## Phase 1.7: 运行时链路与生命周期考古

当需求涉及云资源、异步任务、观测、自动调节能力、创建后操作或资源删除时，本阶段强制执行。目标是证明“对象创建后还能被正确管理”，不能只考古创建 API 或表单。

必须沿以下链路追踪：

```text
UI action/page -> API/client -> backend service/manager -> async task/change tracking -> cloud/Terraform/SDK/runtime -> DB/current data -> observability/UI display
```

输出：

```markdown
### Runtime Lifecycle Archaeology

| Lifecycle/capability | UI entry | API path/body | Backend owner | Async task/change event | Runtime/cloud resource | DB/current state | Observability source | Failure/cleanup behavior | Evidence |
|---|---|---|---|---|---|---|---|---|---|
```

必须覆盖：

- create、update deployment config、scale/auto-adjust、delete、retry/recover。
- change tracking 事件和用户可见文案。
- cloud resource 的 desired state owner、实际资源、tag/identity、清理路径、清理失败路径。
- Metrics/logs/worker/endpoint/plugin health 的数据来源、查询路径和空值语义。
- 自动调节能力的控制环：触发指标、阈值、冷却时间、调节执行者、状态回写、用户可观察证据。

证据要求：

- 每个能力必须有具体文件、接口、历史实现、测试、运行时样本或云资源摘要作为 evidence。
- 删除必须考古到实际清理调用和状态推进，不得只看到 delete API 就判定完成。
- Metrics 必须考古到 runtime 端是否暴露指标、采集配置是否下发、API 查询路径是否依赖 mode-specific label。
- 自动调节能力必须考古到负载如何触发调节，以及是否有可复现压测或替代证明。

失败条件：

- 需求触达创建后操作，但没有 Runtime Lifecycle Archaeology，Stage 3 失败。
- 删除、更新、指标或自动调节能力任一被 PRD 声明支持，但本表缺少 evidence，Stage 3 失败。
- 只考古 happy path 创建，没有覆盖失败/清理/状态回写，Stage 3 失败。

### Local Audit Gate: Runtime Lifecycle Evidence Audit

Phase 1.7 完成后，主 agent 必须本地二次 追查 create 之后的 update/delete/metrics/logs/auto-adjust 全链路证据。

输出：

```markdown
### Runtime Lifecycle Local Audit Report

| Capability | Missing lifecycle proof | Cleanup/terminal/observability gap | Evidence checked | Required backflow | Blocks next stage |
|---|---|---|---|---|---:|
```

阻塞条件：

- PRD 声明支持的删除、更新、指标、日志、Worker、Endpoint、自动调节任一能力缺 evidence。
- 只覆盖 happy create，没有状态回写、失败/清理、终态或幂等证据。
- 自动调节没有负载触发、控制者、阈值、状态回写或可观察证据。

## Phase 2: 隐式约束清单

必须从四类来源提取：

1. 测试：边界、禁用测试、fixture。
2. git history：最近 20 条核心文件提交和 bugfix commit。
3. 注释/文档：TODO、FIXME、兼容、workaround。
4. 防御性检查：assert、Preconditions、requireNonNull、异常分支。

输出：

```markdown
### Hidden Constraints

| ID | Constraint | Source | Consequence if violated | Code/location | Decision needed? |
|---|---|---|---|---|---|
```

## Phase 3: Pattern 与框架语义

### Code / API / Deployment Pattern

```markdown
| Scenario | Pattern | Reference | Must follow? |
|---|---|---|---|
```

### Frontend Pattern

如涉及前端，必须覆盖：

| Pattern | 必须回答 |
|---|---|
| 页面结构 | 参考哪个页面/组件 |
| 表单字段和校验 | 字段顺序、默认值、校验文案 |
| i18n | key 命名、语言文件位置 |
| 权限/菜单/路由 | 权限点、显示/隐藏规则、跳转 |
| 状态展示 | loading/error/empty/unknown |
| 表格/详情/tab | 列、tab、过滤、操作按钮 |

### Phase 3.1: 前端 Action Route Trace

当需求触达用户可见 action（按钮、菜单项、表格行操作、wizard submit、modal confirm、详情页操作、创建后更新/删除/扩缩容）时，代码考古必须追踪真实旧系统链路，不能只列“相关页面目录”。

必须从用户入口沿链路追踪到具体实现文件：

```text
visible action/menu/button -> permission/visibility guard -> route/path builder -> router definition -> page/component -> API client/helper -> backend handler or mocked external boundary
```

输出：

```markdown
### Frontend Action Route Trace

| Action ID | Visible text / i18n key | Source page/component | Visibility/permission guard | Click handler / route builder | Final route/path | Router definition | Landing page/component | API/client side effect | Existing mode assumptions | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
```

强制规则：

- `Final route/path` 必须是用户点击后真实进入的路径或 mutation API；不能写自然语言“更新页”。
- `Landing page/component` 必须写到具体 repo-relative 文件，例如 `.../update-basic-config/page.tsx`；不能只写目录或“update page”。
- `Existing mode assumptions` 必须列出落点页面继承的旧 mode 字段、文案、事件、校验、API payload 或默认值。新增 mode 时，旧 mode 专属假设默认是风险。
- 如果 action 的 visible text/i18n key、route builder 和 router definition 分散在不同文件，必须全部列证据。
- 任何 PRD 声明的创建后操作（修改部署配置、删除、扩缩容、失败恢复、metrics/logs/workers、自动调节）缺少 Action Route Trace 时，Stage 3 失败。
- 如果发现需求语义指向的页面和真实点击落点不一致，必须记录为 `archaeology-missed-action-route` blocker，回流到 frontend contract 和 atomic task planning；不得让实现阶段自行猜。

该表必须被 `frontend-contract-design` 和 `atomic-task-planning` 消费。后续 Atomic Issue 的文件清单不得与 Action Route Trace 的 landing component 冲突；如冲突，必须先修 issue。

### Local Audit Gate: Frontend Action Route Trace Audit

Phase 3.1 完成后，主 agent 必须本地二次 从可见 action 追到真实落点组件/API，专门发现“改错页面”风险。

输出：

```markdown
### Action Route Trace Local Audit Report

| Action ID | Auditor finding | Missing source/route/router/landing evidence | Wrong landing risk | Required backflow | Blocks frontend/task planning |
|---|---|---|---|---|---:|
```

阻塞条件：

- PRD 声明的 action 缺 trace。
- `Landing page/component` 不是具体文件。
- 真实点击落点与需求语义或 mode-specific contract 冲突。
- 创建后操作缺旧 mode assumption 审计。

### Framework Semantics

```markdown
| Framework/API | Method/config | Semantics | Common misuse | Reference |
|---|---|---|---|---|
```

## Phase 4: 下游输入

必须输出给后续阶段的输入。

```markdown
### Cross-Module Contract Candidates

| Candidate ID | Modules/resources | Scenario | Trigger condition | Normal path | Empty/null/fallback path | Failure path | Consistency/timing | Why cross-module | Source |
|---|---|---|---|---|---|---|---|---|---|

### Migration-Diff Inputs

| Old object/behavior | Constraint/pattern | Must preserve? | Source |
|---|---|---:|---|

### Decision Registry Updates

| Decision ID | Type | Decision or open question | Source | Affected modules | Status |
|---|---|---|---|---|---|
```

旧代码事实本身不是决策；只有当旧约束需要 preserve/modify/retire/replace，或 pattern 需要被新实现强制遵守时，才进入 Decision Registry。

## 退出检查

- [ ] Semantic Consumption Matrix 覆盖所有与旧系统相关的 REQ/SCN/PDEC/DEC/DESIGN-DEC，无 blocked 或无理由 dropped 行。
- [ ] Phase 0 模块边界已完成并通过粒度校验。
- [ ] 已完成 Module Boundary Validation，证明模块边界有所有权、状态机和变更独立性证据。
- [ ] 涉及 lifecycle/progress/event/status/terminal/polling/retry/mock state graph 时，已完成 Stateful Behavior Inventory，列出 producer、state owner、consumer、event/status fields、terminal behavior 和证据。
- [ ] 涉及既有对象/action/readback/post-create consumer 被新实现形态复用时，已产出 `existing-object-action-consumer-graph.md`，并从代码列出 producer chain、state owner、readback API/VO 和 consumer surface。
- [ ] 模块不限于后端代码，已覆盖本需求涉及的 API/前端/部署/云资源/观测。
- [ ] 核心依赖边有证据。
- [ ] 隐式约束来自测试、git history、注释/文档、防御性检查。
- [ ] Pattern 和框架语义能回答“照着谁做”。
- [ ] 涉及前端用户 action 时，已产出 Frontend Action Route Trace，并追踪到真实 visible action、route builder、router definition、landing component、API/client side effect。
- [ ] PRD 声明的创建后操作没有只停留在页面目录级考古；每个操作都有真实落点文件和旧 mode assumption 审计。
- [ ] `decision-surface-discovery.md` 的每个 surface 已被消费到考古证据、contract candidate、migration input、frontend trace 或 locked N/A；没有 surface 只留在 source/context 中。
- [ ] 创建或改变对象时，已产出 Post-Create Consumer Archaeology，覆盖 list/detail/progress/update/delete/workers/logs/metrics/connectors/mock/playground 等相关消费者。
- [ ] 若需求参考现有实现，已产出 Reference Implementation Field Matrix，并覆盖 UI/API/后端/任务/云资源/数据样本。
- [ ] 若需求新增/修改 mode，已产出 Mode Semantic Inheritance Audit，并逐项证明旧模式语义是继承、替换、禁用还是未知。
- [ ] 若需求新增/修改 runtime/provider/deployment/compute/storage/network 等实现变体，已产出 `variant-impact-matrix.md`，且不是靠关键词判断，而是根据同一 object/action/API/readback/consumer 结构判断。
- [ ] 新 mode 没有默认继承旧 mode 的事件、日志、Worker、Endpoint、规格、状态或云资源语义；所有继承都有 evidence。
- [ ] 涉及新 mode/资源类型/生命周期或持久化 mutation 时，已产出 Persistent Mutation / Schema Compatibility Audit，覆盖旧 schema/DO/mapper/VO/API required 约束、真实 writer、state owner、null/default/derived/forbidden 策略和 readback consumer。
- [ ] 没有把 “persisted / saved / canonical state” 当成持久化证据；每个 mutation 都能追到 writer、schema/resource constraint 和 readback proof candidate。
- [ ] 涉及云资源、异步任务、观测、自动调节能力、更新或删除时，已产出 Runtime Lifecycle Archaeology，并覆盖 UI/API/后端/task/runtime/DB/observability 全链路。
- [ ] 创建后能力没有只考古 happy path；删除清理、状态回写、指标采集、自动调节触发证据已明确，缺失则进入 blocker 或 Decision Registry。
- [ ] Reference Implementation Field Matrix 不是文件清单；每个字段/资源都有 `API path/params`、`Param source`、`Null/empty behavior`、`Disabled/visibility condition`、`Backend fallback/default`、`Runtime/current data sample` 和 `Evidence`。
- [ ] 涉及资源 selector 时，已逐项覆盖 VPC/Subnet/SecurityGroup/IAM Role/InstanceType/K8s/NodeGroup/Bucket/DNS/Image/AMI/KeyPair 等相关资源；不存在“复用 provider API”这种未展开结论。
- [ ] 所有用于前端禁用/隐藏、后端校验、默认推导的字段，都已证明真实 API/DB/current data 中稳定存在，或已记录为空值/fallback 契约。
- [ ] 已输出 contract candidates 和 migration inputs。
- [ ] Contract candidates 已包含 trigger、normal、empty/null/fallback、failure、consistency/timing 五类语义；不能只列模块名。
- [ ] 需要保留/改变/废弃的旧约束已进入 Decision Registry 或 migration inputs。
- [ ] 已完成适用的 Local Audit Reports：Module Boundary、Reference Field、Mode Inheritance、Runtime Lifecycle、Action Route Trace；无阻塞项。
- [ ] 结果已写入或链接到 `specs/changes/<change-id>/plan.md`。
- [ ] 已满足 artifact-completeness-spec Stage 3 的 Module Boundary、N1/N2、Dependency/Data Flow、Hidden Constraints、Framework Semantics、Pattern Reference、Reference Implementation Field Matrix artifact 要求。
