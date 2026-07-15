---
name: verification-matrix
description: 建立需求、场景、契约到验证的矩阵。Use before implementation to ensure every REQ/SCN/contract/migration decision has a defined unit, integration, E2E, render, plan, runtime, manual, or documentation verification, and to feed verification commands into tasks.md.
---

# Verification Matrix

## 定位

验证必须前置设计，而不是写完代码后再想。

本 skill 把 `REQ/SCN/Contract/Migration` 映射到证明方式，并输入 `tasks.md`。

验证矩阵不仅验证单个模块或单个 issue，还必须验证模块划分和模块组合是否支撑需求。模块内部单测只能证明局部正确，不能替代模块组合验证。

对前端用户流程，验证矩阵必须验证用户意图闭包，而不是只验证页面渲染或 API client：

```text
User intent -> reachable UI state -> action -> validation scope -> API/event side effect -> feedback -> next state
```

任何 create/update/delete/save/submit/scale/bind/import/export 等 mutation flow，如果没有 DOM/browser/mock acceptance proof，只能记录 Blocks done 的 Not Run risk，不能被 service-level payload/path test 关闭。

执行或评审本阶段时，必须按 `ai-dev-methodology/references/artifact-completeness-spec.md` 的 “Stage 8: Verification Matrix” 检查正交维度、Required Artifacts、Completeness Criteria 和 Exit Gate。

创建验证矩阵时必须使用或等价满足 `ai-dev-methodology/templates/verification-matrix.md`。评审时使用 `artifact-review-rubric.md` 的 Verification Rubric。

本阶段产生的验证类型、fixture、runtime smoke、manual/not-run 取舍决策，必须写入 `specs/changes/<change-id>/decision-reviews/verification-decisions.md`，使用或等价满足 `ai-dev-methodology/templates/stage-decision-document.md`，并同步进入 Decision Registry。Not Run 是显式风险决策，不能只是缺失验证。

Not Run 需要区分“可带风险继续”和“阻塞完成”。任何 P0/P1、核心 REQ/SCN、关键跨模块契约、组合验证、runtime lifecycle 或 `Blocks done=yes` 的 Not Run 都阻塞完成声明。

本阶段必须维护 `Semantic Consumption Matrix`：消费 `REQ/SCN/PDEC/DEC/C/MIG` 以及 `external-capability-research.md` 中影响验证的外部 Fact/Constraint，派生 `VER-xxx`、Not Run risk 和验证决策。每个上游语义对象必须有 proof、Not Run risk 或明确 N/A；不能让 PRD/契约/外部事实语义在验证阶段丢失。

本阶段还必须消费 `decision-surface-discovery.md`。每个 mode consumer、capability、frontend action、post-create consumer、persistent mutation、managed resource ownership、runtime lifecycle、mock acceptance / repo-specific acceptance runtime surface 必须有组合 proof、mock/frontend/backend proof、Not Run risk 或 locked N/A。不能用 create smoke 关闭 post-create consumer；不能用 route/page load 关闭 action/mutation/capability；不能用 selector/validation proof 关闭 managed resource ownership。

如果存在 `mechanism-design-model.md`，本阶段必须消费所有影响实现的 `MECH/OPSEQ/EXTAPI/EVT/RMM/RLM/FCM/MIM` 行，并为每行给出 proof、Not Run risk、locked N/A 或 blocker。验证矩阵不能只证明“功能可创建”，还要证明设计阶段定义的生产机制确实发生：外部参数映射、事件字段、runtime carrier、resource cleanup/protect、failure consistency 和 readback。

本阶段必须维护 `Verification Feasibility Gate`：在任务规划前确认验证环境、fixture、账号、云资源、浏览器路径和 setup owner 是否可用。验证不可运行不是执行阶段才发现的事。

如果需求涉及 mock acceptance / no-cloud acceptance / repo-specific acceptance runtime，验证矩阵必须把验收适配器当作交付物验证，而不是只把 mock 当测试数据。实现前的验证矩阵只能锁定生产实现必须发生的外部 adapter/API/resource 副作用、前后端消费契约和待验收维度；不得读取当前仓库专属验收 runtime / no-cloud adapter 实现细节来决定生产实现边界。必须证明真实实现、验收适配器和前端消费契约没有 drift。

## 输入

- `spec.md`
- `plan.md`
- Cross-module contracts
- Module Contract Graph / Module Boundary Validation
- Migration plan
- Decision Registry
- `decision-surface-discovery.md`，如果存在或需求触发决策面发现。
- `external-capability-research.md`，如果验证、mock acceptance、repo-specific acceptance runtime 或 Not Run 风险依赖外部系统事实。
- `mechanism-design-model.md`，如果存在。
- `Semantic Consumption Matrix`，如已存在则更新；不存在则按模板创建。
- `Verification Feasibility Gate`，使用 `ai-dev-methodology/templates/verification-feasibility.md`。

## 输出

写入 `plan.md` 或 `tasks.md`：

```markdown
### Semantic Consumption Matrix - Verification

| Upstream object | Required by verification? | How consumed | Derived object | Copied semantics | Dropped semantics | Drop reason / decision | Verification / gate | Status |
|---|---:|---|---|---|---|---|---|---|
```

要求：

