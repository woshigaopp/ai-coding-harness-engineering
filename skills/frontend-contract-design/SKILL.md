---
name: frontend-contract-design
description: 前端/UI 契约设计门禁。Use when a feature touches UI, frontend API clients, pages, forms, tables, routes, permissions, i18n, user-visible states, wizard/form submit flows, mode switches, or user actions that must trigger API calls or state changes, to replace vague natural-language UI requests with concrete page patterns, field/action/state/API contracts, user-flow proofs, and verification requirements.
---

# Frontend Contract Design

## 定位

前端自然语言描述容易模糊。本 skill 把 UI 微决策显式化，防止 AI 懒处理。

本阶段的核心不是“页面长什么样”，而是锁定用户意图闭包：

```text
User intent -> reachable UI state -> action enabled/disabled -> validation scope -> API/event side effect -> success/failure feedback -> next visible state
```

如果一个前端契约只描述字段展示、路由、文案或 API path，而没有证明用户可达动作会产生预期副作用，它是不完整的。

它应在 `atomic-task-planning` 前完成。

执行或评审本阶段时，必须按 `ai-dev-methodology/references/artifact-completeness-spec.md` 的 “Stage 6: Frontend Contract” 检查正交维度、Required Artifacts、Completeness Criteria 和 Exit Gate。

本阶段产生的布局参考、字段展示、交互、i18n、API 路径、用户动作副作用和浏览器验证决策，必须写入 `specs/changes/<change-id>/decision-reviews/frontend-decisions.md`，使用或等价满足 `ai-dev-methodology/templates/stage-decision-document.md`，并同步进入 Decision Registry。UI 决策不得改变 PRD 中锁定的用户可见语义；如需改变，回到 PRD。

## 输入

- 产品需求。
- AIP / spec / plan。
- `contract-context-pack.md` 或 `plan.md#Contract Context Rehydration`，如果使用 contextpack workflow。缺失或未包含旧代码事实、mode 差异、action route、模块边界、API/field contract candidates 时，阻塞本阶段。
- `decision-surface-discovery.md` 中的 frontend-action、mode-consumer、capability、post-create-consumer surface；缺失或未分配 owner stage 时阻塞本阶段。
- 参考页面、截图、设计稿或现有组件。
- API/字段契约。
- 表单库、wizard 框架、路由框架、请求库和权限框架的既有行为约束。

本阶段不得凭聊天记忆补 action route 或 mode-specific UI 语义。所有 visible action、route builder、router definition、landing component/file、mode branch、forbidden inherited UI/API 必须来自 `contract-context-pack.md`、code archaeology、当前 worktree evidence 或 locked contract，并写入后续 Frontend Action Route Coverage。

`decision-surface-discovery.md` 里的每个 frontend-action、capability、post-create-consumer surface 都必须被消费到本阶段的 `frontend-action-inventory.md`、`frontend-route-component-matrix.md`、`frontend-mode-field-display-matrix.md`、`frontend-form-state-matrix`、`frontend-mode-leakage-negative-matrix` 或 locked N/A。只写在 source/context pack 中不算消费成功。

## 必须选择参考源

至少提供一种：

- 参考页面/组件路径。
- 截图或设计稿。
- 明确的字段展示表和状态矩阵。
- 现有产品 pattern 名称。

没有参考源时，必须输出 open decision，不得让实现阶段自由设计。

如果需求涉及已有页面上的用户 action，参考源不能只写页面目录。必须消费 `code-archaeology-sdd` 的 `Frontend Action Route Trace`，或在本阶段补齐等价 trace。没有 trace 时不得锁定前端契约。

### Reference UI Pattern Gate

当需求、PRD、AIP、设计稿、用户描述或 source 中出现“参考某页面/组件”“参考 Instance 创建体验”“follow existing UI pattern”“和某页面一致”“像某现有功能”“复用现有组件/布局”等语义时，不能只把它解释成字段、selector 或 payload 语义。参考 UI 是独立契约，必须生成：

```text
frontend-reference-pattern-matrix.md
```

直接复制 `ai-dev-methodology/templates/frontend-reference-pattern-matrix.md`，保持列名不变：

```markdown
| Reference ID | Target surface/action | Reference source | Reference file/component | Must reuse/adapt | Must not inherit | Visual/layout obligation | Interaction/state obligation | Browser/visual proof | Owner issue |
|---|---|---|---|---|---|---|---|---|---|
```

要求：

- `Reference source` 写清来自 PRD/AIP/source 的哪句参考要求，例如“参考 Instance ASG 创建体验”。
- `Reference file/component` 必须是当前 worktree 内具体页面或组件文件，不能只写“Instance 创建页”或目录。
- `Must reuse/adapt` 必须列组件、布局、字段分组、控件类型、review summary、错误态或空态等可执行义务。
- `Must not inherit` 必须列参考页面中不适用于本需求的业务逻辑、字段、API、权限、文案或默认值，防止盲目复制。
- `Visual/layout obligation` 必须描述视觉/结构约束，例如 section 顺序、字段分组、控件排列、标题层级、review 分组、表格/详情展示模式。
- `Interaction/state obligation` 必须描述 loading、empty、error、reset、disabled、default、review 或 submit 状态如何对齐。
- `Browser/visual proof` 必须包含 browser/DOM/screenshot/trace 或等价视觉 proof；只检查 payload 不合格。
- `Owner issue` 必须指向具体前端 Atomic Issue。该行必须原样或等价复制到 owner packet 的 `reference_ui_patterns`，并进入 compiled issue 的 `Reference UI Pattern Obligations`。

