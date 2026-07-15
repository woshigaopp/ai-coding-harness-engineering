---
name: product-acceptance-review
description: 产品语义验收门禁。Use after implementation and deployment, before declaring an AutoMQ feature done, to use real browser/runtime evidence to find product semantic conflicts, mode leakage, state inconsistency, unsupported capability exposure, confusing configuration, and missing PRD/contract decisions; if issues are found, route them back to PRD/design/contracts/tasks before redeploying and re-verifying.
---

# Product Acceptance Review

## 定位

这是实现和部署后的产品语义验收阶段。它不替代单测、接口测试、E2E 或 `verification-matrix`；它专门发现“代码能跑但产品语义不自洽”的问题。

目标是回答：

> 用户从入口到创建、列表、详情、进度、日志、后续操作看到的是不是一个自洽产品？

本阶段必须在 `atomic-execution-sdd` 和部署 smoke 之后、宣布完成或进入 `convergence-retrospective` 之前执行。

## 必须输入

- `acceptance-context-pack.md` 或 `mock-acceptance.md#Acceptance Context Rehydration`，如果使用 contextpack workflow。
- PRD / `spec.md`
- AIP / engineering design，如果有
- Decision Registry
- Mode Difference Matrix，如果涉及 mode
- Frontend Contract
- Cross-module contracts
- Verification Matrix
- Atomic task verification log
- 已部署环境或本地可运行环境
- 可操作浏览器能力；远端部署按相关 deploy skill 执行，例如 `cmp-ec2-deploy` / `connect-test-deploy`

如果缺少 PRD、mode matrix、frontend contract 或 runtime environment，本阶段不能直接“凭感觉验收”；必须先记录 blocker 并回到对应阶段补齐。

如果使用 contextpack workflow，缺少 acceptance context pack 也必须 blocker。该 pack 必须证明：实际 diff 和 Atomic Issues 对齐、任务验证日志可追溯、运行产物 fresh、browser/API path 待验清单明确、mock/real boundary 已锁定、Not Run/cloud boundary 已记录。不能用“页面能打开”替代 context rehydration。

## Local Audit Gate: Acceptance Readiness Audit

开始浏览器验收前，主 agent 必须本地二次检查 PAR 输入和环境是否具备。该审计不能替代真实浏览器、submit-flow、runtime capability evidence。

输出：

```markdown
### PAR Readiness Local Audit Report

| Input/environment | Status | Finding | Required backflow | Blocks PAR |
|---|---|---|---|---:|
```

阻塞条件：

- 缺 PRD/spec、mode matrix、frontend contract、cross-module contract、verification matrix 或 runtime/browser environment 中任一必需项。
- 部署环境无法证明 branch/image/commit。
- 只能凭 API 或感觉验收，缺真实浏览器能力。

## 验收原则

1. 产品验收看用户语义，不只看接口是否 200。
2. 必须使用真实浏览器或等价 UI 运行环境；只用 API 不算完成。
3. 必须同时对照 PRD、契约、实际 UI、实际 API/runtime 状态。
4. 发现问题后不能只局部修代码；必须判断是 PRD 缺失、契约缺失、考古遗漏、实现偏差、验证缺失，回写到对应 artifact。
5. 修正后必须重新部署、重新执行相关 verification、重新产品验收。

## 输出位置

写入：

```text
specs/changes/<change-id>/acceptance/product-acceptance-review.md
```

并在 `plan.md`、`task-verification-log.yaml` 或 `execution-state.yaml` 中链接验收结果；不要把验收执行日志写回 sealed `tasks.md`。

如果当前没有 `specs/changes`，也要生成本地验收 Markdown，并在最终回复中指出路径。

## 必填产物

### 1. Acceptance Context

```markdown
| Item | Value |
|---|---|
| Environment |  |
| URL |  |
| Branch/image/commit |  |
| Browser used | yes/no |
| Login/user role |  |
| Feature object under review |  |
```

### 2. Product Semantic Matrix

```markdown
| Area | Expected product semantics | Actual behavior | Conflict? | Severity | Evidence |
|---|---|---|---|---|---|
```

必须覆盖：

- 入口和导航
- 创建表单
- 配置项和默认值
- 列表
- 详情
- Action landing：列表/详情/菜单 action 的真实 URL、landing component 和 mode-specific surface
- 创建/更新/删除进度
- 状态和错误
- 日志、Worker、Endpoint、Metrics、插件
- 权限和操作按钮
- 后续操作：更新、扩缩容、删除、失败恢复

### 3. Mode Semantic Checks

