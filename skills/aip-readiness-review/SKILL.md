---
name: aip-readiness-review
description: AIP 工程设计决策门禁。Use after product requirements and before code-archaeology-sdd/new-feature-design to review whether an AIP has locked architecture decisions, alternatives, interfaces, dependencies, compatibility, observability, risks, and verification strategy, and to extract decisions into the Decision Registry.
---

# AIP Readiness Review

## 定位

检查 AIP 是否足够作为工程设计输入。

它不替 AIP 做最终决策；发现缺口时输出 blocking questions。

AIP、接口草案、Terraform/API 设计、架构文档即使标题和内容很像工程设计，也只能先视为 `Engineering Propose`。本阶段必须把它们归一化为 locked ADEC/DEC，并基于当前架构理解验证其完整度，不能直接接受外部文档为最终工程设计。

执行或评审本阶段时，必须按 `ai-dev-methodology/references/artifact-completeness-spec.md` 的 “Stage 2: AIP / Engineering Design” 检查正交维度、Required Artifacts、Completeness Criteria 和 Exit Gate。

本阶段产生或锁定的工程决策必须写入 `specs/changes/<change-id>/decision-reviews/aip-decisions.md`，使用或等价满足 `ai-dev-methodology/templates/stage-decision-document.md`，并同步进入 Decision Registry。有 `lark-cli` 写权限时必须同步飞书链接。

执行本阶段必须使用或等价满足 `ai-dev-methodology/templates/engineering-propose-intake.md`。

如果本阶段需要生成或改写 `specs/changes/<change-id>/aip.md` 正文，`writing-style` 仅用于 `aip.md` 正文写作；其它 review、矩阵、sidecar、validator 修复和后续阶段不得套用写作风格技能。

当 AIP/readiness 涉及云 API、K8s/HPA、ASG、metrics、IAM、runtime、日志、存储、外部 adapter、资源生命周期、progress/change/event 或跨 mode 行为时，本阶段必须创建或更新 `specs/changes/<change-id>/mechanism-design-model.md`，使用 `ai-dev-methodology/templates/mechanism-design-model.md`。AIP 正文负责让人读懂方案逻辑；`mechanism-design-model.md` 负责锁定生产机制，供 contract、verification 和 atomic task planning 消费。不要把 writing-style 用到该 sidecar。

## 输入

- 产品需求文档或 `spec.md`。
- AIP 文档、接口草案、Terraform/API 设计或其他工程 propose。
- `external-capability-research.md`，当需求涉及外部系统、云资源、K8s/Helm/Terraform/IAM/network/storage/compute/runtime、第三方 API/SDK、官方协议、autoscaling/scheduling/lifecycle、metrics/logs/events 或 mock/playground 外部依赖时必需。
- 目标 change-id。

## 检查项

### 0. Engineering Propose Intake

必须输出：

```markdown
## Engineering Propose Extraction

| Source ID | Engineering propose | Explicit engineering fact | Inferred engineering fact | Unknown / decision needed | Affected interface/module |
|---|---|---|---|---|---|

## Current Architecture Understanding

| Area | Current architecture / behavior | Evidence path / command | Engineering implication | Gap / DEC |
|---|---|---|---|---|

## Engineering Decision Completeness Gate

| Dimension | Complete? | Evidence section | Open DEC | Blocks next stage |
|---|---:|---|---|---:|
```

规则：

- Current Architecture Understanding 必须有 evidence path / command。
- 任一 `Complete?=no` 且 `Blocks next stage=yes` 阻塞设计、考古、契约和任务规划。
- 如果工程决策会改变产品语义，必须回到 PRD/PDEC，不能在 AIP 中锁定。
- 如果 `decision-surface-discovery.md` 或 Decision Registry 中有 owner stage 为 `AIP` / `readiness` 的 `routed-to-*`、`stage-owned` 或等价待决行，本阶段必须关闭为 locked ADEC/DEC、locked N/A 或 blocked backflow；不得让 AIP/readiness `passed` 后仍留下“后续设计/考古再决定”的 AIP-owned 决策。

### 0.5 External Capability Research Gate

当 AIP/design 依赖外部系统真实能力时，必须先消费 `external-capability-research.md`，不能把“参考官方文档”写成 AIP 结论。

必须检查：

- Research Source Inventory 是否优先使用官方文档、SDK/API reference、标准规范、当前 adapter/source 或真实响应样例。
- External Capability Fact Matrix 是否写清能力、默认值、限制、失败语义、权限/IAM、版本/区域差异和 confidence。
- Capability Support / Non-Support Matrix 是否把 `partial/no/unknown-blocking` 转成设计影响、用户可见行为和 required decision。
- External Constraint Matrix 是否把 field/state/lifecycle/timing/permission/quota/compatibility/failure/observability/runtime/mock 约束映射为 contract candidate。
- Research Consumption Gate 是否把每个影响设计的 fact/constraint 消费到 ADEC/DEC、C、VER、semantic carrier / packet，或 locked N/A。

