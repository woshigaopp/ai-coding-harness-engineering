# External Capability Research

用于在 PRD 已明确“要做什么”之后、AIP/design 锁定“怎么做”之前，调研外部系统、官方 API、云资源、运行时机制和第三方依赖的真实能力边界。

它不是产品需求，也不是代码考古：

- PRD 回答用户要什么。
- External Capability Research 回答外部系统真实允许什么、限制什么、失败时怎样表现。
- AIP/design 基于这些事实选择 AutoMQ 怎么做。
- Code Archaeology 回答当前仓库已经怎么做。

触发条件：

- 新增或修改云资源、K8s/Helm/Terraform/IAM/network/storage/compute/runtime 能力。
- 新增外部 SDK/API/第三方系统、官方协议、外部运行时、自动伸缩、调度、生命周期、指标/日志/事件依赖。
- 新增 mock acceptance / repo-specific acceptance runtime 需要模拟的外部依赖。
- AIP/design 中出现 “复用外部能力 / provider 支持 / runtime 支持 / 官方限制 / SDK 行为 / 云资源默认值 / autoscaling / scheduling / lifecycle” 等语义。

## Research Source Inventory

| Source ID | System/provider | Source type | URL/path/command | Official? | Version/date | Read status | Used for | Confidence |
|---|---|---|---|---:|---|---|---|---|

规则：

- 优先官方文档、SDK/API reference、标准规范、当前 adapter/source、真实响应样例。
- 博客、问答、非官方示例只能作为辅助，不得单独支撑 ADEC/C/VER。
- 外部事实可能随时间变化时，必须记录读取日期和版本。
- `Read status=blocked/unread` 且影响设计时，阻塞 AIP/design。

## External Capability Fact Matrix

| Fact ID | Source ID | External system | Capability/API/resource | Official fact | Preconditions/limits | Failure behavior | Version/region caveat | Confidence | Downstream impact |
|---|---|---|---|---|---|---|---|---|---|

规则：

- `Official fact` 必须是可执行语义，不是“支持 autoscaling”这种标签。
- 必须写清默认值、边界值、状态、时序、失败语义、权限/IAM、版本/区域差异。
- `Downstream impact` 必须指向 ADEC/C/VER/mock acceptance / repo-specific acceptance runtime 或 blocked decision。

## External Mechanism Explanation Matrix

| Mechanism ID | Source fact(s) | Mechanism principle | Key API/resource/metric | Key parameters and meanings | Lifecycle create/update/delete/prune behavior | Failure/permission/metric semantics | AutoMQ design consequence | Required mechanism-design row |
|---|---|---|---|---|---|---|---|---|
| MECH-xxx | FACT-xxx / CONSTRAINT-xxx | how the external mechanism actually works | API/resource/metric name | parameter name -> meaning -> limits/defaults | create/update/delete/prune semantics | permission denied, metric missing, unsupported, partial failure | ADEC/C/VER consequence | MECH-xxx / OPSEQ-xxx / EXTAPI-xxx |

规则：

- 这一节写调研结论的机制原理，不是引用目录。
- 对 autoscaling/HPA/ASG/metrics/runtime/IAM/logs/storage 等，必须解释关键机制如何工作、关键参数是什么意思、生命周期动作如何发生。
- 如果只写“官方支持 X”，但没有 mechanism principle、parameter meanings、lifecycle 和 failure semantics，AIP/design 不得消费该结论。
- 每条会进入设计的机制必须映射到 `mechanism-design-model.md` 的 row。

## Capability Support / Non-Support Matrix

| Capability | External system | Supported? | Supported mechanism | Unsupported / limitation | AutoMQ design implication | User-visible behavior | Required decision | Verification |
|---|---|---:|---|---|---|---|---|---|

规则：

- `Supported?` 只能是 `yes`、`partial`、`no`、`unknown-blocking`。
- `unknown-blocking` 阻塞 AIP/design；不能在实现阶段猜。
- `partial/no` 必须进入产品行为：hidden、disabled-with-reason、unavailable-with-reason、Not Run 或后续需求。

## External Mechanism Decision Matrix

| Mechanism ID | Product semantic | External system | Official mechanism/API/resource | AutoMQ field mapping | Non-equivalent / unsupported semantic | Failure/permission/metric-missing behavior | Required DEC/ADEC | Required contract | Required verification | Owner task / packet carrier |
|---|---|---|---|---|---|---|---|---|---|---|

规则：

- `Product semantic` 写用户/产品真正要表达的语义，例如按 CPU 自动扩缩、创建云资源、读取日志、启动 runtime。
- `Official mechanism/API/resource` 写外部系统真实机制、API、资源或指标来源；不能只写“支持 autoscaling / provider call”。
- `AutoMQ field mapping` 必须把产品/API/DB/VO 字段映射到外部机制参数；缺字段、单阈值/双阈值不等价、默认值/派生值都必须写出。
- `Non-equivalent / unsupported semantic` 必须写不能等价表达的语义；如果完全等价，写 `equivalent` 并说明依据。
- `Failure/permission/metric-missing behavior` 必须写权限不足、指标缺失、区域/版本不支持、provider failure、partial failure 的 AutoMQ 行为。
- 每行必须落到 DEC/ADEC、C、VER 和 owner task / packet carrier；不能只停留在调研文档。

## External Constraint Matrix

| Constraint ID | Source fact | Constraint type | Applies to | Required AutoMQ rule | Contract candidate | Mock/acceptance runtime rule | Verification |
|---|---|---|---|---|---|---|---|

`Constraint type` 可选：`field`、`state`、`lifecycle`、`timing`、`permission`、`quota`、`compatibility`、`failure`、`observability`、`runtime`、`mock`。

## Design Implication Matrix

| Fact/constraint/mechanism | Affected decision | Affected module/API | Required contract | Required verification | Atomic owner candidate | Status |
|---|---|---|---|---|---|---|

规则：

- 每个影响设计的 `Fact ID` / `Constraint ID` / `Mechanism ID` 必须有行。
- `Status=blocked` 阻塞 AIP/design/contract/task planning。
- 不能只写 “参考官方文档”；必须写清它改变了哪个设计选择或契约。

## Mock / Acceptance Runtime External Boundary Map

| External dependency | Real code under test | Mocked boundary | Fact source | Fixture states/errors | Forbidden mock | Acceptance verification |
|---|---|---|---|---|---|---|

规则：

- 只 mock 外部依赖边界，不 mock 业务 Controller/Service/domain/API client。
- fixture 的字段、状态、错误、时序必须来自官方事实、真实 adapter/source 或 locked contract。
- 如果新 controller/API 被加入真实业务路径，必须说明 repo-specific acceptance runtime 是否走真实 controller，以及哪些外部依赖需要 no-cloud adapter。automqbox/CMP 的具体 playground 事实只在 mock-acceptance 阶段读取。

## Research Consumption Gate

| Fact/constraint/mechanism | Consumed by ADEC/DEC | Consumed by contract | Consumed by verification | Consumed by semantic carrier / packet | Dropped / N/A reason | Status |
|---|---|---|---|---|---|---|

规则：

- 每条影响设计的外部事实必须进入 ADEC/DEC、C、VER、semantic_carrier/packet，或有 locked N/A。
- 只留在调研文档、AIP 调研论证段、source excerpt、context pack 中不算消费成功。
- `Status=blocked/open/unknown` 不得进入 pre-execution。