- 每个 `REQ/SCN/PDEC/DEC/C/MIG` 必须映射到 `VER-xxx`、Not Run risk、explicit N/A 或 blocker。
- 每个影响验证的外部 `Fact ID` / `Constraint ID` 必须映射到 `VER-xxx`、mock acceptance / repo-specific acceptance runtime fixture proof、Not Run risk、explicit N/A 或 blocker。
- 每个影响验证的 `MECH/OPSEQ/EXTAPI/EVT/RMM/RLM/FCM/MIM` 必须映射到 `VER-xxx`、Not Run risk、explicit N/A 或 blocker。
- 每个 `decision-surface-discovery.md` surface 必须映射到 `VER-xxx`、Not Run risk、explicit N/A 或 blocker。
- `Copied semantics` 必须写明要证明的行为、失败语义、状态、错误或契约要点，不能只有 ID。
- `Dropped semantics` 必须有 locked decision 或 explicit N/A。
- `Status=blocked` 阻塞 atomic task planning。

```markdown
## Verification Feasibility Gate

| Verification | Source | Required? | Environment / fixture needed | Available? | Setup owner/command | Fallback | Blocks done | Risk |
|---|---|---:|---|---:|---|---|---:|---|
```

要求：

- 每条 required verification 必须说明环境/fixture 是否可用。
- `Available?=no` 且 `Blocks done=yes` 必须进入 Not Run Risk Table，并阻塞 done。
- fallback proof 也必须有 expected result 和 proves。
- setup 命令或 owner 必须复制到 tasks/Atomic Issue。

```markdown
## Verification Matrix

| Source | Behavior / contract | Verification type | Command / manual step | Expected result | Proves | Required before merge | Risk if not run |
|---|---|---|---|---|---|---:|---|
| REQ-001 |  | unit/integration/e2e/manual |  |  |  | yes/no |  |
```

Verification Matrix 不是最终执行说明。`atomic-task-planning` 必须把每条相关 verification 展开到对应 Atomic Issue，并补齐 expected result 和 proves。

### Local Audit Gate: Verification Consumption And Feasibility Audit

Semantic Consumption Matrix、Verification Feasibility Gate 和 Verification Matrix 候选稿写出后，主 agent 必须本地二次审计验证消费和可运行性。本地审计只标记 proof gap，不替主流程接受风险。候选验证矩阵不能被任务规划消费；只有无阻塞 proof gap 或已由用户/owner 明确接受的 Not Run 风险后，才能进入 Atomic Task Planning。

输出：

```markdown
### Verification Local Audit Report

| Source | Claimed proof | Auditor finding | Missing composition path | Required verification/backflow | Blocks done |
|---|---|---|---|---|---:|
```

必须审计：

- 每个 REQ/SCN/PDEC/DEC/C/MIG 是否有 proof、Not Run risk 或 locked N/A。
- 每个外部 Fact/Constraint 是否有 proof、mock acceptance / repo-specific acceptance runtime drift guard、Not Run risk 或 locked N/A。
- 每个机制模型行是否有 proof、Not Run risk 或 locked N/A，尤其是 external API parameter mapping、event/state rows、runtime materialization、resource lifecycle、failure consistency。
- required verification 的环境、fixture、账号、浏览器、mock、runtime 是否可用。
- 是否用模块内单测替代模块组合验证。
- 是否用 service/API/payload test 替代 frontend action route、DOM/browser 或 product semantic proof。
- 是否用 create smoke 替代 update/delete/metrics/auto-adjust runtime proof。
- 是否有 decision surface 只停留在 PRD/plan/context，没有具体 proof 或 Not Run risk。

阻塞条件：

- `Status=blocked` 或 `Available?=no` 且 `Blocks done=yes`。
- P0/P1、关键 REQ/SCN、关键契约、runtime lifecycle 或 composition verification 无可执行 proof。
- decision surface 中的 supported / mode-specific-implementation-required capability 没有对应验证。
- mechanism design row 没有对应验证，或验证只证明最终成功状态而没有证明生产机制、参数、事件、runtime、resource lifecycle、failure consistency/readback。
- verification 没有 expected result、proves 或 failure meaning。

## 验证类型

| Type | 适用 |
|---|---|
| unit | 纯函数、转换、状态计算 |
| integration | manager/service/API/DB |
| e2e | 跨服务用户流程 |
| frontend | typecheck/lint/build/browser |
| frontend-action-flow | DOM/browser/mock acceptance；验证真实页面 action 触发 API/event 或字段级错误 |
| api-route | Controller/OpenAPI 最终 HTTP path 命中、鉴权前后状态、404 防回归 |
| mock-drift | 真实契约、mock 契约、前端消费契约的 path/body/response/enum/state/error/progress 反漂移 |
| mock-composition | 真实 controller/DTO/service + mock 外部依赖的用户视角组合链路 |
| api-flow-dag | 多接口用户场景的 API/task/state 调用图、边契约、路径覆盖、时间顺序断言 |
| terraform | fmt/validate/plan/provider tests |
| helm | template/lint/schema |
| cloud-runtime | provider-managed compute group/IAM/RBAC/lifecycle hook smoke |
| observability | metric/event/log/alert validation |
| runtime-lifecycle | create/update/delete/scale/retry 状态推进、任务事件、云资源一致性 |
| auto-adjust-load | 用 CPU/内存/lag/等价负载触发运行时自动调节并观察状态回写 |
| manual | 无法自动化但必须人工确认 |
| docs | 文档链接、render、runbook |

