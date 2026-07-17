---
inclusion: manual
---

# AIP（AutoMQ Improvement Proposal）模板

大项目的开发工作需要先创建 AIP 文档，经过评审后再进入开发。以下是 AIP 的标准模板结构。

## AIP 元信息

| 字段 | 说明 |
|------|------|
| 状态/当前阶段 | Proposed / Accepted / Rejected / WIP / Pre-Release / Released / Discarded / Closed |
| 是否需要开源 | 否/是（默认新功能、工具不开源，评审时可以讨论） |
| 作者列表 | 一个或多个 |
| 预计发布日期 | 如 2023-5-30 |

## 评审记录

| 轮次 | 会议时间 | 参与人 | 会议结论 |
|------|---------|--------|---------|
| Round 1 | | | |

## AIP 正文结构

### 1. 背景
非技术语言的背景和上下文信息，比如来自产品经理的目标客户需求输入，用户故事等。目标客户在背景中特别重要，我们期望通过 AIP 去推动或者转换我们的目标客户。

写够标准：背景需要讲清用户/客户为什么需要这个能力、当前系统是什么状态、为什么现在必须做，以及这些判断来自哪些需求或现有系统证据。背景不是口号，读者应能从这里理解后续方案要解决的真实矛盾。

### 2. 问题定义
该 AIP 具体要解决什么问题，将问题定义清楚，边界描述清楚，Goals 和 Non-Goals。

写够标准：问题定义需要明确 Goals、Non-Goals、涉及概念、支持和不支持的模式、用户可见成功状态、失败状态和边界。容易混淆的概念必须在这里拆开，例如产品能力、部署模式、容量策略、运行时状态、资源 ownership。

### 3. 调研论证
我们今天碰到的问题 99% 都是已经被解决的问题，那么业界有哪些现成的解决方案。

写够标准：调研论证需要同时消费当前架构事实和外部机制事实。凡是涉及云 API、K8s、ASG、HPA、metrics、runtime、IAM、日志、存储、第三方 SDK/API 或 mock/no-cloud 边界，必须写清外部系统实际支持什么、限制是什么、失败/权限/指标缺失如何表现，并引用 `MECH-*`、`FACT-*` 或 `CONSTRAINT-*`。只写“参考官方文档”不够。

### 4. 解决方案
结合我们的实际情况，适合的解决方案，如果跟主流方案相左，需要重点评审。

写够标准：解决方案需要从目的倒推机制，讲清 selected mechanism 为什么能满足产品语义、拒绝了哪些方案、接口/状态/runtime/资源/失败如何闭合。这里必须包含或引用 `Mechanism-Level Design Closure Matrix`，每行降到具体 operation/surface、owner、字段/状态影响、失败行为、验证和 downstream C/VER。

### 5. 原型设计
如果涉及界面，提供一个简单的 PRD 用于评审。

写够标准：涉及 UI 时，需要描述用户从哪里进入、看到哪些字段、触发哪些 action、调用哪些 API、loading/empty/error/warning/review/progress 怎么展示、不同 mode 下哪些字段必须隐藏或只读。不涉及 UI 时写 locked N/A 和理由。

### 6. 接口设计
OpenAPI，模块 API，数据库变更等。

写够标准：接口设计需要给出 canonical request/response/readback 语义，覆盖 OpenAPI、DTO/VO、内部 API、DB/状态/event、Terraform/CLI/frontend payload。必须说明旧字段兼容、缺字段、非法字段、旧 consumer 和新 mode readback 行为。

### 7. 依赖选型
如果涉及依赖外部组件、服务，需要拿出来讨论。

写够标准：依赖选型需要写清选用的外部/内部机制、反选机制、版本/区域/环境/IAM/权限约束、不支持或不等价语义，以及这些约束如何落入 ADEC/C/VER。

### 8. 方案详情
包括架构、流程、测试方案等。

写够标准：方案详情需要展开数据 owner、状态机、runtime 物化、外部副作用、progress/event、资源 ownership、观测、失败恢复、验证 hook 和 mock/no-cloud 替代边界。这里必须包含或引用 `AIP Narrative Materialization Gate`，证明 locked ADEC/DEC、`MECH-*`、`FACT-*`、`CONSTRAINT-*`、当前架构证据和验证策略已经进入 AIP 正文。

### 9. 兼容性问题
该方案是否存在兼容性问题，如果是如何进行升级。

写够标准：兼容性需要覆盖新安装、存量数据、升级、回滚、旧 API/旧字段/旧配置、旧 UI/后端 consumer、mode 泄漏防护和不可兼容项的用户可见表达。

### 10. 被拒绝的其他方案
还有哪些可选的方案，他们各自的优缺点，被拒绝的原因。该章节的目的是帮我们找出较优的方案。

写够标准：被拒绝方案必须是真实可选方案，说明优点、缺点和被拒绝的具体原因。不能只写“复杂度高”“成本高”这类泛化理由。

### 11. 落地计划
AIP 进入 WIP 状态后，最晚一周内需要更新详细的落地计划。为该 AIP 做好规划，时间和里程碑设计，一个 AIP 从开始到关闭设计为 1～4 周为宜，过长的 AIP 应该做进一步细分。

写够标准：落地计划描述工程阶段、前置门禁、验证路径和发布节奏，不在这里拆 Atomic Issue。Atomic Issue 由 task-planning 阶段基于契约和验证矩阵生成。

## AIP 设计完整度附表

在不改变标准章节顺序的前提下，AIP 正文必须在对应章节内包含以下附表：

```markdown
### Mechanism-Level Design Closure Matrix

| Design question | Selected mechanism | Rejected alternatives | Current code evidence | External fact / constraint | Interface impact | State/runtime impact | Failure behavior | Verification | Downstream C/VER |
|---|---|---|---|---|---|---|---|---|---|

### AIP Narrative Materialization Gate

| Source design object | Must appear in AIP section | Narrative requirement | Status |
|---|---|---|---|
```

`Mechanism-Level Design Closure Matrix` 用来证明设计问题已经从概念层降到机制层。`AIP Narrative Materialization Gate` 用来证明 AIP 当时拥有的 ADEC/DEC、外部机制事实、当前架构证据、接口/状态/runtime/兼容/验证决策已经写入 AIP 正文，而不是只留在机器可读矩阵里。后续 readiness/design/archaeology/migration/frontend/verification/task-planning 阶段新增的决策由各自阶段签收，不因共享 `plan.md` 增长而反向成为 AIP 物化义务；只有证明 AIP 原有决策或机制缺失/错误时才回流。

写 AIP 正文时使用 `writing-style`；这个风格只适用于 `aip.md`，不适用于 review、YAML sidecar、Atomic Issue、代码或其它阶段产物。

## AIP 验收

### 发布验收

| 验收项目 | 值和引用 |
|---------|---------|
| （拟）发布版本 | 如：开源版 1.5.0 |
| 新增用例集 | 文档链接 |
| Marathon PR 链接 | |
| 测试报告（功能、性能和兼容性） | 报告链接 |
| 可运维性设计 | 工具使用文档、观测指标说明文档 |
| 产品化文档 | 文档库链接 |
| GTM 文章 | 文章链接 |

### 上线验收

| 验收项目 | 值和引用 |
|---------|---------|
| 目标客户线上运行情况 | 如：某客户采用计算优化型 AutoMQ 实例迁移了 x% 的在线业务 |
| 其它客户升级情况总结 | 不阻碍上线验收，但需要摸底清楚 |
| 故障情况总结 | 如有 |