如果参考源只被写在 Source Context、proposal/spec/plan、semantic carrier 或 `Existing Code References`，不算消费成功。没有 `frontend-reference-pattern-matrix.md` 或 owner packet 缺 `reference_ui_patterns` 时，不得进入 task planning / pre-execution。

### Local Audit Gate: Frontend Source And Trace Audit

选择参考源并消费 Action Route Trace 后，主 agent 必须本地二次审计前端契约的来源合法性。本地审计不做 UI 产品决策，只判断 reference/trace 是否足够支撑后续契约。

输出：

```markdown
### Frontend Source Local Audit Report

| Audit scope | Finding | Evidence | Required backflow | Blocks frontend contract |
|---|---|---|---|---:|
```

阻塞条件：

- 无参考源。
- 涉及已有 action 但未消费 Action Route Trace。
- `decision-surface-discovery.md` 中的 frontend-action / post-create-consumer surface 未进入前端矩阵或 locked N/A。
- 参考源只写目录，没有页面/组件/字段/状态证据。
- 参考旧 mode 行为但未说明哪些可继承、替换或禁用。

## 输出

本阶段不能只把前端契约散写在 `plan.md`。如果需求涉及 UI、页面、路由、表单、用户 action、mode switch 或浏览器验收，必须在 `specs/changes/<change-id>/` 下生成这些独立 artifact，并在 `plan.md` 建索引：

```text
frontend-page-inventory.md
frontend-action-inventory.md
frontend-route-component-matrix.md
frontend-reference-pattern-matrix.md   # 仅当 source/PRD/AIP/契约含参考现有 UI 信号时必需
frontend-mode-field-display-matrix.md
frontend-form-state-matrix.md
frontend-mode-leakage-negative-matrix.md
frontend-api-payload-contract-matrix.md   # 任一 action 提交 HTTP/API body 时必需
frontend-fixture-need-matrix.md
frontend-browser-verification-matrix.md
```

这些文件是 task planning 的 canonical input。`atomic-planning-context-pack.md` 必须逐项消费它们；前端 Atomic Issue packet 必须把对应内容复制进 `frontend_user_task`、`action_route_component`、`reference_ui_patterns`、`mode_field_display_matrix`、`form_state_matrix`、`mode_negative_assertions`、`api_payload_contract_matrix`、`fixture_needs`、`browser_verification` 和 `experience_rubric`。如果这些 artifact 缺失或没有被消费，前端任务不能进入 atomic execution。

创建这些文件时直接复制 `ai-dev-methodology/templates/frontend-*.md` 模板，尤其包括 `frontend-api-payload-contract-matrix.md`；保持文件名和列名不变。可以增加列，但不得删除模板列。模板列名会被 `workflowctl.py` 和 `validate_artifacts.py` 校验，并纳入 frontend-contract stage receipt 的 hash。

### 0. User Task Contract

先按用户动作定义前端闭包，再谈页面和组件。一个用户任务必须能回答：用户从哪里进入、看到什么、点什么、依赖什么数据、成功后去哪、失败在哪里看到反馈。

```markdown
| User task ID | User goal | Entry points | Page/route | Visible controls | Required data | Primary action | Loading/empty/error states | Success next state | Failure feedback | Owner issue |
|---|---|---|---|---|---|---|---|---|---|---|
```

要求：

- `User goal` 必须是用户要完成的工作，不是“实现某组件”。
- `Entry points` 必须包含导航、详情页按钮、列表行操作、wizard step、modal 入口等真实可达路径。
- `Visible controls` 必须列按钮、selector、radio、tab、toggle、输入框、确认弹窗，不得只写“表单”。
- `Required data` 必须列页面渲染和 action enabled 前需要加载的数据、fixture 和权限。
- `Primary action` 必须能映射到后续 Action-To-Route-To-Component 行。
- `Loading/empty/error states` 必须覆盖该用户任务的关键状态，不允许只写 happy path。
- `Owner issue` 必须是后续 Atomic Issue ID；未分配 owner 的用户任务不能宣称被实现。

### 1. 页面结构

```markdown
| Page/route | Purpose | Reference | Layout pattern |
|---|---|---|---|
```

### 1.1 Mode-specific UI 契约

当功能涉及 deployment/runtime/compute/storage/network mode，必须按 mode 展开 UI。不能让旧 mode 的页面、文案、事件、按钮、Tab 或空状态默认出现在新 mode 中。

```markdown
| UI area/page | Existing mode behavior | New mode behavior | Show/Hide/Disable/Unavailable | Empty/error text | Source of truth | Browser verification |
|---|---|---|---|---|---|---|
```

同时必须生成 `frontend-mode-leakage-negative-matrix.md`：

```markdown
| Surface/action | Mode/state | Forbidden DOM/text | Forbidden payload fields | Forbidden route/API | Assertion method | Owner issue |
|---|---|---|---|---|---|---|
```