后端行为验证不得退化成 compile/build。凡是验证对象包含 API schema、DTO/VO、service/domain validation、persistence compatibility、task/runtime executor、provider selector、managed resource ownership、event/progress、autoscaling decision，都必须生成至少一条 `unit`、`integration`、`api-route`、`runtime-lifecycle`、`mock-composition` 或 `api-flow-dag` 行，且 `Expected result` 写到具体断言：

- typed error / field error / warning 是否出现。
- 旧 payload / 旧 DB row 是否兼容。
- persisted state / response body / progress status / event 字段是否正确。
- failure branch、unknown vs explicit failure、idempotency/retry 是否符合契约。

Progress/change/last-change 验证必须证明生产写入/readback 链，而不是只证明前端 fixture 或最终状态。凡是 `progress-change-producer-chain-matrix.md` 存在，至少要有同一对象 id 的闭环 proof：

```text
mutation API -> production writer/task/event -> state owner -> last-change readback -> change detail readback -> frontend/API consumer
```

例如 create 类场景必须验证同一个 created id：create 成功或失败后，`/last-change` 非空或返回锁定的 empty behavior，`/changes/{changeId}` 包含该 operation/variant 的 step/status/terminal/failure reason。Frontend progress fixture 只能作为消费 proof，不能关闭 producer proof。

External side-effect 验证必须消费 `external-side-effect-contract-matrix.md`，逐行证明最低可接受 production proof。若矩阵锁定 provider/operator/API/resource mutation，则验证必须能观察到真实产品路径跨过该边界；no-cloud/playground 只能替换物理外部端点，不能替换 manager/task/provider 调用链。只证明 DB 终态、fixture event、日志 hook、页面展示或 compile/build，不足以关闭外部副作用契约。

Runtime/test topology 验证必须消费 `runtime-test-topology-matrix.md`。凡是 proof owner 不在当前实现模块、测试依赖本地 SNAPSHOT、需要 package/bundle/image freshness、或必须用 runtime task/packaged playground 才能观察生产路径时，Verification Matrix 必须写出 proof module/package、proof file/path、required build/install/freshness step、exact verification command、staleness risk，以及 proof file 是否进入 owner task allowlist。无法纳入 owner task `files_to_change` 和 `task-dag.yaml.files` 时不得进入执行，必须回流 task planning。

Managed resource ownership 验证必须至少包含三类 proof：

| Proof | Required assertion |
|---|---|
| Provider mutation proof | auto-create/default-created/generated 路径真实调用生产 provider/API/operator/resource writer；select-existing 路径不得创建新资源 |
| Ownership readback proof | resource ID/name/tag 和 owned/existing/generated provenance 被权威 state owner 写入，并能被 detail/list/runtime/progress 等消费者读回 |
| Cleanup/protect proof | delete/update/retry 对 owned 资源执行 cleanup/replace，对 existing 资源执行 protect/detach；partial cleanup failure 有 typed residual state |

只验证 selector 候选、DTO validation、resolvedConfig、页面渲染或 simulator fixture，不足以关闭 managed resource ownership。

`compile`、`package -DskipTests`、checkstyle、PMD 只能作为 supporting verification，不得作为 `Required before merge=yes` 的唯一 proof。若短期只能 compile，必须写 Not Run risk，且核心 contract 的 `Blocks done=yes`。

## Module Boundary Validation Gate

验证模块划分是否合理。若 `code-archaeology-sdd` 或 `new-feature-design` 已产出 Module Boundary Validation，本阶段必须把其中的风险转成验证或 Not Run risk。

输出：

```markdown
| Module | Boundary decision | Ownership evidence / proof | State-machine proof | Contract enumerability proof | Granularity risk | Command / manual step | Expected result | Risk if not run |
|---|---|---|---|---|---|---|---|---|
```

必需通过覆盖：

- 模块 owned state/data/resource 有证据。
- 模块内部状态机自洽，有测试/代码路径/场景证明。
- 模块外部依赖都能映射成 consumed contracts。
- 模块对外承诺都能映射成 provided contracts。
- split/merge/keep 决策有验证或评审证据。

## Module Composition Verification Gate

验证模块组合后能满足需求。每个关键 REQ/SCN 必须至少有一条组合路径。

输出：

```markdown
| REQ/SCN | Composition path | Provider contracts | Consumer assumptions | Verification type | Command/manual step | Expected result | Proves |
|---|---|---|---|---|---|---|---|
```

要求：

- `Composition path` 写清模块链路，例如 `FrontendModeUI -> Domain API -> ConfigResolver -> AsyncTask -> ExternalProvider`。
- `Provider contracts` 写提供方契约 ID。
- `Consumer assumptions` 写消费方假设哪些契约成立。
- 验证必须证明 provider 输出满足 consumer 输入，而不是只证明两个模块各自单测通过。
- 对用户可见流程，优先使用 integration/e2e/browser/runtime/manual 组合验证；没有组合验证时必须记录 Not Run risk。

### Local Audit Gate: Module Composition Proof Audit

Module Composition Verification Gate 完成后，主 agent 必须本地二次审计 provider guarantee 是否满足 consumer assumption，且组合路径是否覆盖关键用户场景。

输出：

```markdown
### Composition Proof Local Audit Report

| REQ/SCN | Composition path | Auditor finding | Missing provider/consumer proof | Required backflow | Blocks task planning |
|---|---|---|---|---|---:|
```

