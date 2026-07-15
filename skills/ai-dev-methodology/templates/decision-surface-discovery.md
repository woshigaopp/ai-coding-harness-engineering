# Decision Surface Discovery

用于在锁定 PRD/AIP/契约和生成 Atomic Issue 前，强制发现“这里是否存在必须决策的点”。它不是最终设计，也不是实现计划；它是决策面清单和下游 owner 分配表。

触发条件：

- 新增或修改 deployment/runtime/compute/storage/network mode。
- 新增或修改对象生命周期、创建后能力、外部依赖、mock acceptance / repo-specific acceptance runtime 验收。
- 新增 create/update/delete/resize/save/scale/import/bind 等 mutation。
- create/update/edit/save/resize/delete/recreate/migrate 复用同一对象、同一 config 或同一 readback 字段。
- 出现 auto-create、default-created、generated resource、managed resource、select-existing、existing resource 等外部资源归属语义。
- 用户只给 purpose / 目标描述，未逐项定义页面、能力、下游消费者和验收组合。

## Decision Surface Inventory

| Surface ID | Trigger source | Surface type | Object/capability/action | Why this is a decision surface | Current evidence | Required decision | Decision owner stage | Blocks next stage |
|---|---|---|---|---|---|---|---|---:|

`Surface type` 可选：`mode-consumer`、`capability`、`frontend-action`、`post-create-consumer`、`persistent-mutation`、`operation-mutability`、`managed-resource-ownership`、`runtime-lifecycle`、`runtime-mode-materialization-parity`、`mock-acceptance-runtime`、`observability`、`permission`、`compatibility`。

规则：

- 不能只写 “mode-specific / support ASG / update UI”。必须写清楚这个 surface 会让谁做选择。
- `Required decision` 必须是可回答的问题，例如“ASG 下 logs 是实现、隐藏、禁用还是 unavailable？”。
- `Decision owner stage` 必须是 PRD、AIP、readiness、design、archaeology、migration、frontend-contract、cross-module-contract、verification 或 task-planning 之一。

## Generative Surface Stress Tests

本节用于从当前需求生成经验库未覆盖的 candidate surface。大需求、高风险 surface、purpose-only 输入或会改变 API/状态/资源/runtime/mock/用户可见语义的需求必须运行本节压力测试；低风险、局部无状态或纯文案类改动可用 `locked-n/a` 关闭不适用的 test type，但必须说明原因。不能只写“已检查 / 不适用”；每条有效压力测试必须写出 path trace、旧假设断点、provider/consumer/mock owner、negative assertion 和 verification。发现的 candidate surface 必须进入 `Decision Surface Inventory`，并在 `Surface Obligation Projection Matrix` 中展开；不能停留在本节。

| Stress ID | Test type | Scenario / mutation / invariant / acceptance proof | Path trace | Broken or uncertain assumption | Candidate decision surface | Required decision | Production provider owner anchor | Consumer owner anchor | Mock / acceptance owner anchor | Negative assertion | Verification / exact assertion | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

`Test type` 可选：

- `consumer-enumeration`
- `mutation-chain`
- `invariant-breakage`
- `lifecycle-completeness`
- `reverse-acceptance`

强制问题：

- `consumer-enumeration`：列出 list/detail/progress/logs/metrics/workers/endpoints/plugins/connectors/update/delete/retry/permission/mock/acceptance/observability 等仍会读取、展示、操作或验证新对象/新 mode 的 consumer。每个 consumer 必须有 path trace，例如 `page -> API -> controller -> service -> runtime/provider`。
- `mutation-chain`：按 `before -> mutation -> after -> readback -> later action -> cleanup` 追问 writer、authoritative state owner、readback consumer、later action 依赖、cleanup/protect、partial failure/residual state。
- `invariant-breakage`：写出旧系统默认总为真的假设，以及新需求为什么让它可能不成立。例如字段总存在、资源总由用户提供、创建成功等于 runtime ready、所有 mode 共用页面、API 总能返回完整 runtime state。
- `lifecycle-completeness`：对产品对象、运行时对象、外部资源、配置对象或用户可见实体覆盖 `create/read/update/operate/observe/fail/delete`。回答不上来时生成 candidate surface，而不是直接补实现。
- `reverse-acceptance`：从“如何证明需求完成”倒推 contract、external side effect、frontend action、mock/no-cloud boundary、Not Run risk 或 repo-specific acceptance runtime surface。