必须覆盖：

- 创建表单：模式选择、规格、网络、权限、镜像/版本、容量、标签
- 列表和详情页：状态、资源摘要、endpoint、worker、插件、metrics
- 进度页/change tracking：每个 step 的 mode-specific 文案和顺序
- 日志页/日志入口：支持、隐藏、禁用或替代入口
- 操作按钮：更新部署配置、删除、扩缩容、重启、查看 worker
- 创建后页面：修改部署配置页面、删除确认与删除进度、失败恢复入口、自动调节状态和调节历史

规则：

- 旧 mode 专属文案或资源名，例如特定 orchestrator、容器、命名空间、服务账号等，不能出现在新 mode UI，除非该 mode 明确复用旧运行时。
- 同一个 UI 字段如果在不同 mode 下语义不同，必须拆成不同字段或不同 label；例如 Worker CPU/Mem resource spec 与 EC2 instance type 不得用一个“规格”混淆。
- 不支持能力必须有明确 UI 决策：隐藏、禁用并说明原因，或展示 unavailable 状态；不能保留可点击入口后运行时报错。
- 修改部署配置不能默认复用创建页或旧 mode 页面；必须证明字段语义、默认值、禁用项、提交 API 和后续事件都适配当前 mode。
- Metrics 图表展示 `0` 前必须能区分真实 0、空序列、query error 和采集未配置；采集不可用时按契约展示 unavailable/error，而不是误导为真实 0。
- 自动调节能力支持时必须有 UI 可观察证据：当前 min/max/desired/actual、触发状态或调节历史；不支持时不得展示为可配置能力。
- Mode-specific UI 契约必须引用 PRD Mode Difference Matrix 或 code archaeology Mode Semantic Inheritance Audit。

### 1.2 API Payload Exact-Shape Gate

凡是用户 action 会发出 HTTP/API body，必须生成 `frontend-api-payload-contract-matrix.md`。该表专门防止把 “active fields only / no forbidden payload” 写得太宽，导致同一语义通过两个结构双写。

```markdown
| Action ID | Mode/state | Method/path | Request body canonical path | Allowed keys | Forbidden keys / semantic aliases | Required/nullable/default/derived rule | Legacy compatibility rule | Network exact-key assertion | Owner issue |
|---|---|---|---|---|---|---|---|---|---|
```

要求：

- `Request body canonical path` 必须具体到嵌套路径，例如 `deploymentConfig.asg.resolvedConfig`、`workerSpec.asg.instanceType`，不能只写 `ASG deployment config`。
- `Allowed keys` 写该 path 下允许出现的 key 集合；如允许嵌套对象，必须说明嵌套对象的 key 来源。
- `Forbidden keys / semantic aliases` 必须列同义但禁止的字段，包括旧字段、raw id、camel/snake case 变体、inactive mode path、重复语义 path。
- `Legacy compatibility rule` 必须写明旧字段只在哪个 operation/mode 可用；如果前端新 UI 不应发送旧字段，写 `frontend must not send`。
- `Network exact-key assertion` 必须是浏览器/测试可执行断言，例如 `Object.keys(body.deploymentConfig.asg) === ["resolvedConfig"]`；只写“payload negative assertion”不合格。

阻塞条件：

- 有 `Side effect/API called` 但没有本表对应行。
- `Allowed keys` 或 `Forbidden keys` 为空且没有 locked N/A。
- 同一语义有两个传递路径但未指定 canonical path。
- browser verification 只断言 mode leakage，没有断言 same-mode forbidden aliases。

### Local Audit Gate: Mode-Specific UI Audit

Mode-specific UI 契约完成后，主 agent 必须本地二次 查旧 mode UI/API/文案/入口泄漏。

输出：

```markdown
### Mode UI Local Audit Report

| UI area/page | Finding | Forbidden inherited surface | Evidence | Required backflow | Blocks task planning |
|---|---|---|---|---|---:|
```

阻塞条件：

- 不支持能力仍可点击或显示为可用。
- 创建后操作默认复用旧页面但未证明 mode-specific render、validation 和 API 分支。
- 旧 mode 专属字段、事件、文案、资源名或 payload 分支未被禁止或验证。
- Metrics/日志/Worker/Endpoint 等入口缺 show/hide/disabled/unavailable 决策。

### 2. 字段展示契约

```markdown
| Field | Source of truth | Display label/i18n key | Format | Empty/unknown | Permission |
|---|---|---|---|---|---|
```

### 2.1 Mode Field Display Matrix

只写“详情页按 mode 展示”不合格。每个页面、tab、summary、配置区、表格列和 drawer 都必须按 mode 写清楚 must show / must hide。该表专门防止新 mode 详情页继续展示旧 mode 字段。

必须生成 `frontend-mode-field-display-matrix.md`：

```markdown
| Surface | Mode/state | Data source | Must show | Must hide | Label/i18n | Empty/error state | Fixture ref | Assertion | Owner issue |
|---|---|---|---|---|---|---|---|---|---|
```

要求：