阻塞条件：

- 关键 REQ/SCN 无组合路径。
- consumer assumption 找不到 provider contract。
- 只用模块内部单测关闭组合路径。

## Backend API Flow DAG Composition Gate

当后端功能由多个接口、异步任务、状态查询、外部依赖或创建后操作组合而成时，必须先生成 API Flow DAG，再从 DAG 生成组合测试。不能只按接口列表逐个写单测。

### 1. API Flow Graph

```markdown
| Node ID | Node type | Operation | Input source | Output/state produced | User-visible meaning |
|---|---|---|---|---|---|
```

节点类型包括：

- `api-read`：list/get/detail/options/status/metrics/logs。
- `api-mutation`：create/update/delete/retry/scale/save/control。
- `async-task`：后台任务、change tracking、event sequence。
- `state-transition`：业务对象状态、外部资源状态、terminal state。
- `external-dependency`：被 mock 或真实调用的外部系统。
- `ui-action`：如果该后端链路由前端 action 触发，记录入口动作。

每个核心用户场景必须能映射到一条从入口节点到终态节点的路径。

### 2. Edge Contract Matrix

```markdown
| Edge | From -> To | Data carried | Precondition/state | Normal path | Failure path | Timing/idempotency/retry | Verification |
|---|---|---|---|---|---|---|---|
```

要求：

- `Data carried` 写清上游输出哪些字段会成为下游输入或状态前提。
- `Precondition/state` 写清下游接口允许执行的对象状态、权限、依赖状态。
- `Failure path` 必须是 field-specific 或 contract-specific；不能只写 generic failure。
- `Timing/idempotency/retry` 必须覆盖 polling、terminal stop、重复提交、重复删除、重试、并发操作。
- 任一边无法说明 provider 输出如何满足 consumer 输入，必须回流到 cross-module contract。

### 3. Path Coverage Matrix

```markdown
| Path ID | Source scenario | DAG path | Covered branches | Parameter dimensions | Failure/terminal covered | Test type/command | Expected result | Blocks done |
|---|---|---|---|---|---|---|---|---:|
```

路径覆盖规则：

- 每条主 happy path 必须覆盖。
- 每个 branch edge 至少被一条路径覆盖。
- 每个 failure edge 至少被一条路径覆盖。
- 每个 terminal state 至少被一条路径覆盖。
- 每个合法 state transition 至少被一条路径覆盖；非法 transition 必须有拒绝路径或 locked N/A。
- 每个用户可达参数组合必须覆盖；不可达组合必须标 N/A 并说明原因。
- retry/idempotency/polling loop 必须展开为有限路径，例如 `running -> poll -> terminal`、`delete partial failure -> retry -> terminal`。

### 4. State/Time Assertion Matrix

```markdown
| Assertion ID | Applies to path/edge | Before | Action | After | Must not happen | Proves |
|---|---|---|---|---|---|---|
```

组合测试不能只断言 HTTP 2xx。至少断言：

- mutation 后 detail/list/progress/status 的状态一致。
- progress/change terminal 后不再被当成 running。
- update/delete/retry 的前置状态和后置状态符合契约。
- 外部依赖失败后对象状态、错误、可重试性和残留资源表达正确。
- 重复请求不会重复创建不可清理资源，或按契约幂等失败。
- read APIs 在对象创建中、成功、失败、删除中、删除后返回一致的用户语义。

### 5. Orthogonal Dimension Matrix

```markdown
| Dimension | Values | Coupling strength | Pair/full/representative rule | Covered by paths | N/A values |
|---|---|---|---|---|---|
```

组合爆炸控制规则：

- 强耦合维度必须全组合，例如 mode 与 mode-specific payload、状态与允许操作、依赖可用性与错误映射。
- 弱耦合维度使用 pairwise 或代表性覆盖，但必须写选择理由。
- 状态机边、用户可达路径、失败边和终态不允许用 pairwise 省略。
- 不可达组合必须由 PRD、契约或代码状态机证明为 N/A。
- 任何省略的 P0/P1 用户可达组合都必须进入 Not Run risk，不能默认为已覆盖。

输出的 API Flow DAG、Edge Contract Matrix、Path Coverage Matrix、State/Time Assertion Matrix 和 Orthogonal Dimension Matrix 必须被 `atomic-task-planning` 消费，生成独立的 backend composition acceptance issue 或写入对应 mock acceptance issue。

### Local Audit Gate: API Flow DAG Coverage Audit

Backend API Flow DAG Composition Gate 完成后，主 agent 必须本地二次审计 DAG、边、路径、状态/时间和维度覆盖。

输出：

```markdown
### API DAG Local Audit Report

| Path/edge | Auditor finding | Missing state/time assertion | Missing failure/terminal coverage | Required verification/backflow | Blocks done |
|---|---|---|---|---|---:|
```

阻塞条件：

- 只有接口列表，没有 DAG。
- failure/terminal/retry/idempotency 未覆盖。
- provider 输出如何满足 consumer 输入说不清。
- 只断言 HTTP status，没有状态/时序断言。

## Mock Delivery Verification Gate

当需求需要 mock acceptance / no-cloud acceptance / repo-specific acceptance runtime，必须输出：

```markdown
| Mock contract | Real source of truth | Mock artifact | Consumer | Verification type | Command/manual step | Expected result | Blocks done |
|---|---|---|---|---|---|---|---:|
```