阻塞条件：

- 外部能力触发条件存在但缺 `external-capability-research.md`。
- 使用非官方事实支撑关键 ADEC/C/VER，且无官方或真实 adapter/source 佐证。
- 存在 `unknown-blocking`、`blocked`、`unread`、`open`。
- 外部事实只出现在 AIP 调研论证段或 source excerpt，没有进入设计决策、契约、验证或 mock/playground 边界。

### 0.7 Mechanism-Level Design Closure Gate

AIP/readiness 不能只锁定概念级 ADEC，例如“支持 ASG autoscaling”“复用 K8s worker 语义”。凡是会影响实现的设计问题，必须降到机制级闭合：一个问题对应一个 operation/surface、一个 selected mechanism、一个 canonical owner、一个失败语义和一个验证闭环。

必须输出：

```markdown
## Mechanism-Level Design Closure Matrix

| Design question | Selected mechanism | Rejected alternatives | Current code evidence | External fact / constraint | Interface impact | State/runtime impact | Failure behavior | Verification | Downstream C/VER |
|---|---|---|---|---|---|---|---|---|---|
```

每行规则：

- `Design question` 必须是可执行问题，描述具体 operation/surface，例如 create、update、delete、readback、runtime materialization、metrics source、autoscaling policy、compatibility migration、frontend action，而不是宽泛能力名。
- `Selected mechanism` 必须写清生产机制、API/resource/state owner 或 runtime 物化方式。
- `Rejected alternatives` 必须包含至少一个真实反选方案及拒绝原因；没有反选方案的行只能标 blocked，不能 passed。
- `Current code evidence` 必须引用路径或命令，说明当前系统相邻模式、旧行为或 owner 位置。
- `External fact / constraint` 在涉及云、K8s、ASG、HPA、metrics、runtime、IAM、日志、存储、mock/no-cloud 时必须引用 `MECH-*`、`FACT-*` 或 `CONSTRAINT-*`。
- `Interface impact` 必须写清 API/DTO/VO/OpenAPI/Terraform/frontend payload/readback 的字段影响，若无影响必须说明 locked N/A。
- `State/runtime impact` 必须写清 DB/state/event/progress/runtime/config/resource ownership 的影响，若无影响必须说明 locked N/A。
- `Failure behavior` 必须写清权限、指标缺失、外部失败、部分失败、旧数据、降级或用户可见错误。
- `Verification` 必须映射到具体 VER 或可输入 Verification Matrix 的证明。
- `Downstream C/VER` 必须指定将被契约和验证消费的 C/VER；禁止写“后续契约阶段决定”“task-planning 再拆”。

阻塞条件：

- 机制级问题仍停留在 capability/concept 层。
- selected mechanism 依赖外部系统但没有官方事实、SDK/API、当前 adapter/source 或真实响应样例支撑。
- interface/state/runtime/failure/verification 任一列是空、TBD、同上、mode-specific、related、后续决定。
- 当前 AIP/readiness owner 的 routed/stage-owned 决策没有关闭为 locked ADEC/DEC、locked N/A 或 blocked backflow。
- 发现实现仍需要选择 provider API、runtime 形态、字段语义、state owner 或失败表现。

### 0.75 Mechanism Design Model Gate

`Mechanism-Level Design Closure Matrix` 只说明每个问题的选择结果；`mechanism-design-model.md` 必须说明这个选择在生产代码里如何发生。凡是本阶段触发机制模型，必须输出并审查：

```text
mechanism-design-model.md
```

必须包含这些模型，不能只写一张摘要表：

- `Mechanism Row Inventory`：每个 `MECH-*` 是一个 operation/surface，不是能力名。
- `Operation Sequence Model`：每个 create/update/delete/autoscaling/readback/progress/runtime operation 的生产步骤、外部调用、状态写入、事件和失败分支。
- `External API Parameter Map`：K8s/HPA/ASG/cloud/runtime/metrics/IAM/logs/storage 等外部 API/resource 的参数含义、AutoMQ 字段映射、不等价语义和失败/权限/指标缺失表现。
- `Event State Model`：事件/step 名、producer、state owner、from/to、terminal、字段、consumer 和 failure reason。
- `Runtime Materialization Model`：artifact、product config、plugin/extensions、secret/security、dependency endpoint、bootstrap/entrypoint、readiness/readback 如何在新 mode 中物化。
- `Resource Lifecycle Model`：owned/generated/select-existing resource 的 create/update/delete cleanup/protect、identity/provenance、idempotency/retry、partial failure residual。
- `Failure Consistency Model`：DB/state 和 provider side effect 的先后顺序、失败后 readback 不变量、retry/rollback/cleanup 策略。
- `Module Interface Model`：producer/consumer、method/API/event/resource surface、request/response/error fields 和 timing。