- `Surface` 必须精确到页面区域，例如 `ConnectCluster detail / Config tab`、`detail action dropdown`、`update-config page / Deployment section`。
- `Mode/state` 必须写具体 mode、capacity、runtime/capability state，例如 `deploymentMode=asg`。
- `Must show` 必须列字段、文案、按钮、tab 或状态，例如 `instanceType, VPC, Subnet, Security Group, IAM Role, min/max worker count`。
- `Must hide` 必须列旧 mode 不得出现的字段、文案、按钮、tab、route 或 payload，例如 `namespace, serviceAccount, workerResourceSpec, K8s cluster, pod endpoint`。
- `Assertion` 必须包含 DOM/browser/fixture 断言，且必须有负向缺失断言；只写 screenshot 或人工看一下不合格。
- `Owner issue` 必须指向具体前端 Atomic Issue；未分配 owner 的字段展示契约阻塞 task planning。

如果需求涉及详情页、配置 tab、summary card、action dropdown、update-config、resize、workers/metrics/logs/progress 任一 UI surface，该表必填；不能只靠 `frontend-mode-leakage-negative-matrix.md` 的宽泛负向断言。

### 3. 交互契约

```markdown
| Action | User intent | Reachable from | Visible when | Enabled when | Validation scope | Side effect/API called | Success behavior | Failure behavior |
|---|---|---|---|---|---|---|---|---|
```

要求：

- 每个用户可见按钮、菜单项、wizard Next/Submit、批量操作、开关、模式切换、表格行操作都必须有一行。
- `Reachable from` 必须写清前置页面、step、tab、modal、mode、权限和数据状态。
- `Validation scope` 必须写当前 action 会校验哪些字段、哪些隐藏/非当前 mode 字段不得参与校验。
- `Side effect/API called` 必须写具体 HTTP method/path、路由跳转、状态写入、后台任务、轮询或无副作用。不能只写“调用创建接口”。
- `Success behavior` 必须包含用户可见反馈和下一个状态，例如 toast、跳转 progress/detail、列表刷新、modal 关闭。
- `Failure behavior` 必须包含字段级错误、表单级错误、toast、禁用原因或 unavailable 状态，不能是“无反应”。
- 如果 action 在当前 mode 下不支持，必须选择 hide、disable-with-reason 或 unavailable；不能保留可点击入口再依赖后端报错。

### 3.0 Action-To-Route-To-Component 契约

每个用户可见 action 必须在交互契约前或后补充真实落点映射。该表用于防止“需求写了某 mode 的 update page，但实现改错页面 / 验证测错页面”。

```markdown
| Action ID | Visible action / i18n key | Source component | Permission/visibility guard | Click handler / route builder | Final route/API | Router definition | Landing component/file | Mode branch required | Forbidden inherited UI/API | Verification | Owner issue |
|---|---|---|---|---|---|---|---|---|---|---|---|
```

该表必须落到 `frontend-route-component-matrix.md`。`frontend-action-inventory.md` 则保留完整用户意图和副作用：

```markdown
| Action ID | Action | User intent | Reachable from | Side effect/API called | Success behavior | Failure behavior | Owner issue |
|---|---|---|---|---|---|---|---|
```

要求：

- `Source component`、`Router definition`、`Landing component/file` 必须是具体文件路径。
- `Owner issue` 必须是具体 `Txxx`；同一个 `UI-ACT-*` 后续必须被同一个 packet 的 `action_route_component` 精确复制。
- `Final route/API` 必须是用户实际点击后的路径或 mutation API；不得只写“打开更新页”。
- `Mode branch required` 必须写 `none`、`by deploymentMode`、`by capacityType`、`by provider` 等具体条件。
- `Forbidden inherited UI/API` 必须列旧 mode 不得出现的页面、字段、文案、事件、payload 分支或默认值。
- 操作下拉、行操作、tab action 和创建后 action 必须逐项列出，不能用一个 “detail actions” 总结。
- 如果一个 action 是创建后操作（修改部署配置、扩缩容、删除、失败恢复、metrics/logs/workers、自动调节），必须证明落点页面和提交 API 都适配当前 mode。
- 如果 trace 与前端契约语义冲突，例如契约说新 mode update page 但真实点击落点是旧 mode-only component，必须记录 `frontend-contract-gap`，不得进入 atomic-task-planning。
- 任何 action 缺少此表中的 `Landing component/file` 或 `Verification`，其后续 Atomic Issue 只能标 `blocked-pending-action-route-trace`。
- 如果仓库使用文件路由、没有单独 router definition 文件，`Router definition` 必须写明 `file-based router; landing component owns route`，并仍然列出 landing component/file。
- `Source component`、`Click handler / route builder`、`Router definition`、`Landing component/file` 中出现的每个文件都必须进入 owner issue 的 `files_to_change` 或 `task-dag.yaml.files`；否则 task planning gate 会失败。

### 3.0.1 Frontend Surface Atomicity Gate

前端的“原子”不是目录层面的一个页面，也不是“前端 UX”一整个包。它必须按用户可达 surface 和 action-flow 拆。

强制拆分或显式 locked merge rationale：

- create wizard / create submit flow。
- detail summary/config tab display。
- detail action dropdown / row action / tab action。
- update deployment config route and form。
- resize/capacity route and form。
- progress/change tracking page。
- events/metrics/logs/workers tabs。
- mock/browser verification matrix owner。