如果目标仓库/应用是 automqbox/CMP，验证矩阵在实现前不得消费当前
`mock-acceptance-gate/references/cmp-playground.md` 的架构事实，也不得读取当前
`cmp-playground` 代码细节，除非本需求就是修改 playground 基础模块。此阶段只分配
VER 行：生产 adapter/API/resource 副作用证明、backend matrix、frontend action matrix、
packaged representative case、strict case validator、representative browser
click/select/submit evidence、CMP top-level smoke。controller routing guard、acceptance adapter、
fixture graph audit、packaged runtime freshness 等 playground 架构事实必须在
`mock-acceptance-gate` 执行阶段重新读取并填写；缺任一项时，automqbox/CMP playground acceptance 只能是
blocked 或 Not Run，不能被 API smoke 或页面加载替代。

mock verification 必须采用三层 proof；automqbox/CMP 的第三层是 packaged playground：

| Proof layer | Purpose | Typical verification type | Can replace |
|---|---|---|---|
| Backend Mock Matrix | 快速覆盖 controller/service/mock-handler/mock-service/API/state 组合 | mock-composition / mock-drift / api-flow-dag | 不能替代 frontend action 或 packaged freshness |
| Frontend Action Matrix | 快速覆盖真实 route/component/API-client/DOM/payload/user action 组合 | frontend-action-flow / mock-drift | 不能替代 backend state semantics 或 packaged freshness |
| Packaged / Repo-Specific Representative Cases | 证明打包产物、静态资源、真实浏览器路由、handler wiring 和 handoff QA；automqbox/CMP 中是 packaged playground | e2e / browser / runtime-freshness | 不能替代前两层的组合覆盖 |

验证矩阵必须把组合覆盖优先分配给 backend/frontend 快矩阵，把 packaged/runtime representative case
只作为代表性集成证明。若某维度只能通过 packaged runtime 验证，必须写明原因和
Blocks done 风险。

必需通过覆盖：

- mock handler/simulator/fixture 覆盖每个被测 controller/API 方法，不允许静默 fallback 到真实外部依赖。
- request path、method、query、body 与真实 API/client 一致。
- response shape、字段名、enum、错误码、状态机、进度/任务终态、空值/不可用语义与真实外部契约一致。
- mock 内部状态必须经过与真实服务等价的 externalize/adapter/normalization 后再给 consumer。
- 用户可达 happy path、failure path、edge case、terminal state 都有 fixture 或 simulator state。
- 前端至少有 contract/DOM/browser proof 证明真实页面正确消费 mock response；只测 service fixture 不足以关闭 UI 流程。
- mock 展示环境刷新必须验证 bundle/package/process freshness。

输出还必须包含 mock matrix preflight：

```markdown
| Matrix | Source semantics | Coverage sets | Owner issue | Command | Expected result | Proves | Blocks packaged/runtime acceptance |
|---|---|---|---|---|---|---|---:|
```

规则：

- `mock-backend-matrix.yaml` 和 `mock-frontend-action-matrix.yaml` 都必须有 VER 行。
- 每个 required coverage set 必须映射到 backend matrix、frontend matrix 或 packaged representative cases。
- Packaged representative case 必须追溯到 backend/frontend matrix refs；没有 refs 的 packaged case 只能算 smoke，不能关闭需求。
- 如果前后端矩阵任一阻塞，packaged/runtime representative case 不得用于声明 acceptance passed。

如果 mock 与真实契约存在 locked 差异，必须在 `Expected result` 和 product acceptance 边界中说明；没有 locked 差异时，任何 drift 都是 failure。

### Local Audit Gate: Mock Drift Audit

Mock Delivery Verification Gate 完成后，主 agent 必须本地二次 比对真实契约、mock 契约和前端消费契约。

输出：

```markdown
### Mock Drift Local Audit Report

| Mock contract | Auditor finding | Drift area | Missing guard | Required backflow | Blocks acceptance |
|---|---|---|---|---|---:|
```

阻塞条件：

- mock path/body/response/enum/status/progress 与真实契约 drift。
- mock 静默 fallback 到真实外部依赖。
- mock 直接替代被测 controller/API/service。
- 前端只测 fixture，不测真实页面消费。

## 代表性运行时样本

对云资源、部署模式、控制面创建流程、派生配置逻辑，mock 单测只能证明局部转换，不能证明真实环境配置完整性。必须至少加入一个 `representative-fixture` 或 `runtime-smoke` 验证：

```markdown
| Source object | Required real-ish fields | Missing-field case | Verification | Risk if skipped |
|---|---|---|---|---|
```

要求：

- 样本字段必须来自真实环境、DB fixture、API fixture 或参考实现字段矩阵，而不是只构造理想 mock。
- 如果后端从已有对象推导配置，必须覆盖“字段完整”和“字段缺失”两类路径。
- 如果无法访问真实云环境，至少验证到 API 创建请求、部署计划、任务参数或 cloud SDK request 生成层。
- 错误验证必须断言具体缺失字段/资源，不能只断言 generic invalid error。

## Mode Runtime Acceptance Gate

当需求新增或修改 deployment/runtime/compute/storage/network mode，必须加入真实路径验收 gate。单元测试、payload 测试、mock manager 测试不能替代该 gate。

必须输出：