规则：

- `Path trace` 必须包含至少一个具体代码或产品锚点：页面/route/component、API path、controller/service/task class、provider/operator/client method、DB/entity/field、runtime writer、mock handler/fixture/simulator。没有 path trace 的压力测试只是摘要，不算发现；如果当前阶段还没有足够 code scope evidence，`Status` 必须是 `blocked-needs-code-scope`，不得用猜测的 class/API/path 补齐。
- `Broken or uncertain assumption` 不能为空。若没有旧假设被打破，必须说明为什么该 stress row locked N/A。
- `Production provider owner anchor` 和 `Consumer owner anchor` 必须分开。consumer 不能替代 provider；frontend 不能关闭 backend/API/runtime/provider 能力。
- `Negative assertion` 必须说明要防止的错误继承、内部异常、fake state、错误 provider context、mock/real route 漂移或过度产品承诺。
- `Status` 只能是 `candidate-surface-created`、`locked-n/a`、`blocked-needs-code-scope`、`blocked-needs-human-decision`、`blocked-backflow`。`checked`、`covered`、`done` 不是合法状态。`locked-n/a` 必须写清为什么该 test type 不适用，不能只有 `N/A`。

## Mode Consumer Matrix

新增或修改 mode 时必填。

| Consumer ID | Consumer surface/module | User/API entry | Current old-mode assumption | New mode expected behavior | Support status | If unsupported/unavailable | Required contract | Owner issue | Verification |
|---|---|---|---|---|---|---|---|---|---|

必须覆盖：

- create/check/review/submit。
- list/detail/config/capacity/progress/events。
- update-config/resize/delete/retry/failure recovery。
- workers/logs/metrics/endpoints/plugins/connectors。
- backend API/service/task/runtime/repository。
- frontend route/action/component/API client。
- mock acceptance fixtures and repo-specific packaged/runtime acceptance.

`Support status` 只能是 `supported`、`mode-specific-implementation-required`、`hidden`、`disabled-with-reason`、`unavailable-with-reason`、`not-applicable`、`needs-decision`。`needs-decision` 阻塞。

## Capability Support Matrix

所有用户可见能力必须逐 mode 决策，不能默认继承。

| Capability | Mode/variant | Supported? | Product behavior | Backend/API behavior | Frontend behavior | Runtime/mock behavior | Failure/unavailable reason | Owner issue | Verification |
|---|---|---:|---|---|---|---|---|---|---|

能力包括但不限于：create、check、update-config、resize、worker-spec update、delete、workers、logs、metrics、endpoint、connector create/status、events、autoscaling decision、permission-gated actions。

## Post-Create Consumer Audit

创建类需求必填。创建成功不是终点；必须审计创建后的所有消费者。

| Created object | Consumer | Consumption path | Old assumption consumed | New object state required | Decision | Contract/verification | Owner issue | If omitted failure |
|---|---|---|---|---|---|---|---|---|

规则：

- 如果新对象能被列表/详情/connector/logs/metrics/workers/update/delete/progress/event 消费，每个 consumer 都必须有行。
- 如果 consumer 不支持新对象，必须锁定 hidden/disabled/unavailable，而不是让运行时报错。
- consumer 行不能只停在 Source Context；必须进入对应 `C-xxx`、`VER-xxx` 和 owner Atomic Issue。

## Frontend Action Surface Graph

前端用户 action 必填；详表仍由 `frontend-route-component-matrix.md` 承载。

| Action surface | Source page/component | Visible action | Mode/state | Expected route/API | Landing/component | Forbidden inherited route/API/UI | Decision needed | Owner issue | Verification |
|---|---|---|---|---|---|---|---|---|---|

规则：