默认规则：

- 一个 `UI-ACT-*` 至少对应一个 owner issue。
- 一个 owner issue 可以承载多个 action，只有在它们共享同一个 primary surface、同一个 form state、同一组 source/landing component、同一条 route/API 或同一条浏览器验证命令时才允许；否则必须拆。
- 如果某个 issue 同时写 create、detail、resize、progress、events，必须在 `task-planning-decisions.md` 和 owner packet 的 `atomicity_review.merge_rationale` 写强合并理由，证明这些 action 不能按 action-flow 拆。强理由只能是同一提交、同一路由/落点、同一状态写入、同一 browser proof 或拆开会破坏契约/编译；“同一页面/同一模块/相关工作/任务数少”不合格。
- 创建后 surface 是一等公民：详情页操作下拉、修改部署配置、resize、delete confirm、progress、events 不能靠 create flow smoke 关闭。
- build/lint/typecheck 只能证明 bundle 可构建，不能证明前端用户流程完成。
- 禁止用 “post-create consumers / frontend UX / detail consumers / 完整前端体验” 作为 owner issue 标题关闭多个 surface。这些只能是候选分组名，必须继续拆到 action-route-component、mode-field-display、form-state 或 browser-verification 的具体 owner。
- 如果 Action-To-Route-To-Component、Mode Field Display、Form State 或 Browser Verification 任一矩阵有多行归到同一个 owner issue，task planning 必须逐行复制到 packet 专用字段，并填写 `atomicity_review` 说明为什么仍是一个 closure；只出现在 Source Context、semantic carrier 或 implementation summary 不算消费成功。

### Local Audit Gate: Action Landing Audit

Action-To-Route-To-Component 表完成后，主 agent 必须本地二次 对每个 action 复核真实落点。该 gate 专门防止“原子任务实现了页面，但详情页链接仍指向旧页面”。

输出：

```markdown
### Action Landing Local Audit Report

| Action ID | Auditor verdict | Actual source component | Actual route/API | Actual landing component/file | Mode branch observed | Forbidden inherited surface found | Required contract/task update | Blocks task planning |
|---|---|---|---|---|---|---|---|---:|
```

阻塞条件：

- 缺 `Landing component/file`、`Router definition` 或 `Final route/API`。
- 前端契约与 code archaeology trace 冲突。
- 创建后 action 的真实落点是旧 mode-only surface。
- mode branch 或 forbidden inherited UI/API 没有验证要求。

### 3.1 User-Flow / Submit-Flow 契约

任何创建、更新、删除、绑定、启停、扩缩容、批量操作、导入导出、配置保存、模式切换后的提交，都必须补一张用户流程闭包表：

```markdown
| Flow | Steps user performs | Required data loaded before action | Fields submitted | Fields explicitly excluded | Expected API/event | Expected payload/params | Success state | Failure states | Verification |
|---|---|---|---|---|---|---|---|---|---|
```

强制规则：

- Wizard 不能只验证每一步 `Next`。必须验证最后 `Submit` 从真实页面状态触发预期 side effect。
- 表单不能只验证 payload builder。必须验证可见输入、隐藏字段、默认值、mode switch、权限和异步 option loading 组合后，最终 submit 仍然会调用 API 或显示字段级错误。
- 若使用 `react-hook-form`、Formik、Cloudscape Form、AutoMQWizard、Ant Design Form 等表单框架，必须写明 hidden/unmounted fields 的注册、unregister、reset、defaultValue、dirty/touched、full-form trigger 行为。
- mode-specific 表单必须显式列出 active fields 和 inactive fields；inactive fields 不得阻塞 submit，除非产品明确要求保留跨 mode 约束。
- 动态 selector 必须覆盖 options 未加载、空列表、加载失败、父字段切换后子字段 reset、已选值失效、默认值自动填充。
- “API client 测试能构造 payload”只能算 service-level proof；不能关闭 UI submit-flow proof。
- “浏览器页面能打开”只能算 display proof；不能关闭 submit-flow proof。
- 如果仓库缺少 DOM/browser 测试工具，必须记录 Not Run risk，并把真实浏览器 submit smoke 作为阻塞完成项。

如果该用户流程触发多接口后端链路，必须引用或生成后端 API Flow DAG 的入口节点、后续查询节点和终态节点。前端 user-flow verification 必须证明：

- 用户 action 触发 DAG 中预期的 mutation/read 节点。
- 提交 payload 中用于后续节点的数据能被后端返回或状态推进消费。
- 成功反馈、跳转、轮询、详情刷新对应 DAG 的后续节点。
- 失败展示对应 DAG 的 failure edge。
- terminal state 对应停止轮询、隐藏进度、禁用/启用后续操作等 UI 行为。

### Local Audit Gate: Submit Flow Closure Audit

User-Flow / Submit-Flow 契约完成后，主 agent 必须本地二次审计真实用户流程闭包。

输出：

```markdown
### Submit Flow Local Audit Report

| Flow | Auditor finding | Missing UI/action/API/feedback proof | Hidden field risk | Required backflow | Blocks task planning |
|---|---|---|---|---|---:|
```