```markdown
| Mode | User path | Browser required? | API/runtime required? | Environment | Evidence required | Required before done |
|---|---|---:|---:|---|---|---:|
```

必需通过验收路径：

- 浏览器打开真实页面，完成创建/更新流程或打开已创建对象详情。
- 打开创建进度/change tracking 页面，确认没有旧 mode 专属事件泄漏。
- 打开详情页、配置页、Worker/Endpoint、日志、Metrics、插件相关入口，确认 show/hide/disabled/unavailable 与契约一致。
- 用真实 API 查询对象详情和 last-change，确认用户可见状态与底层状态一致。
- 对云资源 mode，查询云端资源摘要，例如资源组、启动模板、计算实例、权限、网络、镜像、标签。

Evidence 可以是截图、API 响应摘要、DB 非敏感字段、cloud CLI 摘要或日志片段。若环境不可用，必须记录 Not Run risk，并且不能声称该 mode 已端到端验收完成。

## Frontend Action-Flow Verification Gate

当需求涉及前端 mutation action、wizard submit、mode switch 后提交、批量操作或创建后操作时，必须输出：

```markdown
| Flow | Source action contract | Reachable UI state | Validation scope | Expected API/event | Expected payload/params | Success evidence | Failure evidence | Tool/environment | Blocks done |
|---|---|---|---|---|---|---|---|---|---:|
```

同时必须输出 Action Route Render Verification：

```markdown
| Action ID | Visible action / i18n key | Source component | Final route/API | Router definition | Landing component/file | Mode/source state | Expected rendered surface | Forbidden inherited surface | Verification type/command | Blocks done |
|---|---|---|---|---|---|---|---|---|---|---:|
```

该表是 `frontend-action-flow` 的前置证明。它证明用户动作落到正确页面/组件，不能由 payload builder、API client test 或 backend mock service test 替代。

同时必须输出 Mode Field Display Verification：

```markdown
| Surface | Mode/state | Must show | Must hide | Fixture/ref | DOM assertion | Browser step | Blocks done |
|---|---|---|---|---|---|---|---:|
```

该表证明详情页、配置 tab、summary、创建后操作页面和状态页没有旧 mode 字段泄漏。它必须被 `frontend-mode-field-display-matrix.md` 和前端 Atomic Issue 的 `mode_field_display_matrix` 消费。

必需通过覆盖：

- final submit 必须从真实页面或等价 DOM 状态触发，而不是只测 payload builder。
- 创建后操作必须先证明 `visible action -> final route -> landing component` 正确，并断言 landing component 按 mode 渲染。
- mode switch 后 submit 必须证明 inactive/hidden fields 不参与校验，active required fields 参与校验。
- mode-specific action 必须有旧 mode 泄漏负向检查，例如旧 mode 专属字段、文案、事件、payload 分支不得出现或提交。
- 详情页、配置 tab、summary、update-config、resize、workers/metrics/logs/progress 等 mode-specific surface 必须有 must show/must hide 字段级 DOM 断言。
- 成功路径必须证明 API request、payload、toast/跳转/刷新/状态推进。
- 失败路径必须证明字段级或契约级错误展示；无反应是失败。
- 依赖 selector 必须覆盖 loaded/empty/error/parent-change-reset。
- 若浏览器/DOM 测试工具缺失，必须写 Not Run risk，并把 display/runtime 环境的手工 submit smoke 设为 Blocks done；automqbox/CMP 中该 runtime 可以是 playground。
- 如果使用后端静态资源 jar/image 验收，必须验证前端 bundle、jar/image、进程 PID 都晚于修复。

若验证矩阵覆盖的是用户可见 workflow，必须把相关场景标记为是否需要后续 `product-acceptance-review`。Verification 证明“行为被测试”，Product Acceptance 证明“产品语义自洽”；两者不能互相替代。

```markdown
| Source | Needs product acceptance? | Acceptance focus | Evidence expected |
|---|---:|---|---|
```

Mode-specific 负向检查：

```markdown
| Mode | Forbidden inherited behavior | Check | Expected result | Proves |
|---|---|---|---|---|
```

示例：新 provider-managed compute mode 下禁止出现旧 orchestrator mode 的专属资源创建事件；日志入口若不支持必须隐藏或明确 unavailable；规格不得显示旧 mode 专属 resource spec 语义。

### Local Audit Gate: Action-Flow Proof Audit

Frontend Action-Flow Verification Gate 完成后，主 agent 必须本地二次审计真实 action -> route/component -> API/event -> feedback 是否被证明。

输出：

```markdown
### Action-Flow Local Audit Report

| Flow/action | Auditor finding | Missing route/render/side-effect proof | Forbidden inherited leak risk | Required verification/backflow | Blocks done |
|---|---|---|---|---|---:|
```

阻塞条件：

- wizard/modal/bulk/mode-switch submit 未单独验证。
- payload builder、API client 或 service fixture 被用来替代 action proof。
- 创建后 action 缺 route/component render proof。
- 旧 mode 泄漏负向检查缺失。

## Runtime Lifecycle Verification Gate

当需求涉及云资源、异步任务、创建后操作、删除、observability 或运行时自动调节能力，必须加入运行时生命周期验证。创建成功不能替代更新、删除、指标或自动调节验证。

必须输出：

```markdown
| Capability | Verification type | Command/manual step | Expected result | Evidence required | Required before done |
|---|---|---|---|---|---:|
```

必需通过覆盖：