规则：

- 每个影响实现的 `MECH-*` 必须有上述模型行，或在不适用列写 locked N/A 和理由。
- 如果某行只写“支持 ASG autoscaling”“使用 HPA”“复用 K8s 配置”“创建资源”“记录事件”，没有参数、字段、状态、事件、owner、失败和 verification，本阶段不得 passed。
- 如果 AIP 正文写了某机制，但 `mechanism-design-model.md` 没有对应 `MECH-*`；或 sidecar 有 `MECH-*` 但 AIP 正文没有讲清设计链条，均阻塞。
- Contract、verification、task-planning 只能消费这些机制行，不得重新发明 provider API、runtime carrier、event fields 或 cleanup/protect 语义。

### 0.8 AIP Narrative Materialization Gate

AIP 不是只给机器消费的 sidecar。`aip.md` 必须让人能读懂本次方案的完整设计链条：问题为什么存在、当前系统是什么、外部机制允许什么、为什么选这个方案、接口/状态/runtime/失败/兼容/验证如何闭合。ADEC、MECH、FACT、CONSTRAINT、Current Architecture Understanding 和关键 verification 不能只停留在 `plan.md` 或 `decision-reviews/aip-decisions.md`。

必须输出：

```markdown
## AIP Narrative Materialization Gate

| Source design object | Must appear in AIP section | Narrative requirement | Status |
|---|---|---|---|
```

规则：

- `Source design object` 必须覆盖 locked ADEC/DEC、`MECH-*`、`FACT-*`、`CONSTRAINT-*`、Current Architecture Understanding 的关键 evidence、接口/状态/runtime/兼容/验证决策。
- `Must appear in AIP section` 必须指向标准 AIP 章节，例如 `3. 调研论证`、`4. 解决方案`、`6. 接口设计`、`8. 方案详情`、`9. 兼容性问题`、`10. 被拒绝的其他方案`。
- `Narrative requirement` 必须说明正文需要讲清的推理链，不允许只写“引用 ADEC-xxx”。
- `Status` 只能是 `materialized`、`locked N/A` 或 `blocked`。`blocked` 阻塞下一阶段。

AIP 正文写作要求：

- 保留 AutoMQ AIP 标准标题。
- 工程矩阵可以作为章节内子表，但正文必须用自然语言把设计链条讲清楚。
- 生成或改写 `aip.md` 正文时使用 `writing-style`；该风格不适用于本 review 文档、矩阵、YAML sidecar 或后续 Atomic Issue。
- 如果 AIP 正文没有消费 sidecar 中的关键设计对象，即使 sidecar 完整，本阶段仍不通过。

### 1. 问题定义

- 是否说明为什么现在做。
- 是否定义 Goals 和 Non-Goals。
- 是否区分产品能力、部署模式、容量策略、运行时状态等容易混淆的概念。

### 2. 方案决策

```markdown
| Decision | Selected option | Rejected alternatives | Reason | Impact |
|---|---|---|---|---|
```

每个关键设计选择必须有反选方案。没有反选方案的“方案”通常还不是决策。

### 3. 接口与契约

检查是否覆盖：

- OpenAPI
- Terraform / SDK / CLI
- 内部模块 API
- DB / 状态机 / 事件
- 前端展示和交互
- 部署/云资源
- metrics/logs/events/alerts

如果 AIP 涉及云资源、部署模式或派生配置，必须额外说明：

- 每个云资源参数由用户选择、后端自动创建、从现有资源推导、环境固定，还是不支持。
- 如果从现有资源推导，逐字段说明 source of truth、缺字段行为、错误语义。
- 是否复用现有产品创建模式；如果复用，引用参考实现字段矩阵；如果不复用，说明反选理由。
- 前端空 payload 是否合法，合法时后端必须补齐哪些字段。

### 4. 兼容性和迁移

必须说明：

- 新安装行为
- 存量行为
- 升级
- 回滚
- 旧 API/旧字段/旧配置
- 数据兼容

### 5. 验证策略

必须说明哪些行为由哪些验证证明：

- unit
- integration
- E2E
- Terraform/Helm render/plan
- runtime/manual
- performance/compatibility if relevant

## Local Audit Gate: Engineering Decision Audit

AIP readiness verdict 输出后、允许进入设计/考古/契约前，主 agent 必须本地二次审计工程决策完整度。本地审计只发现工程 propose 归一化和证据缺口，不锁定 ADEC/DEC。

输入：