阻塞条件：

- mutation flow 只有 payload builder/API client proof，没有真实 action side effect proof。
- wizard 只验证 step next，没有 final submit。
- hidden/inactive fields 是否参与校验不明。
- 成功/失败反馈、后续状态或轮询停止语义缺失。

### 3.2 表单字段闭包

对每个表单或 wizard step，必须输出：

```markdown
| Form/step | Mode/state | Active fields | Inactive/hidden fields | Default/reset rule | Validation trigger | Submit participation | Error location |
|---|---|---|---|---|---|---|---|
```

该表必须落到 `frontend-form-state-matrix.md`，并被前端 Atomic Issue packet 的 `form_state_matrix` 精确复制。只在源码里检查 payload builder，不足以关闭这个矩阵。

检查点：

- 字段可见不等于字段参与校验；字段隐藏不等于已取消注册。
- 条件渲染、tab 切换、accordion 折叠、modal 关闭、mode switch、duplicate/copy flow 都可能留下旧值或旧校验规则。
- 每个 conditional required 字段必须说明 required 条件、取消 required 条件、错误展示位置。
- 每个 derived/default 字段必须说明由前端填、后端推导、还是只读展示；不得让实现者临时猜。
- 每个用户可修改字段必须说明 source of truth：form state、component state、URL state、server response、global data 或 derived state。若同一字段有双 state，必须说明同步方向。

### 3.3 API 调用契约

当前端调用后端 API 时，必须锁定最终 HTTP 形态，不能只写“调用 match/list/create API”。

```markdown
| API purpose | Method | Final path pattern | Query/body | Frontend caller | Backend handler | Unauthenticated expected status | Verification |
|---|---|---|---|---|---|---|---|
```

要求：

- `Final path pattern` 必须是浏览器实际请求路径，例如 `/api/v1/<resource>:<action>`，不得只写 Controller base path 或自然语言名称。
- `Backend handler` 必须写到 Controller/class/method 或 OpenAPI operation。
- 对带冒号 action 的路径，必须明确冒号属于同一 path segment 还是下一段；例如 `/templates:match` 不等于 `/templates/:match`。
- 未登录/无权限态必须写清楚预期 HTTP status 和错误码，用于部署 smoke 判断路由是否存在。通常应是鉴权错误，而不是 404。
- 每个 API 必须标注它被哪个用户 action 触发。若 API 只出现在 service test，没有对应 action-flow，不能证明产品流程成立。
- 每个 mutation API 必须至少有一个 user-flow verification，证明真实 UI 能触发该 API 或按契约阻止触发。

### 4. 状态矩阵

```markdown
| State | Loading | Empty | Error | Disabled | User action |
|---|---|---|---|---|---|
```

状态矩阵必须覆盖：

- 页面数据加载前、加载中、加载失败、局部刷新、重试。
- 依赖数据缺失、权限不足、feature flag/capability 不支持。
- 提交中、防重复提交、提交成功、提交失败、后台任务进行中、任务失败、可重试。
- stale data：用户提交后列表/detail/progress 是否刷新，轮询何时停止，旧数据是否会误导用户。
- stale bundle/runtime：如果验收依赖后端静态资源或打包产物，必须说明如何确认运行环境加载的是最新前端 bundle。

### 5. i18n 契约

```markdown
| Text | Key pattern | File | Notes |
|---|---|---|---|
```

### 6. 验证

```markdown
| Scenario | User flow | Verification | Tool | Expected evidence | Blocks done |
|---|---|---|---|---|---:|
```

如果前端流程需要 mock/playground 验收，必须先生成 `frontend-fixture-need-matrix.md`，把页面需要的数据和 mock acceptance case 绑定起来：

```markdown
| Page/action | Fixture needed | State variant | Real contract source | Mock owner | Browser assertion | Negative assertion | Owner issue |
|---|---|---|---|---|---|---|---|
```

然后生成 `frontend-browser-verification-matrix.md`：

```markdown
| User task ID | Action ID | Browser steps | Network assertions | DOM assertions | Screenshot/trace | Negative assertions | Fixture refs | Blocks done |
|---|---|---|---|---|---|---|---|---:|
```

前端体验质量还必须给出轻量评分，避免“能编译但不好用”的任务被标 completed：

```markdown
| User task ID | Task clarity | Form ergonomics | State completeness | Error readability | Mode separation | Route/action closure | Design consistency | Responsive layout sanity | Required follow-up |
|---|---|---|---|---|---|---|---|---|---|
```

评分规则：`0` 阻塞进入 task planning；`1` 必须有 owner issue 和 Required follow-up；`2` 表示当前任务可以闭合。这个评分不是审美讨论，而是检查用户是否能完成动作、状态是否可理解、错误是否可恢复、页面是否和既有设计系统一致。

前端验证分层：

| Layer | 能证明 | 不能证明 |
|---|---|---|
| Type/API client test | path、类型、payload builder、fixture consumption | 用户真实点击能触发 API |
| Pure contract/helper test | 字段集合、mode active/inactive、状态转换纯逻辑 | DOM wiring、表单库注册行为、wizard submit |
| Component/DOM test | 可见输入、校验、按钮、API mock 调用 | 真实路由、真实 bundle、真实后端 filter |
| Browser/E2E/mock acceptance | 真实页面、路由、网络请求、跳转、错误反馈 | 真实云/外部 runtime 行为 |
| Runtime/product acceptance | 产品语义和真实环境一致性 | 单元级分支穷尽 |