- create：对象、任务、云资源、UI 状态一致。
- update deployment config：进入 mode-specific 修改页面，提交后任务、runtime 和详情摘要一致。
- delete：控制面对象终态、云资源清理或残留资源表达、重复删除幂等。
- failure/retry：失败时用户能看到恢复动作，重试不重复创建不可清理资源。
- observability：metrics/logs/worker/endpoint/plugin 入口与契约一致；空值、0、query error 可区分。
- 自动调节能力：必须通过 CPU 压力、内存压力、lag 或契约定义的等价负载触发调节，观察 desired/actual capacity、事件和 UI/API 状态变化。

规则：

- 自动调节能力只验证 policy/config 写入不算通过，除非 Decision Registry 明确标为 Not Run 并说明风险。
- Metrics 只看页面非空不算通过；必须证明 runtime 暴露、采集、API 查询、UI 展示链路至少到故障可定位的层级。
- 删除验证必须检查资源清理或残留资源告警；不得只验证 HTTP delete 返回成功。
- 如果环境被回收或无法跑 runtime 验证，必须把相关项写入 Not Run risk，不得宣布产品验收或上线标准已满足。

### Local Audit Gate: Runtime Proof Audit

Runtime Lifecycle Verification Gate 完成后，主 agent 必须本地二次审计创建后能力验证是否覆盖真实能力。

输出：

```markdown
### Runtime Proof Local Audit Report

| Capability | Claimed proof | Auditor finding | Missing runtime evidence | Required verification/backflow | Blocks done |
|---|---|---|---|---|---:|
```

阻塞条件：

- create smoke 替代 update/delete/metrics/auto-adjust。
- 自动调节只验证配置写入，没有 CPU/内存/lag 或等价负载触发证据。
- Metrics 只看页面非空，未证明 runtime 暴露、采集、API 查询和 UI 展示链路。
- Not Run 未阻塞 done。

## Stateful Behavior Verification Gate

当 `cross-module-contract-sdd` 产出 Stateful Behavior Matrix，验证矩阵必须从矩阵行生成验证，而不是只写“event/progress API tests”。

必须输出：

```markdown
| Stateful row | Operation | Mode/variant | Transition | Producer proof | API/event proof | Frontend consumer proof | Mock fixture proof | Terminal/polling proof | Expected result | Proves | Blocks done |
|---|---|---|---|---|---|---|---|---|---|---|---:|
```

规则：

- 每个用户可达 transition 至少有一个 proof。
- 每个 terminal state 必须有停止 polling、后续 action enable/disable 或状态不可再推进的 proof。
- 每个 failure/blocked/rejected state 必须验证 typed reason 或 field/contract-specific reason。
- 每个 frontend consumer 必须有 DOM 或 action-flow assertion，不能只靠 backend API test。
- 每个 mock acceptance / repo-specific acceptance runtime consumer 必须有 fixture row 或 mock matrix row，不能只靠 packaged browser smoke。
- operation、mode/variant、status、failure/terminal 这些强耦合维度不允许用 pairwise 省略；省略必须是 locked N/A 或 Not Run risk。
- 验证失败必须回流到状态机矩阵对应的 contract/verification/task，而不是让实现阶段临场补事件名或状态语义。

## 规则

- 每个 REQ/SCN 至少有一个 verification。
- 每个 locked contract 至少有一个 verification。
- 每个核心模块边界风险有 validation 或 Not Run risk。
- 每个关键 REQ/SCN 至少有一个 module-composition verification，或明确 Not Run risk。
- 每个 consumed contract 都有 provider contract；不允许 consumer 假设无 provider 的契约。
- 每个 migration action 至少有一个 verification。
- 每个前端会调用的新/改 API 至少有一个 `api-route` verification，使用最终外部 path/query/body。
- 每个前端 mutation API 至少有一个 `frontend-action-flow` verification，证明真实用户 action 能触发 API/event 或按契约阻止触发。
- 每个用户可见 action 至少有一个 Action Route Render Verification，证明真实 action 落点 component/file 与契约一致；创建后 mode-specific action 必须有旧 mode 泄漏负向验证。
- 每个 mock acceptance / repo-specific acceptance runtime 交付物至少有一个 `mock-drift` verification，证明真实外部契约、mock 契约和 consumer 期望一致。
- 每个 no-cloud acceptance 核心流程至少有一个 `mock-composition` verification，证明真实被测 API/UI 组合链路通过 mock 外部依赖成立。
- Service-level API client/path/payload tests 不能替代 `frontend-action-flow`。
- Wizard final submit、modal confirm、批量操作 confirm、mode switch 后 submit 都必须单独验证，不能由页面截图或 step-level next validation 替代。
- Payload builder、API client、service fixture 和 mock service tests 不能替代 action route render proof。
- 带 action suffix 的 API，例如 `/resource:action`，必须验证不会被注册成 `/resource/:action` 或其他变体。
- 需要登录的 API 至少有未登录 smoke，预期为鉴权错误而不是 404；如可获得 token，再补 authenticated happy path。
- 每个 cloud/deployment/derived-configuration contract 至少有一个 representative fixture 或 runtime smoke。
- 每个新增/修改 mode 至少有一个 Mode Runtime Acceptance Gate，并包含 browser + API/runtime evidence；否则只能标记为 Not Run risk。
- 每个 mode-specific UI/事件/日志/Worker/Endpoint/Metrics 契约至少有一个正向或负向验证。
- 每个创建后 runtime capability 至少有一个 runtime-lifecycle 验证；支持运行时自动调节能力时必须有 auto-adjust-load 验证或明确 Not Run risk。
- 删除、更新部署配置、metrics、自动调节能力不能被“创建成功”验证覆盖。
- 每个用户可见 workflow 都必须标明是否进入 `product-acceptance-review`；如果不需要，写清原因。
- 如果无法验证，必须写 Risk，并进入 Not Run 候选。
- P0/P1 或 Blocks done 的 Not Run 不能进入 done，只能保持 blocked / risk-accepted-by-user 状态。