涉及 deployment/runtime/compute/storage/network mode 时必须输出：

```markdown
| Mode | Forbidden inherited behavior | Check | Expected | Actual | Pass? | Evidence |
|---|---|---|---|---|---|---|
```

规则：

- 新 mode 不得泄漏旧 mode 专属文案、事件、资源名或入口。
- 旧 mode 专属词汇或资源名，例如特定 orchestrator、容器、命名空间、服务账号等，默认禁止出现在新 mode，除非 PRD 明确说明复用旧运行时。
- 同级 mode 必须在 UI、事件、状态、日志、资源摘要上有各自语义。
- 不支持能力必须隐藏、禁用或显示 unavailable，不能像支持一样展示。

### 4. State Consistency Checks

```markdown
| State source | Observed value | Expected relation | Consistent? | Evidence |
|---|---|---|---|---|
| List page |  |  |  |  |
| Detail page |  |  |  |  |
| Progress/change page |  |  |  |  |
| API detail |  |  |  |  |
| API last-change/task |  |  |  |  |
| Runtime/cloud resource |  |  |  |  |
```

列表、详情、进度、API、任务、云资源状态不一致时，必须形成验收问题。除非 PRD 明确允许并给出用户可理解解释。

### 4.1 Runtime Capability Checks

当功能涉及部署模式、云资源、创建后操作、observability 或运行时自动调节能力，必须逐项验收运行时能力。不能因为创建成功就认为产品完成。

```markdown
| Capability | Expected semantics | Runtime action/evidence | UI/API evidence | Pass? | Issue if failed |
|---|---|---|---|---|---|
```

必须覆盖：

- 修改部署配置：入口必须进入当前 mode 的配置页，字段、默认值、禁用项和提交后事件符合契约。
- 删除：对象终态、云资源清理或残留资源表达、重复删除幂等符合契约。
- Metrics：CPU/Memory 等图表区分真实 0、空序列、query error 和采集未配置；不允许把采集失败展示成正常 0。
- 日志/Worker/Endpoint/插件：支持则能打开并有合理状态；不支持则隐藏、禁用或 unavailable。
- 自动调节能力：用 PRD/Verification Matrix 定义的 CPU 压力、内存压力、lag 或等价负载触发调节，并观察 desired/actual/status/event 变化。无法执行压测时必须记录 Not Run risk，不能判定通过。

### 4.2 Action Landing Checks

每个创建后用户 action 必须验证真实落点，防止“链接打开了旧 mode 页面”。

```markdown
| Action | Source page/object state | Expected route/component | Actual route/component | Expected visible surface | Forbidden inherited surface | Pass? | Evidence |
|---|---|---|---|---|---|---|---|
```

要求：

- 从真实详情页/列表页点击 action，不只直接打开 URL。
- 记录实际 URL、页面标题/关键字段、截图或 DOM 摘要。
- 对 mode-specific action，必须检查旧 mode 专属字段、文案、事件或资源名不出现，除非契约明确允许。
- 如果实际 route 正确但 landing component 内部仍渲染旧 mode surface，按 `frontend-contract-gap` 或 `implementation-bug` 分类，不得降级为链接问题。
- 如果无法使用浏览器点击，必须记录 PAR Not Run risk；API smoke 不能关闭本检查。

## Local Audit Gate: Product Semantic Evidence Audit

Product Semantic、Mode、State、Runtime Capability 和 Action Landing 检查完成后，主 agent 必须本地二次复核真实 evidence，并记录 severity 和冲突证据。

输出：

```markdown
### Product Semantic Local Audit Report

| Lane | User path inspected | Expected | Actual | Evidence | Finding | Root stage candidate | Blocks acceptance |
|---|---|---|---|---|---|---|---:|
```

默认 lanes：

- Action Landing auditor：从真实列表/详情点击 action，检查 route、component、mode surface 和 forbidden inherited UI。
- Runtime Capability auditor：检查更新、删除、metrics/logs/worker/endpoint/plugin、auto-adjust 的 UI/API/runtime evidence。
- State Consistency auditor：比较 list/detail/progress/API/task/runtime 状态。

阻塞条件：

- 无真实浏览器 evidence。
- 状态在 list/detail/progress/API/runtime 间冲突。
- 不支持能力仍展示为可用。
- action 落到旧 mode surface 或 landing component 内部泄漏旧 mode UI/API。

### 5. Issue Triage and Backflow

每个验收问题必须分类：

```markdown
| Issue ID | Symptom | Severity | Root stage | Required backflow | Artifact to update | Blocks acceptance? |
|---|---|---|---|---|---|---|
```