必需通过覆盖：

- 每个 mutation user-flow 至少有 DOM/browser/mock acceptance proof；没有时 Blocks done。
- 每个 mode switch 至少有正向当前 mode 和负向旧 mode 泄漏检查。
- 每个 conditional validation 至少有“应阻止提交”和“不应阻止提交”两类检查。
- 每个 async selector 至少有成功、空、错误、父字段变化重置检查。
- 每个成功 mutation 至少证明 API request、payload、用户反馈、后续页面/状态。
- 每个失败 mutation 至少证明字段级或契约级错误展示，不能无反应。
- 每个页面如果由 jar/image/static bundle 提供，验收前必须证明 bundle/package/process freshness。

对每个 Action-To-Route-To-Component 行必须至少有一个验证：

- `route/component render proof`：直接打开或点击到 `Final route`，断言落点 component 按 mode 渲染正确页面。
- `negative inherited-mode proof`：断言旧 mode 专属字段/文案/API payload 分支不出现或不提交。
- `action side-effect proof`：如果 action 会 mutation，断言真实页面 action 触发预期 API/event 或字段级错误。

Payload builder 或 service-level API 测试只能补充 `action side-effect proof`，不能替代 route/component render proof。

### Local Audit Gate: Frontend Verification Sufficiency Audit

前端验证表完成后，主 agent 必须本地二次审计验证是否足以证明用户意图闭包。

输出：

```markdown
### Frontend Verification Local Audit Report

| Scenario/action | Claimed proof | Auditor finding | Missing proof | Required verification/backflow | Blocks done |
|---|---|---|---|---|---:|
```

阻塞条件：

- mutation user-flow 无 DOM/browser/mock acceptance proof 且未 `Blocks done`。
- service-level proof 被用于关闭 UI user-flow。
- route/component render proof 或 negative inherited-mode proof 缺失。
- bundle/package/process freshness 未定义但验收依赖打包静态资源。

## 任务拆分要求

任务规划必须把本阶段七个矩阵作为输入，而不是让实现者临场读整份 PRD 重新理解前端。映射关系如下：

| Frontend contract artifact | Must appear in Atomic Issue packet |
|---|---|
| `frontend-page-inventory.md` | `frontend_user_task.entry_points` / `files_to_change` / `existing_code_references` |
| `frontend-action-inventory.md` | `frontend_user_task.primary_action` / `action_route_component` / `behavior_details` |
| `frontend-route-component-matrix.md` | `action_route_component` / `implementation_steps` / `verification` |
| `frontend-mode-field-display-matrix.md` | `mode_field_display_matrix` / `mode_negative_assertions` / `browser_verification.dom_assertions` |
| `frontend-form-state-matrix.md` | `form_state_matrix` / `semantic_carriers` / `prohibited_changes` |
| `frontend-mode-leakage-negative-matrix.md` | `mode_negative_assertions` / `browser_verification.negative_assertions` |
| `frontend-api-payload-contract-matrix.md` | `api_payload_contract_matrix` / `browser_verification.network_assertions` / exact-key negative assertions |
| `frontend-fixture-need-matrix.md` | `fixture_needs` / mock acceptance cases |
| `frontend-browser-verification-matrix.md` | `browser_verification` / `done_criteria` |

缺任一适用矩阵，或矩阵没有复制进 packet，前端 Atomic Issue 只能标 `blocked-pending-frontend-contract`。

矩阵消费必须是 row-level + section-scoped。也就是每一行必须进入 owner issue 的专用执行字段，不能只出现在 `Source Context`、`semantic_carriers`、source excerpt、implementation summary 或泛化步骤里：

- `frontend-route-component-matrix.md` 的每个 `UI-ACT-*` 行必须进入同一 owner packet 的 `action_route_component`。
- `frontend-mode-field-display-matrix.md` 的每个 `Surface + Must show + Must hide + Assertion` 必须进入 `mode_field_display_matrix`。
- `frontend-form-state-matrix.md` 的每个 `Form/step + active fields + inactive/hidden fields + validation trigger + submit participation` 必须进入 `form_state_matrix`。
- `frontend-mode-leakage-negative-matrix.md` 的每个 `Surface/action + forbidden DOM/text + forbidden payload fields + forbidden route/API + assertion method` 必须进入 `mode_negative_assertions` 和 `browser_verification.negative_assertions`。
- `frontend-api-payload-contract-matrix.md` 的每个 `Action ID + Method/path + canonical path + allowed keys + forbidden aliases + exact-key assertion` 必须进入 `api_payload_contract_matrix` 和 `browser_verification.network_assertions`。只在 mode leakage negative 中写 payload forbidden 不算 exact-shape proof。
- `frontend-browser-verification-matrix.md` 的每个 `Action ID + browser steps + network assertions + DOM assertions + screenshot/trace` 必须进入 `browser_verification`。