## 输出给 tasks.md 和 Atomic Issues

`atomic-task-planning` 必须把矩阵中的验证写入 `tasks.md` 索引，并展开到每个 `atomic-issues/Txxx.md`：

- Verification Commands
- 对应 task 的验证描述
- Not Run 风险表

Atomic Issue 中的验证必须使用以下格式：

```markdown
| Check | Command/manual step | Expected result | Proves | Failure meaning / Not Run risk |
|---|---|---|---|---|
```

要求：

- `Expected result` 必须具体，例如 HTTP status/body、DB row、grep no matches、rendered route visible、Terraform plan diff、metric/log label。
- `Proves` 必须说明该验证证明哪个 REQ/SCN/Contract/Migration。
- `Failure meaning / Not Run risk` 必须说明失败代表哪个契约或组合路径不成立；无法运行时写风险和 owner。
- 对 `api-route`，必须写 exact request、未登录/已登录预期、404 防回归含义。
- 对 manual/browser 验证，必须写可重复步骤和失败风险。

## 退出检查

- [ ] Semantic Consumption Matrix 覆盖所有 REQ/SCN/PDEC/DEC/C/MIG，无 blocked 或无理由 dropped 行。
- [ ] Verification Feasibility Gate 已确认 required verification 的环境/fixture/setup owner；不可用且 Blocks done 的项已阻塞完成。
- [ ] 已完成适用的 Local Audit Reports：Verification Consumption、Composition Proof、API DAG、Mock Drift、Action-Flow、Runtime Proof；无阻塞项。
- [ ] 所有 REQ/SCN 覆盖。
- [ ] Module Boundary Validation 风险已进入验证矩阵或 Not Run risk。
- [ ] 每个关键用户场景已有 Module Composition Verification，证明模块组合后满足需求。
- [ ] 每个 consumed contract 都能追溯到 provider contract 和验证。
- [ ] 所有 contracts 覆盖。
- [ ] 所有 migration actions 覆盖。
- [ ] 后端行为验证不是 compile-only；每个核心 backend contract 至少有 typed assertion、state assertion、error/warning assertion、event/progress assertion 或 API/path assertion。
- [ ] 前端调用的 API 均有最终 URL 的 `api-route` 验证。
- [ ] 前端 mutation API 均有 `frontend-action-flow` 验证；缺失时 Blocks done。
- [ ] 每个用户可见 action 均有 Action Route Render Verification，包含 source component、final route/API、router definition、landing component/file、mode/source state、expected rendered surface 和 forbidden inherited surface。
- [ ] 创建后 mode-specific action 已验证真实落点页面，不允许只靠 payload/API/mock 测试关闭。
- [ ] Wizard/modal/bulk/mode-switch submit flow 均验证了 action side effect、validation scope、success/failure feedback。
- [ ] Service-level fixture/path/payload 测试没有被用来替代 UI action-flow proof。
- [ ] 带 `:action` 或复杂 path 拼接的 API 有 404 防回归验证。
- [ ] 云资源、部署模式、派生配置有真实或拟真样本验证，未只依赖理想 mock。
- [ ] 新增/修改 mode 已有真实路径验收 gate，覆盖浏览器、API/runtime、进度事件、详情页和不支持能力展示。
- [ ] 已验证旧 mode 专属事件、文案、资源入口不会泄漏到新 mode，或已记录明确 Not Run risk。
- [ ] 创建后 runtime capability 已有 runtime-lifecycle 验证，删除清理、更新配置、指标链路和自动调节压力触发未被创建 smoke 替代。
- [ ] Stateful Behavior Matrix 的每条用户可达 transition、terminal 和 failure/blocked 状态都进入 Stateful Behavior Verification Gate；没有用一句 “run progress/event tests” 替代状态机覆盖。
- [ ] 用户可见 workflow 已标注是否需要 `product-acceptance-review`，且需要验收的场景已有验收 focus 和 evidence 预期。
- [ ] 没有“实现完成但不可证明”的行为。
- [ ] 未自动化验证有明确 manual step 和风险。
- [ ] Not Run 表包含 Source、Severity、Owner/approval、Blocks done；P0/P1 或 Blocks done 项没有被标成完成。
- [ ] 每条验证都能展开到至少一个 Atomic Issue。
- [ ] Atomic Issue 验证包含 expected result 和 proves，不只是命令。
- [ ] Atomic Issue 验证包含 failure meaning / Not Run risk。
- [ ] 已满足 artifact-completeness-spec Stage 8 的 Verification Matrix、Expected Result、Representative Fixture、Runtime Smoke、Not Run Risk artifact 要求。
- [ ] Verification Rubric 中所有 required verification 维度均达到 2 分，或有明确 Not Run risk。