- Engineering Propose Extraction。
- Current Architecture Understanding。
- Engineering Decision Completeness Gate。
- AIP/接口草案/Terraform/API 设计。
- PRD/PDEC 和 Decision Registry。

输出：

```markdown
### AIP Local Audit Report

| Audit scope | Finding | Evidence | Missing decision | Required backflow | Blocks next stage |
|---|---|---|---|---|---:|
```

必须审计：

- 工程 propose 是否被拆成 explicit fact、inferred fact 和 unknown / decision needed。
- 外部能力调研是否完整，官方事实是否被消费到 ADEC/DEC/C/VER，而不是停留在调研段。
- 当前架构理解是否有路径/命令 evidence，而不是只采信 AIP 文本。
- Mechanism-Level Design Closure Matrix 是否把每个关键设计问题降到 operation/surface、selected/rejected mechanism、interface/state/runtime/failure/verification 和 downstream C/VER。
- `mechanism-design-model.md` 是否把每个机制选择展开为 production sequence、external API parameter map、event state、runtime materialization、resource lifecycle、failure consistency 和 module interface，且每行都可追到 ADEC/MECH/FACT/CONSTRAINT/C/VER。
- AIP Narrative Materialization Gate 是否证明 ADEC/MECH/FACT/CONSTRAINT/current architecture/interface/state/runtime/verification 已进入 `aip.md` 标准章节正文。
- 每个工程取舍是否有反选方案、产品约束对齐、影响模块和验证方式。
- 接口、数据/状态、部署/IAM、观测、兼容、验证是否完整。
- 工程决策是否改变产品语义；若改变，必须回流 PRD。

阻塞条件：

- ADEC/DEC open 或 missing alternatives。
- 外部能力调研缺失、官方事实 unread/blocked、unknown-blocking 未处理，或 research fact 没有 downstream consumption。
- 当前架构理解缺 evidence。
- 工程 propose 直接被当成 final design。
- 机制级设计问题缺 selected/rejected mechanism、接口影响、状态/runtime 影响、失败语义、验证或 downstream C/VER。
- 机制模型缺失，或仍把 provider API、runtime 形态、CPU/metrics source、event fields、resource cleanup/protect、partial failure/readback consistency 留给 contract/task-planning/implementation。
- AIP 正文没有 materialize 已锁定 ADEC/MECH/FACT/CONSTRAINT/current architecture 关键设计对象。
- 接口/兼容/观测/验证缺任一必需维度。
- 工程决策与 PDEC 冲突或改变用户语义。

## 输出

```markdown
## AIP Readiness Review

### Verdict

| Item | Ready? | Notes |
|---|---:|---|
| Problem definition | yes/no |  |
| Architecture decisions | yes/no |  |
| Interface design | yes/no |  |
| Compatibility | yes/no |  |
| Observability | yes/no |  |
| Verification | yes/no |  |

### Blocking Questions

| ID | Question | AIP section | Blocks | Suggested owner |
|---|---|---|---|---|

### Decision Registry Extract

| Decision ID | Decision | Source section | Alternatives | Status |
|---|---|---|---|---|
```

## 退出检查

- [ ] AIP/接口/Terraform/API 设计均作为 Engineering Propose 归一化，未直接接受为 final design。
- [ ] 涉及外部能力时，`external-capability-research.md` 已完成并被消费到 ADEC/DEC/C/VER/mock/verification。
- [ ] Current Architecture Understanding 有 evidence path / command。
- [ ] Engineering Decision Completeness Gate 没有阻塞项。
- [ ] Mechanism-Level Design Closure Matrix 已把关键设计问题降到 operation/surface、selected/rejected mechanism、owner、字段/状态/runtime、失败语义、验证和 downstream C/VER。
- [ ] AIP Narrative Materialization Gate 证明 ADEC/MECH/FACT/CONSTRAINT/current architecture/interface/state/runtime/verification 已写入 `aip.md` 标准章节正文。
- [ ] 关键工程决策已锁定。
- [ ] 反选方案和取舍明确。
- [ ] 接口、兼容、观测、验证都有设计。
- [ ] 涉及云资源/部署模式/派生配置时，参数归属、source of truth、缺字段行为和参考实现取舍已锁定。
- [ ] AIP 决策已进入 Decision Registry。
- [ ] 已生成或更新 `decision-reviews/aip-decisions.md`，有飞书写权限时已同步飞书并回写链接。
- [ ] 已完成 AIP Local Audit Report；无 `Blocks next stage=yes` 项。
- [ ] 没有 blocking question。
- [ ] 已满足 artifact-completeness-spec Stage 2 的 Architecture Decision、Interface Change、Data/State、Deployment/IAM、Observability、Compatibility、Verification Strategy artifact 要求。