这条规则的目的不是让 issue 变长，而是防止 task planning 把“完整前端矩阵”压缩成“实现前端 UX”这种不可执行摘要。执行者必须从单个 Txxx packet 直接看到每个用户动作、页面区域、隐藏字段、负向断言和浏览器证明，不需要回读前端矩阵才能知道要做什么。

前端任务必须拆分为：

1. API client/types
2. route/page shell
3. data binding
4. visual layout
5. i18n
6. permissions/actions
7. loading/empty/error states
8. form/action-flow contract
9. browser/mock acceptance verification

拆分规则：

- API client/types 任务不能声明用户流程完成。
- UI 任务不能只以 build、lint、typecheck、payload builder 或截图作为完成标准；涉及 mutation 时必须消费 submit-flow verification。
- Browser/mock acceptance 可以单独成 verification task，但它的 blocker 必须回压到提供该 action 的 UI task；未通过前 UI/form issue 只能标 `implemented-pending-action-flow`，不能标 passed/completed。
- 如果生成 Atomic Issue 时发现某个用户 action 没有 side-effect contract 或 verification，必须回流到本 skill，不能让实现阶段补。

## 退出检查

- [ ] 有参考源。
- [ ] 已生成 `frontend-page-inventory.md`、`frontend-action-inventory.md`、`frontend-route-component-matrix.md`、`frontend-mode-field-display-matrix.md`、`frontend-form-state-matrix.md`、`frontend-mode-leakage-negative-matrix.md`、`frontend-api-payload-contract-matrix.md`、`frontend-fixture-need-matrix.md`、`frontend-browser-verification-matrix.md`，或逐项记录 N/A 原因。
- [ ] 已生成 User Task Contract，并且每个用户任务都有 Owner issue 或 blocked reason。
- [ ] 涉及 mode 时，已产出 Mode-specific UI 契约，且每个页面区域都有 show/hide/disable/unavailable 决策。
- [ ] 旧 mode 专属文案、事件和资源名没有默认泄漏到新 mode UI。
- [ ] 同名但不同语义的配置字段已拆分或明确 mode-specific label。
- [ ] 日志、Worker、Endpoint、Metrics、插件验证等入口在每个 mode 下都有 UI 决策。
- [ ] 修改部署配置、删除、失败恢复、自动调节这些创建后操作都有 mode-specific UI 契约，未默认复用旧 mode 页面。
- [ ] Metrics 的 0/empty/query error/unavailable 展示语义明确。
- [ ] 字段 source of truth 明确。
- [ ] 每个用户可见 action 都有 User intent、Reachable from、Validation scope、Side effect、Success behavior、Failure behavior。
- [ ] 每个用户可见 action 都有 Action-To-Route-To-Component 映射，包含 visible action、source component、route builder、router definition、landing component/file、mode branch 和 forbidden inherited UI/API。
- [ ] 创建后操作没有默认复用旧 mode 页面；若复用，已证明落点 component 内部有 mode-specific render、validation 和 API 分支。
- [ ] 每个 create/update/delete/save/submit/scale/bind/import/export flow 都有 User-Flow / Submit-Flow 契约。
- [ ] 每个 wizard final submit 都证明会触发预期 API/event，或显示字段级/契约级错误。
- [ ] 每个 mode-specific 表单都有 active fields、inactive fields、default/reset、validation trigger、submit participation。
- [ ] hidden/unmounted/disabled fields 的注册、unregister、reset 和 full-form validation 行为已明确。
- [ ] 每个 conditional required 字段都有阻止提交和不阻止提交两类验证要求。
- [ ] 每个 async selector 覆盖 options 未加载、空、错误、父字段切换、已选值失效。
- [ ] 每个前端 API 调用有最终 HTTP method/path/query/body 契约。
- [ ] 每个前端 API 调用映射到后端 handler 或 OpenAPI operation。
- [ ] 每个 mutation API 都映射到至少一个真实用户 action-flow。
- [ ] 带 action suffix 的路径已区分 `/resource:action` 与 `/resource/:action`。
- [ ] 未登录/无权限态的预期 status/error 已用于验证路由存在性。
- [ ] unknown/null/empty 展示明确。
- [ ] 权限、路由、操作按钮明确。
- [ ] i18n key 和文件明确。
- [ ] 有浏览器/DOM/mock acceptance 验证要求，且区分 service-level proof 与 user-flow proof。
- [ ] mutation user-flow 没有 DOM/browser proof 时，已记录 Blocks done Not Run risk。
- [ ] 如果验收使用 jar/image/static bundle，已要求 bundle/package/process freshness 证明。
- [ ] 已完成适用的 Local Audit Reports：Frontend Source、Mode UI、Action Landing、Submit Flow、Frontend Verification；无阻塞项。
- [ ] `atomic-planning-context-pack.md` 会消费全部前端矩阵，并把它们映射到前端 Atomic Issue packet 的专用字段。
- [ ] 前端 Atomic Issue 的 browser verification 包含 browser steps、network assertions、DOM assertions、screenshot/trace、negative assertions 和 failure meaning。
- [ ] 已满足 artifact-completeness-spec Stage 6 的 Page Structure、Field Display、Interaction、State、i18n、API Call、Browser Verification artifact 要求。