`Root stage` 只能使用：

- `prd-missing-decision`
- `decision-surface-discovery-miss`
- `aip-design-gap`
- `archaeology-missed-old-semantics`
- `frontend-contract-gap`
- `cross-module-contract-gap`
- `verification-gap`
- `implementation-bug`
- `deployment/runtime-data-gap`

`Required backflow` 必须写清：

- 回到 PRD 补产品决策
- 回到 Decision Surface Discovery 补 mode consumer、capability、frontend action、post-create consumer、persistent mutation 或 mock/playground surface，并重算 owner issue
- 回到 AIP/设计补工程决策
- 回到考古补旧语义/字段矩阵/mode audit
- 回到前端契约补 UI mode 决策
- 回到跨模块契约补状态/事件/API/任务契约
- 回到验证矩阵补验收或 runtime smoke
- 重新拆 atomic task
- 重新实现、部署、浏览器验收

## Local Audit Gate: Backflow Classification Audit

Issue Triage 完成后，主 agent 必须本地二次审计每个验收问题是否回流到最早缺失阶段，并标记分类不自洽和 artifact 失效缺口。不得只改代码或只更新最终报告。

输出：

```markdown
### Backflow Classification Local Audit Report

| Issue ID | Auditor root-stage finding | Missing invalidation | Verification rerun needed | Required artifact update | Blocks acceptance |
|---|---|---|---|---|---:|
```

阻塞条件：

- P0/P1/P2 block 未更新 Backflow Invalidation Matrix。
- `prd-missing-decision`、`frontend-contract-gap`、`cross-module-contract-gap` 或 `verification-gap` 只改代码。
- 受影响 DEC/C/T/VER 未 supersede 或 affected task 仍为 done。

## Local Audit Gate: Final PAR Exit Audit

声明 Accepted 前，主 agent 必须本地二次核对最终 PAR 是否满足退出规则。若任何实体证据缺失，仍必须 blocked。

输出：

```markdown
### Final PAR Local Exit Audit

| Exit item | Auditor verdict | Evidence | Missing action | Blocks Accepted |
|---|---|---|---|---:|
```

阻塞条件：

- P0/P1 未关闭。
- 新增/修改 mode 未做 Mode Semantic Checks。
- 创建后 runtime capability 未验。
- 无 browser evidence。
- 最终报告缺 evidence 或 Accepted 结论。

## 严重级别

| Severity | Definition | Acceptance |
|---|---|---|
| P0 | 核心路径不可用、数据破坏、安全/权限错误 | block |
| P1 | 产品语义冲突、mode 泄漏、状态不一致、错误恢复不可理解 | block |
| P2 | 次要入口语义不清、文案误导、非核心能力不可用但有替代 | usually block unless explicitly accepted |
| P3 | 轻微展示问题、不影响理解和操作 | non-blocking |

默认 P1：

- 新 mode 出现旧 mode 专属事件或文案。
- 用户看到的状态与 API/runtime 状态冲突。
- 不支持能力仍作为可用入口展示。
- 用户配置与实际生效配置不一致。
- 错误只暴露内部异常，用户无法知道恢复动作。

## 浏览器验收步骤

至少执行：

1. 登录真实环境。
2. 从导航进入功能入口。
3. 创建或打开一个真实对象。
4. 查看列表、详情、进度/change 页面。
5. 查看所有相关 tab/入口：配置、日志、Worker、Endpoint、Metrics、插件、操作按钮。
6. 对照 API/runtime/cloud 状态。
7. 保存截图、URL、API 摘要或 cloud 摘要作为 evidence。

如必须依赖远端部署，先使用对应 deploy skill 完成部署和 root smoke；再执行本 skill。

## automqbox / CMP Playground 验收

本节只适用于目标仓库或目标应用为 automqbox / CMP 的需求；其他项目不受本节约束。

当产品验收环境是 automqbox / CMP playground 时，必须把 playground 当作上线前验收环境，而不是 demo：