- 操作下拉、行操作、tab action、wizard submit、创建后 action 必须逐项列出。
- 旧 mode 页面或旧 mode-only component 不能作为新 mode 默认落点，除非有 locked evidence。

## Managed Resource Ownership Matrix

外部资源出现 auto-create / default-created / generated / managed / select-existing / existing 语义时必填。它和 selector 矩阵不同；selector 只回答如何选，ownership 矩阵回答是否真实创建、谁拥有、谁清理。

| Resource row ID | Resource | Selection mode | Create timing | Provider writer | Resource identity | Provenance state owner | Runtime/readback consumers | Update rule | Delete cleanup/protect rule | Failure/idempotency behavior | Contract/verification | Owner issue |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

规则：

- `Provider writer` 必须是真实生产路径会调用的 provider/API/operator/resource writer；不能写 mock/no-cloud handler。
- `Provenance state owner` 必须说明 owned/existing/generated/derived 如何持久化或可读回。
- `Delete cleanup/protect rule` 必须同时覆盖 owned resource cleanup 和 existing resource protect。
- 如果资源只选择已有且不创建，也必须写 locked N/A，并说明 update/delete 时如何保护。
- 只写在 Source Context、selector 字段或 resolved config 中不算消费成功。

## Operation Mutability Matrix

已有对象出现 update/edit/save/resize/delete/recreate/migrate，或 create-time config/readback 字段出现在后续操作入口时必填。创建时需要配置的字段，不等于运行后可以在普通更新入口修改；每个字段必须先决策产品语义。

| Mutability row ID | Field / config path | Operation | Create-time meaning | Runtime owner after create | Update action required | Product semantic | Recommendation | Reason | Backend owner or locked N/A | UI expression | Verification / negative assertion |
|---|---|---|---|---|---|---|---|---|---|---|---|

规则：

- `Recommendation` 只能是 `editable`、`read-only`、`hidden`、`disabled`、`unsupported`、`recreate-required`、`migrate-required` 或 `needs-decision`；`needs-decision` 阻塞。
- 如果修改字段需要 delete+create 核心运行时资源、替换外部资源边界或迁移数据/流量，必须把它作为产品决策暴露出来，不得默认归入普通 update。
- 若允许修改，`Backend owner or locked N/A` 必须列出 controller/service/task/provider owner；若没有 owner，frontend 不能提供可提交控件。
- 若字段只读、禁用、隐藏、unsupported、recreate-required 或 migrate-required，必须定义用户/API 看到什么、UI 如何表达、mock/product acceptance 如何证明不是内部异常或静默失败。
- frontend exact-key payload 只能证明已锁定决策被正确消费，不能替代字段级 mutability decision。

## Surface Obligation Projection Matrix

本表把抽象 surface 展开成最小可执行义务。`Owner Assignment Gate` 只能引用本表的 `Expanded obligation ID`，不能用粗 `Surface ID` 直接关闭。

| Surface ID | Expanded obligation ID | Mode / variant | Capability / consumer | Operation surface | Production provider owner anchor | Consumer owner anchor | Mock / acceptance owner anchor | Required decision | Contract / obligation | Verification / exact assertion | Negative assertion | Owner Txxx or locked N/A | Closure status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

规则：

- `Production provider owner anchor` 必须是具体生产锚点：API path、controller/service/task class、provider/operator/client method、DB/entity/field、runtime writer、frontend route/component/API client 中的真实 owner。只写 `backend`、`runtime`、模块名、阶段名或 `Txxx` 不合格。
- `Consumer owner anchor` 必须写消费方具体锚点。frontend、progress/event、mock/acceptance consumer 不能替代 production provider owner。
- `Mock / acceptance owner anchor` 必须写 mock handler、fixture file、simulator、adapter evidence、packaged case，或 locked N/A。mock row 不能关闭 production side effect。
- `Verification / exact assertion` 必须能被执行或审查打脸：命令、测试类、browser network/DOM assertion、API response shape、fixture evidence、provider call/readback assertion。只写 “covered by tests” 不合格。
- `Negative assertion` 必填，证明不会继承旧 mode、内部异常、假状态、错误 provider context、fake readback 或 mock/real route 漂移。
- `Closure status` 只能是 `locked-decision`、`contracted`、`verified-owner-planned`、`locked-n/a`、`blocked-backflow`。`covered`、`done`、`handled`、`mode-aware` 不是合法关闭状态。
- 下列词不能单独关闭行：`mode-aware`、`support`、`handle`、`stable shape`、`runtime tabs`、`baseline`、`readback`、`mock coverage`、`selector`、`managed resource`、`provider proof`、`mode-specific`。它们必须绑定具体对象、owner anchor、错误语义和验证断言。