1. 必须从 packaged playground 或明确等价的 CMP 本地运行环境验收，并记录 branch、bundle、package、PID、port。
2. 必须覆盖 CMP 全局 top-level 入口 smoke：Instances、Connect Clusters、Connectors、Plugins、Accounts/Access、Support/Settings。某入口环境不可用时，记录 blocker 或 Not Run risk。
3. 必须覆盖受影响业务域完整生命周期：list、create/check、review/submit、progress/change、detail、update、delete、workers、metrics、logs、权限/错误、终态和重试。
4. 创建类需求必须从 UI 点击提交并进入 progress/change 或等价任务状态；progress 页面没有显示、状态不推进、状态和 API/detail/list 不一致，按 P1 blocker。
5. mock 数据、mock API、progress/change、workers/metrics/logs 必须能追溯到真实 CMP API/client、外部官方 API、真实 adapter/source、真实响应样例或 locked contract。
6. 不能只验改动页面；本需求未直接修改但可能受全局 shell、菜单、静态资源、权限、API client、mock handler 影响的 CMP 页面也要 smoke。

在进入人工产品语义判断前，必须先完成 playground handoff QA：

- root / target route 非白屏，DOM、shell、导航和目标入口真实渲染。
- CSS、JS、chunk、worker script 和核心 API 无 404/500/MIME 错误；`.js` 返回 `text/html` 或 console 出现 `Unexpected token '<'` 时不得继续验收。
- 浏览器 console 无阻断流程的 critical error。
- bundle/package/process freshness 已记录，运行环境确认为最后一次修复后的产物。
- 至少一个真实 UI submit-flow smoke 和创建类 progress/change smoke 已通过。

必须在 `product-acceptance-review.md` 输出：

```markdown
### CMP Playground Coverage Matrix

| CMP area/page | Required path | Expected source contract | Browser evidence | API/state evidence | Result | Blocker |
|---|---|---|---|---|---|---|
```

```markdown
### Playground Handoff QA

| Check | Evidence | Result | Blocks PAR |
|---|---|---|---:|
```

缺少该矩阵时，automqbox / CMP playground product acceptance 不得通过。

## 退出规则

- P0/P1 未关闭时，不得宣布产品验收完成。
- 新增/修改 mode 但未执行 Mode Semantic Checks，不得宣布完成。
- 没有真实浏览器 evidence，不得宣布完成。
- 涉及创建后 runtime capability 但未执行 Runtime Capability Checks，不得宣布完成。
- 任一适用 PAR Local Audit Report 缺失或存在 `Blocks PAR/acceptance/Accepted=yes` 项时，不得宣布完成。
- 声称支持运行时自动调节能力但没有压力触发或等价运行时证据，不得宣布该能力验收通过。
- automqbox / CMP playground 验收缺少 CMP 全局 top-level smoke、受影响域完整生命周期、UI submit-flow 或 progress/change evidence 时，不得宣布完成。
- automqbox / CMP playground handoff QA 缺失、白屏、静态资源错误、critical console error、stale bundle/package/process、或核心资源 `.js` 返回 `text/html` 时，不得宣布 ready、Accepted 或交付给用户验收。
- 发现 `prd-missing-decision`、`frontend-contract-gap`、`cross-module-contract-gap` 或 `verification-gap` 时，不得只改代码；必须先更新对应 artifact，再重新执行下游阶段。
- 修复后必须重新部署并重新验收受影响路径。
- 最终验收通过时，`product-acceptance-review.md` 必须包含 evidence 和 “Accepted” 结论。

## 工作流回流

发现问题后按最早缺失阶段回流：

```text
PRD/AIP decision gap
  -> update PRD/AIP + Decision Registry
  -> update archaeology/design/contracts
  -> update verification matrix
  -> update atomic issues/tasks
  -> implement
  -> deploy
  -> product acceptance again

Implementation bug only
  -> update task/verification if needed
  -> implement
  -> deploy
  -> product acceptance again
```

不能跳过中间 artifact，因为跳过会让后续实现继续基于旧决策收敛。

## 回流失效硬门禁

产品验收发现任何 P0/P1/P2 block 问题时，必须同步更新：

- `Backflow Invalidation Matrix`
- `Semantic Consumption Matrix`
- Decision Registry / 对应阶段决策文档
- Verification Matrix / Not Run Risk Table
- 受影响的 `atomic-issues/Txxx.md`、`task-dag.yaml` 状态和 `workflow-state.yaml.task_receipts` / execution log

要求：

- `prd-missing-decision` 必须使相关设计、契约、验证和 task 进入 `pending-rewrite`。
- `cross-module-contract-gap` 必须使 provider/consumer issue 和组合验证失效。
- `verification-gap` 必须使对应 VER 和 Atomic Issue Verification 失效。
- `frontend-contract-gap` 必须补 Action-To-Route-To-Component / Action Landing Checks，并使相关 UI issue 和验收 verification 失效。
- P0/P1 未关闭时必须撤销或禁止 done 状态。
- 修复后必须重跑受影响 verification、重新部署、重新产品验收。