强制展开规则：

- `post-create-consumer` / `runtime tabs`：按 `consumer capability × mode × backend/API provider owner × frontend/API consumer × mock fixture × unsupported/unavailable decision` 展开。`workers`、`logs`、`metrics`、`endpoints`、`plugins`、`connectors`、`events` 不能合成一行关闭。
- `managed-resource-ownership`：按 `resource × selection mode × provider writer × identity/provenance persistence × runtime/readback consumer × cleanup/protect × failure/idempotency` 展开。selector/UI 行不能关闭 provider create/delete/protect。
- `baseline` / `default`：拆成具体 baseline kind，例如 deploy trust/profile、runtime permission policy、connector-specific permission；每类必须有 decision、owner、verification 或 blocked。
- user-visible `event/progress/change`：必须写 `event_purpose`，区分 policy materialization、decision record、runtime activity、failure/prevented record，并证明 UI 文案不超过证据层级。
- browser selector / option API：按 `selector API × controller route × provider context source × configured fixture ID × real-vs-mock route` 展开，并包含 query/body negative assertion。
- `operation-mutability`：按 `field × operation × product semantic × backend mutation owner × UI expression × verification` 展开。create-time 字段不能默认 update-time mutable；每个字段必须有 editable/read-only/hidden/disabled/unsupported/recreate-required/migrate-required 决策或 blocked。
- handoff / acceptance command：按 exact command、toolchain/runtime、executed status、expected assertion 展开；未执行必须标 `not_run_disclosed`，不能暗示已验证。

## Owner Assignment Gate

| Surface ID | Derived decision/contract/verification | Owner issue | Copied into packet section | Execution obligation | Pass-task evidence required | Status |
|---|---|---|---|---|---|---|

规则：

- `Derived decision/contract/verification` 必须引用 `Surface Obligation Projection Matrix` 的 `Expanded obligation ID`，不能只引用 `DS-xxx`。
- PRD/readiness/design 阶段只有在 owner stage 是未来阶段时，才允许 `Owner issue` 写 `pending task-planning`，但必须写清 `Execution obligation`。如果当前阶段就是该 surface 的 owner stage，本阶段签收前必须关闭为 locked decision、C/VER、blocked backflow 或 locked N/A，不能继续 pending/routed。
- task-planning/pre-execution 阶段每个 `Surface ID` 必须有具体 owner issue `Txxx`，或 locked N/A。
- `Copied into packet section` 必须指向执行层字段，例如 `behavior_details`、`provided_contract_obligations`、`action_route_component`、`mode_field_display_matrix`、`backend_behavior_verification`、`browser_verification`、`persistent_mutation_proofs`。
- `managed-resource-ownership` surface 必须复制到 `behavior_details`、`provided_contract_obligations`、`backend_behavior_verification`、`persistent_mutation_proofs` 或专用 `managed_resource_ownership` packet section；只复制到 selector/UI section 不算关闭。
- `operation-mutability` surface 必须复制到 `behavior_details`、`form_state_matrix`、`mode_field_display_matrix`、`backend_behavior_verification`、`browser_verification` 或专用 `operation_mutability` packet section；只证明 active branch payload 或 route 存在不算关闭。
- 只出现在 source excerpt、context pack、appendix 或全局 plan 中不算消费成功。
- owner issue 未验证该 surface 时，`pass-task` 不得通过；验收失败必须回流到对应 surface 行。
