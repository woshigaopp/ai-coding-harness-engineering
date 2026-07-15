---
name: automq-ai-dev-workflow
description: AutoMQ AI coding 大需求总入口。Use when starting a new feature or major existing-code change from product requirements/AIP, deciding atomic vs SDD workflow, routing through product requirement design, AIP readiness, decision registry, new-feature design, code-archaeology-sdd, migration diff, frontend contracts, cross-module-contract-sdd, verification matrix, atomic task planning, atomic-execution-sdd, strict mock acceptance gate, product acceptance, and convergence retrospective while keeping final artifacts under specs/changes.
---

# AutoMQ AI Dev Workflow

## 定位

这是大需求 / 大改动的协调层，不替代具体阶段 skill。

本 workflow 的中间交付物不是 PRD、AIP、plan 或 tasks.md，而是一组模块内、契约闭包完备、可以按顺序执行的 Atomic Issues。Atomic Issues 的目标是降低实现方差；所有 Atomic Issues 依次实现并完成各自验证后，只表示可以进入上线收敛评审，不表示大需求自然完成。

本 workflow 的通用验收层是 `mock acceptance`：任何涉及 API、前端、外部依赖、部署/运行时模式、异步状态、metrics/logs、第三方服务或不上云验收的大需求，都必须让验收适配器、fixture、simulator、matrix case 与业务代码一起设计、实现、测试和提交。

`repo-specific acceptance runtime` 是目标仓库可选定义的打包验收运行时：真实产品代码必须正常运行，只允许把云 API、K8s API、Kafka instance API、Kafka Connect REST API 等物理外部依赖替换成 no-cloud adapter。automqbox/CMP 只有在开发 Connect 相关功能时才启用 `playground`，对应真实 `cmp-playground` 模块；automqbox 非 Connect 功能和其他仓库不得生成 `playground-*` artifact，也不得读取 automqbox playground 事实，除非它们自己定义了等价验收运行时。

前置所有阶段只服务于一个目标：识别模块、锁定模块责任边界、枚举并决策模块之间的契约，再把这些契约闭包转成模块内可执行 issue，让实现阶段满足 AI 原子能力边界：

1. 零决策或决策已前置
2. 单层变更
3. 上下文自包含
4. 验证闭环短
5. 错误不传播

在“决策前置”之前，workflow 必须先完成“决策面发现”。用户只给 purpose、目标或高层需求时，AI 不能稳定自行想到所有需要决策的点。因此在 PRD/readiness 阶段必须生成 `specs/changes/<change-id>/decision-surface-discovery.md`，使用 `ai-dev-methodology/templates/decision-surface-discovery.md`，覆盖 mode consumer、capability、frontend action、post-create consumer、persistent mutation、operation mutability、managed resource ownership、runtime lifecycle、runtime mode materialization parity、mock acceptance / repo-specific acceptance runtime、observability、permission 和 compatibility。每个 surface 必须有 owner stage、locked decision/contract/verification、owner Atomic Issue 或 locked N/A；缺失时不得进入 pre-execution。若命中 runtime mode materialization parity，按需读取 `/Users/keqing/.codex/skills/ai-dev-methodology/references/experience/runtime-mode-materialization-parity.md`。

## Gate-Locked Delivery

本 workflow 的优先级是：先锁定阶段质量，再推进下一阶段。`继续推进` 只能表示在 gate 允许的范围内自动修复和重跑；不能表示先写候选文档、薄任务或代码来制造进度。

候选 artifact、未锁定文档、空表、部分 packet、局部通过的 compiler check 都不是下游输入。只有状态为 `passed`，且对应 artifact、rubric、validator 全部通过并存在有效 `stage_receipts.<stage>` 的产物，才能被下一阶段消费。

当用户要求“workflow 继续推进”“直到所有步骤做完”“中间不要中断”时，含义是自动完成从需求到实现、验证、mock acceptance、适用的仓库专属验收 runtime 和产品验收入口的闭环；每一步仍必须经过对应 gate。遇到 gate failure 时，必须回流修到 gate 通过，而不是把 failure 记录成待办后继续。

执行规则：

- 任一 gate、脚本、rubric、本地审计、browser smoke 或 acceptance 返回 `blocked` / `fail` / P0/P1 时，默认动作是回流到最早缺失阶段，修 artifact / 代码 / mock / 验证 / 环境后继续重跑。
- 在 `workflowctl.py validate pre-execution` 和 `validate_artifacts.py` 同时通过之前，禁止修改 `specs/changes/<change-id>` 之外的文件。发现已经有非 specs 代码改动时，必须停止执行、记录 backflow，并先修 artifact；不得继续扩大实现。
- `workflowctl.py` / `validate_artifacts.py` / `atomic_issue_compile.py` 失败、不可运行、输出过长、规则严格、或 agent 觉得修复成本高，都只能导致 `blocked` / backflow；不得降级成 checklist 自审、关键词自审、人工口头确认或“先执行已闭合 Txxx”。
- 没有 `workflowctl.py validate pre-execution`、`validate_artifacts.py` 和 `workflowctl.py begin-execution` 的成功证据时，不得说 `pre-execution complete`、`ready for execution`、`准备开始 T001`、`进入 T001`、`可以开始改代码` 或等价表达。
- 只有真实人类阻塞才停下来：产品决策未授权、凭证/权限缺失、真实云/runtime evidence 客观不可取得、PRD/AIP 互相冲突且无可锁定选择、或用户明确要求暂停。
- `blocked` 不是 `done`，也不是“跳过继续”。它表示当前阶段必须进入 backflow loop，并在 `Backflow Invalidation Matrix`、对应 stage decision doc、`tasks.md` / acceptance artifact 中记录失效对象和重跑结果。
- `completed` / `done` 不是合法阶段状态。`workflow-state.yaml.stage_status` 只能使用 `not_started`、`in_progress`、`blocked`、`passed`、`not_applicable`、`pending-rewrite`、`pending-rerun`。`passed` 不是人工状态，只能由 `workflowctl.py pass-stage <stage> specs/changes/<change-id>` 在对应 artifact、rubric 和 validator 通过后写入，并同时写入 `stage_receipts.<stage>`。
- 手工把 `stage_status.<stage>` 改成 `passed` 属于门禁违规；没有 `stage_receipts`、receipt 命令不匹配、或 artifact hash 过期时，下游必须视为未通过并回流，不得继续。
- 对 automqbox/CMP Connect 功能，完成状态必须包含可访问的 packaged playground 或明确等价环境、端口/PID/branch/bundle/package freshness、mock/product acceptance evidence、以及交付前 first-line QA 结果。automqbox 非 Connect 功能只使用通用 mock/product acceptance，不感知 `cmp-playground`。

### No Broad Skeletonization

不得为了制造进度而批量创建大量空表、薄 artifact 或只有标题的 canonical 文件。需要创建多个 artifact 时，必须按可验证语义对象逐个闭合，而不是先铺全目录再补。

规则：

- 写不出完整内容的 artifact 标 `blocked`，只记录 blocker、缺失 source、required backflow；不要伪装成候选 `passed` artifact。
- 不得把未锁定候选产物用作进入下游阶段的理由。
- 不得把 `atomic_issue_compile.py --check` 通过当作 task tree 可执行；它只证明 packet 与 Markdown 同步。
- 不得因为部分 Txxx packet 合格，就执行这些 Txxx；pre-execution 是整个 change 的 admission gate，不是单任务绿灯。
- 不得因为 validator 严格、任务数量多、artifact 生成重，就改成“先生成一组可执行任务包”。任务数量和拆分必须由 contract edge、semantic type、operation/surface 和 verification loop 决定；无法完整闭合时标 `blocked-backflow`。

### Depth-First Semantic Closure

大需求 artifact 生成必须先深后广。对每个高密度语义对象，先完成以下闭环，再扩展到下一组对象：

```text
SRC/REQ/SCN/PDEC -> decision surface -> DEC/ADEC -> C/MIG -> VER -> semantic_carrier -> Txxx packet -> compiled issue -> validator
```

如果某条链路无法闭合，当前阶段保持 `blocked`，并回流到最早缺失阶段。不得用全局文档、聊天记忆、自然语言摘要或后续实现阶段来补这条链路。

### Surface-to-Obligation Projection Gate

`decision-surface-discovery.md` 发现的是抽象决策面，不是可执行义务。抽象 surface 不能直接关闭为一个粗 `Txxx`；必须先展开成可被代码、API、fixture 或验证打脸的最小 obligation rows，再进入 C/VER/T。

进入 `cross-module-contract-sdd`、`verification-matrix` 或 `atomic-task-planning` 前，必须在 `decision-surface-discovery.md#Surface Obligation Projection Matrix` 证明每个高风险 surface 已经展开。每行必须同时具备：

- `Expanded obligation ID`：稳定 ID，不得只复用 DS 编号。
- `Mode / variant`、`capability / consumer`、`operation surface`：明确是哪种模式、哪个能力、哪次操作。
- `Production provider owner`：真实生产代码 owner，必须落到具体 API path、class/file、provider/operator/client method、DB/entity/field、task step 或 runtime writer；不能只写模块名、阶段名、`backend`、`runtime`、`T009`。
- `Consumer owner`：消费方 owner，如 frontend route/component/API client、progress/event consumer、mock acceptance case；consumer 不能替代 provider。
- `Mock / acceptance owner`：需要不上云或 repo-specific runtime 验收时，列出 mock handler、fixture file、simulator、adapter evidence 或 locked N/A。
- `Required decision`、`Contract obligation`、`Verification`：每行都必须有具体决策、C/OBL 或 locked N/A，以及 exact assertion / command / browser network / DOM / fixture proof。
- `Negative assertion`：证明错误继承不会发生，例如 wrong-mode 字段不出现、旧 provider profile 不发送、K8s namespace error 不泄漏、policy materialization 不被当成真实 scaling activity。
- `Owner Txxx or locked N/A`：实现 owner 和 proof owner 必须对应行级 obligation，而不是关闭整个 surface。

反填表规则：

- 以下词不能单独关闭 obligation row：`mode-aware`、`support`、`handle`、`stable shape`、`runtime tabs`、`baseline`、`readback`、`mock coverage`、`selector`、`managed resource`、`provider proof`、`mode-specific`。可以使用这些词，但必须紧跟具体对象、代码锚点、状态/错误语义和验证断言。
- frontend row 不能关闭 backend/API/runtime/provider 能力；mock row 不能关闭 production side effect；DB readback 不能关闭 provider write；browser smoke 不能关闭 backend contract；packaged playground 代表性 case 不能关闭 backend/frontend matrix 穷举行。
- locked N/A 必须写产品语义：用户/API 看到什么、错误码/response shape 是什么、UI 如何展示、mock/acceptance 如何证明、为什么不是运行时内部异常。
- 如果一行没有 concrete anchor、negative assertion 或 exact verification，它只是写作摘要，不是 closure。当前阶段必须 `blocked`，回流到 surface discovery、contract、verification 或 task planning。

强制展开触发器：

| Trigger | Required projection |
|---|---|
| `workers/logs/metrics/endpoints/plugins/connectors/events` | 按 `runtime tab × mode × backend API owner × frontend consumer × mock fixture × unavailable/unsupported decision` 展开；每个 tab/mode 都要有 production behavior 或 locked N/A。 |
| `auto-create/default-created/generated/managed/select-existing` | 按 `resource × selection mode × provider writer × identity/provenance persistence × runtime/readback consumer × cleanup/protect × failure/idempotency` 展开；selector/UI 不能关闭 ownership 生命周期。 |
| `baseline/default` | 拆成具体 baseline kind，例如 deploy trust/profile、runtime permission policy、connector-specific permission；每类必须有 decision、owner、verification 或 open blocker。 |
| user-visible event / progress / change | 必须写 `event_purpose`，区分 policy materialization、decision record、runtime activity、failure/prevented record；UI 文案和 evidence level 必须匹配。 |
| browser selector / option API | 按 `selector API × controller route × provider context source × configured fixture ID × real-vs-mock route × negative assertion` 展开。 |
| create/update/edit/save/resize/delete/recreate/migrate 复用同一对象、同一 config 或同一 readback 字段 | 按 `field × operation × product semantic × backend mutation owner × UI expression × verification` 展开；创建时需要配置的字段，不等于运行后可以在普通更新入口修改。每个字段必须决策为 editable / read-only / hidden / disabled / unsupported / recreate-required / migrate-required，并说明产品原因。 |
| exact handoff / acceptance command | 每条交付命令必须有 executed evidence，或显式 `not_run_disclosed`，并写明 toolchain/runtime 环境。 |

### Operation Mutability Decision Gate

凡是需求涉及已有对象的 `update` / `edit` / `save` / `resize` / `delete` / `recreate` / `migrate`，或前端出现“修改配置”“update basic config”“edit settings”“change deployment”等入口时，workflow 必须先决策 operation 语义，不能从 create 表单、create DTO、readback VO 或已有字段反推 update 能力。

Operation mutability 是产品/工程边界决策，不是实现期推断。创建时需要用户选择的字段，运行后修改可能只是普通 update，也可能需要 rolling refresh、restart、delete+create、migration，或者应该明确 unsupported。AI 必须把这种差异显式化，让人或已授权决策流程选择。

每个相关字段必须至少回答：

| Field | Required decision |
|---|---|
| Field / config path | 具体字段路径，例如 `deployment_config.asg.vpc_id` |
| Create-time meaning | 创建时该字段决定什么资源、状态、runtime 或外部依赖 |
| Runtime owner after create | 创建成功后该状态由谁拥有：DB、provider resource、runtime、外部系统、用户选择或 derived readback |
| Update action required | 修改该字段需要什么真实动作：只改 DB、provider update、rolling refresh、restart、delete+create、migration 或 unsupported |
| Product semantic | 该动作在用户语义上是 update、restart、recreate、migrate、dangerous operation 还是 unsupported |
| Recommendation | 推荐 editable、read-only、hidden、disabled、unsupported、recreate-required 或 migrate-required |
| Reason | 从产品预期、风险、可恢复性、现有模式、验证成本和失败表达说明为什么 |
| Backend owner | 若允许修改，必须有 controller/service/task/provider owner；若没有则不能让 frontend 提交 |
| UI expression | selector、只读展示、禁用说明、隐藏、跳转到重建/迁移 flow 或错误/提示文案 |
| Verification | API exact-key、DOM、negative assertion、provider/readback/failure proof 或 locked N/A proof |

硬规则：

- 如果修改某字段需要 delete+create 核心运行时资源、替换外部资源边界或迁移数据/流量，AI 必须把它作为产品决策暴露出来；不得默认归入普通 update。
- 如果 backend 没有对应 mutation owner，frontend 不得提供可提交控件；只能 locked N/A、只读、禁用、隐藏，或回流补 backend contract。
- 如果字段被标记为 read-only / disabled / unsupported / recreate-required / migrate-required，必须定义用户/API 看到什么、错误码或 UI 表达是什么，以及 mock/product acceptance 如何证明不是内部异常或静默失败。
- Operation mutability decision 会改变用户可见语义，未授权 AI 决策时必须作为产品/工程决策处理；模糊的“按 create 页面做一版”“沿用已有字段”不能关闭该决策。
- frontend action-flow 只能消费已锁定的 mutability decision；不得用“active branch payload 正确”替代“该字段允许在该 operation 修改”的产品/工程决策。

## Module Contract First

大需求不是先拆 checklist task，而是先建模为模块和模块契约图。

必须先回答：

- 有哪些模块。
- 每个模块拥有的数据、状态、资源和生命周期是什么。
- 每个模块对外提供哪些契约。
- 每个模块依赖其他模块提供哪些契约。
- 每条跨模块契约的触发、正常路径、失败路径、一致性、时序和验证是什么。
- 每条跨模块契约是否需要本地 mock acceptance 或仓库专属验收 runtime 表达；mock 对外契约是否与真实 provider/API 同构。
- 每条契约背后的产品/工程/兼容/验证决策是否已锁定。

“不允许未知决策出现”的具体含义是：不允许未知模块责任决策、未知跨模块契约决策、未知对外承诺决策进入实现阶段。

实现 issue 的正确模型是：

```text
在某个模块内，在 consumed contracts 已成立的前提下，实现该模块需要提供/维护的 provided contracts。
```

如果一个 issue 需要重新定义模块边界或模块之间的契约，它不是实现 issue，而是 design/contract gap，必须回流到设计或契约阶段。

## Mock As First-Class Delivery

mock 的目标不是“让页面有数据”，而是把真实外部世界或运行时边界的外部契约本地化。它必须和真实业务实现遵守同一份对外契约。

本 workflow 必须严格区分“生产实现契约”和“验收适配器契约”：

- 生产实现契约在设计、契约、验证、任务规划和业务实现阶段锁定。它只描述真实产品代码必须调用哪些 controller/service/manager/task/repository/provider/K8s/Connect REST 抽象、产生哪些 DB/resource/event/runtime 副作用、对 UI/API 暴露什么状态。生产实现不得因为后续要用 mock acceptance、no-cloud adapter 或仓库专属验收 runtime 而降级成本地完成、跳过外部 adapter 调用、只写 DB 状态或只发 progress event。
- 验收适配器契约只在 `mock-acceptance-gate` / product acceptance 阶段读取和使用。它描述验收适配器如何承接生产代码打出的外部调用，用于证明生产路径，不反向决定生产实现边界；automqbox/CMP Connect 功能中的该验收适配器才是 packaged playground + no-cloud adapter。
- 实现前的 artifact 可以生成 mock/backend/frontend/packaged case 的 planned rows，但这些 rows 只能使用生产契约、官方/真实外部接口事实和待证明维度；不得读取当前 `repo-specific acceptance runtime` 代码、仓库专属验收适配器实现、packaged 启动细节，或把这些细节复制进业务 Atomic Issue。
- `mock acceptance`、`no-cloud`、“不上真实云验收”或 repo-specific acceptance runtime 这类词不得解释为“功能可不真实实现”。正确解释永远是：生产代码正常调用生产 adapter；验收时由 adapter/simulator 接住该调用。

强制规则：

- 需求涉及外部依赖或不上云验收时，必须在设计阶段明确 mock 边界：哪些是真实被测代码，哪些是外部系统替身。
- 真实服务对外 API、mock API、前端消费契约必须共享同一组 path、body、response shape、enum、错误码、状态机、终态语义和时序假设。
- mock 可以保存内部状态，但不得向被测前端/API 消费方泄漏真实服务不会暴露的内部状态、内部错误或中间枚举。
- mock 数据必须覆盖成功、失败、边界、终态、权限/依赖不可用、部分失败和重试；只覆盖 happy path 不合格。
- mock acceptance 相关修改必须进入 Atomic Issue、Verification Matrix、Mock Acceptance Gate 和最终提交范围；不得作为临时本地脚本或手工 fixture 留在工作区外。automqbox/CMP playground changes 只有在目标仓库/应用为 automqbox/CMP 且功能属于 Connect domain，或需求明确修改 playground module 时才适用。
- product acceptance 发现 mock 行为与真实契约不一致时，按正式验收缺陷处理，回流到最早缺失阶段；不能以“只是 mock”降级。

### Packaged Acceptance Runtime Boundary

本小节只定义通用边界，不携带任何仓库专属实现细节。

- `mock acceptance` 是通用验收机制：用契约驱动的 fixture、simulator、backend/frontend matrix 和 representative packaged/browser case 证明真实产品路径。
- `repo-specific acceptance runtime` 是目标仓库自己的验收运行时；它只能在 mock-acceptance / product-acceptance 阶段读取具体实现事实。
- 如果目标仓库定义了 repo-specific acceptance runtime，它只在 `mock-acceptance-gate`、product acceptance、或专门修改该 runtime 基础模块时读取目标仓库的 runtime reference 和当前 runtime 代码。automqbox/CMP 的 `playground` 只对 Connect 相关功能启用。
- 设计、契约、任务规划和业务实现阶段不得读取 `repo-specific acceptance runtime` 启动命令、验收适配器实现、controller routing guard、fixture graph 或 runtime 细节；这些阶段只锁定生产实现必须真实调用的 adapter/API/resource 副作用，以及后续需要验证的维度。
- 任何 repo-specific acceptance runtime 都不能反向降低生产实现义务。生产代码必须按生产路径实现；验收运行时只是替代物理外部依赖来接住同一批生产 adapter 调用。

Mock 合格标准：

| Dimension | Required proof |
|---|---|
| Contract source | mock 字段、枚举、状态、错误、时序能追溯到 API 规范、现有真实服务、外部文档或 locked contract |
| Boundary | 被测业务/API/UI 没有被 mock 掉；只 mock 外部依赖或为 no-cloud 验收必需的持久化替身 |
| Drift guard | 有测试或脚本防止真实服务契约、mock 契约、前端消费契约漂移 |
| User semantics | mock 驱动的页面状态、进度、错误、空值、不可用、终态与产品语义一致 |
| Deliverability | mock 代码和业务代码一起 build/test/package，能被 reviewer 看到并复现 |

Mock acceptance 必须分三层；对带 repo-specific acceptance runtime 的目标仓库，不得把所有组合压到最终 packaged/browser 点击：

| Layer | Role | Required artifact | Why |
|---|---|---|---|
| Backend Mock Matrix | 快速覆盖 controller/service/mock-handler/mock-service/API/state 组合 | `mock-backend-matrix.yaml` | 先挡住 contract drift、fallback、状态机、持久化 write+readback 和 fixture 图错误 |
| Frontend Action Matrix | 快速覆盖真实 route/component/API-client/DOM/payload/user action 组合 | `mock-frontend-action-matrix.yaml` | 在打包前验证 action、payload、DOM、负向泄漏和 selector 状态 |
| Packaged / Repo-Specific Representative Cases | 代表性证明打包产物、静态资源、真实浏览器路由、handler wiring、freshness 和 handoff QA | `mock-acceptance-cases.yaml` + `mock-acceptance.md` | 最慢、最接近交付，只证明集成代表样本，不承担全组合穷举 |

`mock-acceptance-cases.yaml` 的 packaged case 必须通过 `backend_matrix_refs` 和 `frontend_action_refs` 追溯到前两层矩阵。后端或前端矩阵未通过时，不得启动、刷新或交付任何 packaged/runtime/browser 入口来声明验收完成；尤其不得用 packaged browser check 替代矩阵。

这三层 case system 必须在 task-planning / pre-execution 前生成 planned rows：

- `mock-test-dimensions.yaml` 定义有限维度和 coverage sets。
- `mock-backend-matrix.yaml` 定义快速后端/handler/service/API/state 组合。
- `mock-frontend-action-matrix.yaml` 定义快速前端 route/component/API-client/DOM/payload/action 组合。
- `mock-fixture-graph.yaml` 定义 selector、runtime、progress、detail、event 数据如何被页面和 API 消费。
- `mock-acceptance-cases.yaml` 只保留 packaged/runtime 代表性集成 case，并回指 backend/frontend matrix refs。

pre-execution 前允许这些行是 `planned`，但不允许只有自然语言“覆盖四种组合”。执行后 `mock-acceptance` stage 必须把 blocking rows 的 row-level evidence 写入 `mock-acceptance-execution.yaml`，再由 `workflowctl.py pass-stage mock-acceptance` 签收；不得修改 sealed matrix/case 文件去标 passed。

## Post-Atomic Launch Convergence Gate

Atomic execution、mock acceptance 和 product acceptance 通过后，仍必须进入上线收敛评审。该 gate 的评审基准是当前需求的生产上线标准，不是 Atomic Issues 的逐字清单。

主口径：

> 以当前需求的生产上线标准为唯一评审基准，评审集成 PR 或等价 diff 是否已经形成可上线的端到端实现闭环；不要把 Atomic Issues 当作逐字验收清单，也不要把实现方案差异直接判定为缺口。

生产上线标准必须从当前需求的 PRD、AIP、spec、contracts、verification、acceptance evidence 和实际 diff 中实例化。通用 closure 维度是：

| Closure | Review question |
|---|---|
| User journey closure | 需求声明的关键用户路径是否端到端闭合，并能被真实入口或等价 acceptance runtime 证明。 |
| Domain semantic closure | 核心领域语义是否真实实现，而不是只有字段、DTO、页面或 mock 数据形状。 |
| Runtime / external effect closure | 声明的外部副作用、provider/API/runtime 调用是否真实发生，并有 readback、adapter evidence 或明确 Not Run 风险。 |
| State and failure closure | 状态、错误、重试、回滚、残留、部分成功、不可用和权限失败是否能解释真实 runtime。 |
| Compatibility and boundary closure | 新旧模式、兼容路径、互斥字段、权限边界和 mode boundary 是否没有串味。 |
| Acceptance evidence closure | 验收证据是否覆盖代表性上线场景，而不是只证明单点存在或单测通过。 |

Finding 必须分类：

| Type | Meaning | Required action |
|---|---|---|
| `implementation_gap` | PR / diff 没有达到生产上线标准。 | 修代码、补测试、补 acceptance evidence，并重新 review。 |
| `atomic_task_gap` | PR 可以成立，或暴露了当前 Atomic Issues 未能清楚描述的上线级实现闭环。 | 记录为方法论/任务描述缺口，作为后续复盘输入；本 gate 不再回流改 Atomic Issues。 |
| `launch_decision_required` | 最终上线评审发现实现方无法自行决定的上线时决策，例如接受风险、调整上线范围、选择保守行为。 | 在本 gate 内与人交互确认，记录 human launch decision、owner、影响和结论；不回流到 PRD/AIP/contract/Atomic Issues。 |
| `acceptance_gap` | 实现可能成立，但缺少足够上线证据。 | 补 mock/product/packaged/browser/provider evidence。 |
| `methodology_gap` | 缺口来自 workflow/skill/rubric 没有防住可重复问题。 | 记录为后续 skill/validator 改进输入；不阻塞当前 PR，除非同时构成 launch-blocking implementation/acceptance/decision finding。 |
| `allowed_implementation_variance` | PR 与 Atomic Issue 的具体方案不同，但不破坏需求语义和上线闭环。 | 记录差异，不能当作 implementation gap。 |

硬规则：

- Atomic Issues 是实现计划和对照材料，不是生产上线标准本身。
- 发现 PR 与 Atomic Issue 不一致时，必须先判断差异是否破坏需求语义或上线闭环；如果不破坏，归为 `atomic_task_gap` 或 `allowed_implementation_variance`。
- 评审输出写入 `specs/changes/<change-id>/launch-readiness-review.md`，记录 review input、production standard sources、findings、classification、owner、resolution action、human launch decision、evidence 和关闭状态；模板使用 `ai-dev-methodology/templates/launch-readiness-review.md`。
- 该 gate 是最终 post-PR convergence gate，只能在集成 PR 创建/更新或等价 diff artifact 发布后启动；运行 `workflowctl.py validate-launch-readiness specs/changes/<change-id>` 校验。
- 所有 launch-blocking findings 关闭前，不得宣布 workflow 完成；修复后必须重新执行受影响验证和本 gate。
- 若仓库流程要求 PR，Atomic execution 和 acceptance 完成后必须创建或更新集成 PR，再用该 PR 作为 launch convergence review 对象；若没有 PR 流程，必须有等价 diff/review artifact。
- 当前 `workflowctl.py pass-stage` 不支持该 gate，不得伪造 stage receipt，也不得把它提前建模成普通前置阶段。
- 该 gate 完成即 workflow 完成；不得从这里回流重写 PRD/AIP/contract/Atomic Issues。发现实现方不能自行决定的事项时，使用 `launch_decision_required` 与人确认后在本 gate 收口。

## Boundary And Composition Gates

模块契约图本身也必须被验证。不能只“列出模块”和“列出契约”，必须证明模块划分合理、模块组合后覆盖需求。

## No Subagent Workflow Discipline

AutoMQ 大需求 workflow 默认不使用 subagent。此前实践表明，在长上下文、多阶段 artifact 和 atomic task planning 场景中，subagent 容易放大上下文缺失、过早并行执行、污染任务树，并让主流程跳过硬门禁。

硬规则：

- 不启动 subagent 生成、审计或执行 workflow artifact。
- 不把 PRD/AIP/草案、Atomic Issue、verification、acceptance 或代码实现分派给 subagent。
- 所有 canonical artifact 必须由主 agent 基于落盘 canonical artifacts、context rehydration pack、validator 和 rubric 本地完成。
- 除 atomic execution 的 `pass-task` 前同步阻塞只读 task-local semantic review subagent 例外，所有“独立审计”改为主 agent 本地二次审计：重新打开对应 artifact，对照 checklist、`validate_artifacts.py`、rubric、browser/runtime evidence 检查，并把审计结果写入对应 artifact。
- 需要并行探索时，优先用 deterministic command、`rg`、脚本、测试、浏览器自动化和 validator，而不是 subagent。
- 如果上层系统或用户明确要求使用 subagent，也只能在本 workflow 外作为临时只读咨询；其输出不得进入 canonical artifact，且不能影响 pass/ready/done/accepted 结论。

唯一内置例外是 `atomic-execution-sdd` 的只读 reviewer：当前 Txxx 完成实现、验证和 `validate-task-diff` 后，必须启动一个只读 reviewer subagent 对照当前 Atomic Issue、当前 diff 和验证日志找 `contract-deviation`、`verification-insufficient`、`behavior-bug`、`diff-scope-risk`。该 subagent 不能改代码、不能生成/修改 artifact、不能签发 receipt、不能决定 done。主 agent 必须复核 findings，修复或 backflow，并把最终 review 结果写入 `task-semantic-review.yaml`；`workflowctl.py pass-task` 会拒绝缺失、阻塞、过期、或无明确 fallback reason 的 main-local review 记录。

该 reviewer 是同步阻塞 gate，不是并行执行 lane。启动 reviewer 后，主 agent 必须等待 final findings；等待期间不得 admit 后续 Txxx、不得修改业务代码、不得执行下一个 Atomic Issue、不得用部分输出签收当前任务。

默认本地审计 lane：

| Stage | Local audit lane | Focus | Blocking output |
|---|---|---|---|
| PRD / readiness | Source and current-state audit | 用户输入、补充链接、当前产品/代码现状是否被读取和消费 | 未读 source、PRD 当前理解缺证据、产品决策 open |
| AIP / new design | Engineering completeness and module-boundary audit | 工程 propose 是否归一化，模块边界是否可形成 contract-closed issue | ADEC/DEC open、module boundary evidence missing |
| Code archaeology | Boundary / reference / mode / runtime / action-route audit | 旧系统事实、字段矩阵、mode 继承、运行时链路、action 落点 | 旧 mode leakage、参考字段缺失、action landing 不明 |
| Frontend contract | Route/action/submit-flow audit | visible action -> route -> router -> landing component -> API/event -> feedback | 改错页面、submit 未触发 API、旧 mode UI 泄漏 |
| Cross-module contract | Provider/consumer and materialization audit | provider guarantee 是否满足 consumer assumption，契约能否复制进 Atomic Issue | consumer 无 provider、contract ID-only、mock drift |
| Verification matrix | Proof sufficiency audit | REQ/SCN/C/MIG 是否都有组合级、前端、mock、runtime proof | 用 service test 替代 UI/route/runtime proof、P0/P1 Not Run |
| Atomic task planning | Atomic issue independent rubric audit | Txxx 是否自包含、单模块、契约物化、验证可执行 | 任何 0 分、文件落点不明、verification expected result 缺失 |
| Atomic execution | Post-task diff and verification audit | 已完成 issue 的 diff scope、contract preservation、verification log | 需要新决策、diff 越界、验证未回写 |
| Mock acceptance | Backend / frontend / runtime freshness audit | 真实 controller/page 组合链路、mock drift、bundle/package/process freshness | mock 被测代码、无 browser/DOM 证据、stale runtime |
| Product acceptance | Action landing / runtime capability / backflow audit | 真实浏览器验收、创建后能力、产品语义冲突和最早回流阶段 | P0/P1 未关闭、未执行真实浏览器、回流 artifact 未更新 |
| Convergence retrospective | N1/N2 classification audit | 所有收敛项是否归因正确，N1 是否反哺 workflow/skill | N1 被归为 N2、Not Run leak 未关闭、skill 未更新 |

### Module Boundary Validation Gate

进入 `cross-module-contract-sdd` 前，模块边界必须验证：

- 每个模块有明确 owned state/data/resource。
- 每个模块内部状态机自洽，内部错误不会改变其他模块输入语义。
- 每个模块的外部依赖都能枚举成 consumed contract。
- 每个模块对外承诺都能枚举成 provided contract。
- 不存在明显过大模块：多个独立状态机、上下文不可自包含、核心类/资源过多。
- 不存在明显过小模块：两个模块契约过密、总是共改、无法独立产生 contract-closed issue。
- 每个 split/merge/keep 决策都有理由、反选方案和验证方式。

必需通过产物：

- `Module Boundary Validation`：证明每个核心模块的 ownership、state-machine self-containment、contract enumerability、too-large/too-small risk 和 keep/split/merge decision。
- 对应 `decision-reviews/design-decisions.md` 或 `decision-reviews/archaeology-decisions.md`：逐决策记录 split/merge/keep 的 alternatives、reason、verification。

### Module Composition Verification Gate

进入 `atomic-task-planning` 前，必须证明模块组合能满足需求：

- 每个 REQ/SCN 映射到一条或多条模块 provided contracts。
- 每条 consumed contract 都有对应 provider contract。
- provider 提供的 normal/failure/timing/consistency 语义满足 consumer 的假设。
- 每条跨模块路径有组合级验证，不能只靠模块内部单测。
- 存在端到端/集成/route/browser/runtime/manual 等 proof 证明关键用户场景由模块组合后成立。
- 如果某条用户场景只有模块局部验证，没有组合验证，只能记录 Not Run risk，不能宣布需求完成。

必需通过产物：

- `Module Contract Graph`：module -> owned state/data/resources -> provided contracts -> consumed contracts。
- `Provider/Consumer Assumption Matrix`：逐 contract 证明 provider guarantee 满足 consumer assumption；不匹配必须成为 locked decision 或 blocker。
- `Module Composition Verification Matrix`：REQ/SCN -> composition path -> provider contracts -> consumer assumptions -> verification -> expected result -> proves。
- `Requirement Composition Coverage`：每个关键 REQ/SCN 都能追溯到模块组合路径、provided contracts、verification 和 Atomic Issue。

这些表不是补充说明。缺少任一项时，不允许进入 `atomic-execution-sdd`。

## Contract-Closed Issue Last

所有阶段 artifact 都必须回答一个问题：它能否被可靠地压缩进后续 `atomic-issues/Txxx.md`，让 worker 不读完整全局文档也能执行？

规则：

- `proposal.md`、`spec.md`、`plan.md`、决策文档、契约、验证矩阵都是 Atomic Issue 的上游素材，不是最终目的。
- `tasks.md` 只是 Atomic Issue 索引、依赖顺序和初始状态，不承载执行语义或执行日志；task 状态和验证结果只能由 `workflowctl.py begin-execution/admit-task/validate-task-diff/pass-task`、`workflow-state.yaml.task_receipts`、`task-verification-log.yaml`、`task-semantic-review.yaml` 和适用的 `mock-acceptance-execution.yaml` 表达。
- 每个 Atomic Issue 必须像一个完整 GitHub issue：所属模块、模块职责、consumed contracts、provided contracts、背景、语义、范围、决策、代码参考、文件级步骤、验证和禁止事项齐全。
- 每个 Atomic Issue 必须物化契约，而不是引用契约：把执行前世界状态、已成立上游保证、必须交付给下游的保证、失败时如何判断都复制到 issue 内。
- `atomic-task-planning` 必须先建立 `Module-to-Issue Map`、`Contract Closure Coverage`、`Requirement Composition Coverage` 和 `Semantic Carrier Coverage`，再写 `atomic-issue-packets.yaml`。
- `atomic-issues/Txxx.md` 必须由 `atomic_issue_compile.py` 从 `atomic-issue-packets.yaml` 编译生成，不得手写 Markdown issue。
- 每个 packet 必须包含 `semantic_carriers`：字段矩阵、selector/default/auto-create、managed resource ownership、禁止 raw text、action route、错误/状态/默认值/时序、mock fixture 等密集语义必须逐项列出，并复制到执行章节。
- `atomic-task-planning` 必须建立 `Task DAG`：每个 issue 是 node，provider issue 先于 consumer issue，verification gate 先于依赖它的场景，并行任务必须文件不重叠、契约不依赖、失败不污染对方输入。
- 如果 Atomic Issue 需要实现者回读完整 `proposal/spec/plan` 才知道怎么做，任务不合格，必须回到 `atomic-task-planning` 或更早阶段补齐。
- 如果无法写出自包含 Atomic Issue，说明上游 PRD/AIP/考古/迁移/契约/验证仍有缺口；不得用“执行时再看全局文档”绕过。
- 进入 `atomic-execution-sdd` 前，必须确认每个 Atomic Issue 都可以单独创建为 issue 并独立派发。

### Atomic Planning Context Rehydration Gate

进入 `atomic-task-planning` 前，主 agent 必须从磁盘上的 canonical artifacts 重新恢复上下文，不能依赖聊天历史、压缩摘要或 subagent 记忆生成原子任务。

必须重新读取或等价核对：

- `source-intake-ledger.md`
- `proposal.md` / `spec.md`
- `plan.md`
- Decision Registry 和 `decision-reviews/*.md`
- code archaeology / new-feature design / migration diff 产物
- frontend contract、cross-module contract、verification matrix
- Backflow Invalidation Matrix，如存在
- mock acceptance / repo-specific acceptance runtime、runtime lifecycle、mode semantic、frontend action route、API flow DAG 等适用矩阵

必须生成或更新 `specs/changes/<change-id>/atomic-planning-context-pack.md`，作为从 canonical artifacts 到 Atomic Issues 的中间上下文包。它至少包含：

| Section | Required content |
|---|---|
| Source rehydration ledger | 每个 canonical artifact 的路径、读取时间、状态、是否参与任务生成 |
| Upstream semantic index | 所有 REQ/SCN/PDEC/DEC/C/MIG/VER 的可执行语义摘要和必须保留的 semantic carriers，不只是 ID |
| Module and contract pack | 模块边界、owned state、provided/consumed contracts、provider-consumer assumptions |
| Frontend/action pack | visible action、route builder、router definition、landing component/file、mode branch、forbidden inherited UI/API |
| Mock / acceptance runtime pack | mock 边界、真实契约来源、runtime lifecycle、progress/change、handoff QA 要求 |
| Verification pack | 每条 required verification 的命令/步骤、expected result、proves、failure meaning、environment owner |
| Task generation constraints | primary module 规则、文件范围、禁止事项、semantic carrier 到 issue/packet section 的映射、DAG/provider/consumer 顺序约束 |

如果 context pack 无法覆盖所有 required upstream object，或无法说明每个 dense semantic carrier 会进入哪些 Txxx packet section，`atomic-task-planning` 必须 blocked 并回流补 artifact；不得用“记得需求里说过”补齐。必须由主 agent 本地审计 context pack 是否完整，且不能用任何并行 agent 替主 agent 生成 context pack 或最终 Atomic Issues。

### Contract Materialization Gate

Atomic Issue 必须像 sealed execution packet。它不是“去读 C-001/T002 再实现”，而是直接说明：

- 执行当前任务前，世界已经应当是什么状态。
- 当前任务可以无条件依赖哪些 upstream facts。
- 当前任务必须为下游 consumer 保证哪些 observable facts。
- 哪些事实禁止重新决策、重新解释或绕过。
- 如果前提不成立，应该停止回流，而不是在实现阶段补猜。

每个非纯文档 issue 必须包含：

| Section | Purpose |
|---|---|
| Execution Preconditions | 按事实写明前置任务完成后已经成立的状态、schema、API、行为、测试证据 |
| Consumed Contract Snapshot | 复制 consumed contracts 的完整可执行语义：字段、状态、错误、时序、幂等、默认值、兼容边界 |
| Provided Contract Obligation | 复制当前任务必须交付给 downstream consumer 的保证和可观察输出 |
| Invariant Carryover | 当前任务必须保持不变的旧语义、兼容性、mode 行为、权限、错误、数据约束 |
| Forbidden Re-decisions | 明确本任务禁止重新选择的产品/架构/API/UI/状态/错误/路径决策 |
| If Preconditions Fail | 发现前提不成立时如何分类、回流、标记 blocked，而不是继续改代码 |

如果这些内容写不出来，不是“任务描述再润色”，而是上游契约没有锁定，必须回流到设计、契约或验证阶段。

### Dense Semantic Carrier Gate

任务规划时必须先识别 dense semantic carriers，再拆 Txxx。以下语义禁止压缩成一句自然语言摘要：

- selector/default/auto-create/default derived value/select-existing/read-only resolved display。
- managed/generated/default-created/select-existing external resource ownership：真实 provider/API 创建时机、资源 ID/name/tag、owned/existing provenance、持久化位置、runtime consumer、update/delete cleanup/protect、幂等、失败和验证。
- 禁止 raw text 主路径、禁止旧 mode 字段泄漏、禁止强绑定某现有资源。
- action -> route -> router -> landing component -> API/event -> feedback。
- explicit failure vs unknown/warning、错误码、field error、权限不足、不可达、空值和 unavailable。
- mock/provider fixture 状态、response shape、enum/status/progress/change/terminal state。
- runtime lifecycle、create/update/delete、cleanup、idempotency、partial failure、Not Run boundary。
- operation mutability：create-time 字段在 update/edit/save/resize/delete/recreate/migrate 中的 editable/read-only/hidden/disabled/unsupported/recreate-required/migrate-required 决策、产品原因、backend mutation owner、UI 表达和验证。
- runtime mode materialization parity：mode change classification、产品能力 baseline、runtime artifact/config/plugin/secret/bootstrap/entrypoint/readback 映射、禁止 resource-exists-only proof。

每个 carrier 必须在 `semantic-objects.yaml`、`contracts.yaml` 或 `task-dag.yaml` 中落为 `semantic_carriers`，并在 `atomic-issue-packets.yaml` 对应 Txxx 中出现。`workflowctl.py validate pre-execution` 和 `atomic_issue_compile.py --check` 失败时，不得把 `tasks.md` 标为 ready。`atomic_issue_compile.py --check` 只证明 packet 与 Markdown 同步，不是 pre-execution admission，也不能作为“先执行已闭合任务”的理由。

这是机器硬门禁，不是写作建议：`workflowctl.py` 会从 `REQ/SCN/DEC/C/T` 的 `semantics`、契约字段和任务 sources 中推导 dense semantics。只要文本出现 selector/default/auto-create/no raw text、managed/generated/existing external resource、explicit failure vs unknown、action route/API/feedback 等高密度语义，而对应对象或任务没有 `semantic_carriers`，pre-execution 必须 fail。把语义留在 `sources.excerpt`、`contract_excerpts` 或 `scope` 中不算通过。

对 ASG infrastructure selector，carrier 不能只写 “use selectors”。必须按任务职责裁剪但显式携带：VPC、Subnet、SecurityGroup/SG、IAM Role/Profile、InstanceType；selector/default/auto-create/select-existing/derived display；禁止 raw AWS ID/text box 普通主路径；空列表、权限错误、wrong parent、invalid existing candidate、unknown reachability warning/non-blocking；以及证明 UI render/DOM 或 service validation 的 verification。

对 managed external resource ownership，carrier 不能只写 “auto-create resources / managed resource / cleanup”。必须按任务职责裁剪但显式携带：selection mode、create timing、provider writer、resource identity、owned/existing provenance state、persistence owner、runtime/readback consumer、update rule、delete cleanup/protect rule、idempotency、provider/permission/quota/partial failure behavior，以及 provider mutation、ownership readback、cleanup/protect verification。该语义和 selector 语义不同；selector 任务不能关闭资源创建和 ownership 生命周期。

对 update/edit/save/resize/delete/recreate/migrate，carrier 不能只写 “active fields / active branch / submit update payload”。必须按字段携带 operation mutability decision：create-time meaning、runtime owner、update action required、product semantic、editable/read-only/hidden/disabled/unsupported/recreate-required/migrate-required、backend mutation owner 或 locked N/A、UI expression、negative assertion 和 verification。frontend issue 不能让未锁定为 editable 的字段提交；backend issue 不能实现未被产品语义锁定的 mutation。

典型 blocker：

- `REQ/PDEC/C` 说了 VPC/Subnet/SG/IAM/InstanceType selector/default/auto-create，但 Txxx 只写 “use provider selectors”。
- source 说了 auto-create/default-created/generated/select-existing external resource，但 Txxx 只写 selector/validation/resolvedConfig，没有 owner task 实现 provider create、resource ID persistence、owned/existing readback 和 delete cleanup/protect。
- frontend issue 不列 active/inactive fields、selector options、parent reset、submit payload、错误展示和跳转。
- frontend update/edit issue 复用 create fields，或只证明 payload exact-key，却没有字段级 mutability decision、backend mutation owner 或 locked N/A。
- mock issue 不列 fixture 对象、path/body/response shape、错误状态和 drift guard。

## 语言与产物规范

持久化 workflow 文档默认使用中文，包括 `proposal.md`、`spec.md`、`plan.md`、`tasks.md`、`decision-reviews/*.md`、`atomic-issues/Txxx.md`、`acceptance/*.md`。

例外：

- 代码标识、类名、字段名、API path、命令、错误码、枚举值、日志原文保留原文。
- 用户明确要求英文时才使用英文。
- 引用外部英文资料时可以保留原文摘录，但必须用中文解释其对决策或任务的影响。

## 方法论优先原则

本 workflow 可以复用 SDD 的 `proposal/spec/plan/tasks` 入口，但 SDD 只是文件容器，不定义 AutoMQ AI coding 的质量标准。

当 SDD 模板与 AI 原子能力要求冲突时，以 AutoMQ 方法论为准：

- 可以新增 `atomic-issues/`、`contracts/`、`verification/`、`archaeology/`、`frontend-contract/` 等文件。
- `plan.md` 可以作为导航索引引用额外文件，不必把所有内容塞进一个文件。
- `tasks.md` 只作为任务索引、依赖顺序和初始状态；每个可执行任务必须有独立 Atomic Issue。执行结果不得写回 sealed `tasks.md`。
- 产物是否合格不看“是否符合轻量 SDD 模板”，而看“是否把大需求转成 AI 可零决策执行的 atomic issues”。
- 不允许为了让 `validate_artifacts.py` 通过而只补章节标题；结构校验通过后仍必须按 rubric 做语义质量 review。

当需要生成或评审任何阶段 artifact 时，必须按 `ai-dev-methodology/references/artifact-completeness-spec.md` 检查对应 Stage 的 Goal、Orthogonal Dimensions、Required Artifacts、Completeness Criteria 和 Exit Gate。

强约束资源：

- 模板：`/Users/keqing/.codex/skills/ai-dev-methodology/templates/*.md`
- 输入账本：`/Users/keqing/.codex/skills/ai-dev-methodology/templates/source-intake-ledger.md`
- 代码范围发现：`/Users/keqing/.codex/skills/ai-dev-methodology/templates/code-scope-discovery.md`
- 用户决策交互：`/Users/keqing/.codex/skills/ai-dev-methodology/templates/user-decision-interaction.md`
- 工程 propose：`/Users/keqing/.codex/skills/ai-dev-methodology/templates/engineering-propose-intake.md`
- 语义消费：`/Users/keqing/.codex/skills/ai-dev-methodology/templates/semantic-consumption-matrix.md`
- 验证可行性：`/Users/keqing/.codex/skills/ai-dev-methodology/templates/verification-feasibility.md`
- 版本分支对齐：`/Users/keqing/.codex/skills/ai-dev-methodology/templates/version-branch-alignment.md`
- Rubric 评分：`/Users/keqing/.codex/skills/ai-dev-methodology/templates/artifact-rubric-scorecard.md`
- 执行 DAG：`/Users/keqing/.codex/skills/ai-dev-methodology/templates/task-dag.md`
- 回流失效：`/Users/keqing/.codex/skills/ai-dev-methodology/templates/backflow-invalidation.md`
- Rubric：`/Users/keqing/.codex/skills/ai-dev-methodology/references/artifact-review-rubric.md`
- 正反例：`golden-atomic-issue.md` / `bad-atomic-issue.md`
- 结构与语义门禁：`/Users/keqing/.codex/skills/ai-dev-methodology/scripts/validate_artifacts.py`

这些是 skill runtime 资源，不是目标仓库内置脚本。不得在目标 repo 内寻找 `workflowctl.py` / `validate_artifacts.py` 来判断它们是否可用；目标 repo 没有这些脚本不是降级理由。必须先用 `/Users/keqing/.codex/skills/ai-dev-methodology/scripts/...` 绝对路径运行。只有绝对路径文件不存在或不可执行，才算 skill runtime 工具缺失；此时只能 blocked 并报告，不能用 checklist 自审替代，也不能进入实现。

进入 `atomic-execution-sdd` 前，必须使用上述资源完成模板化、rubric review 和结构校验。

## 何时使用

Use when:

- 用户要从需求/AIP 开始做新功能。
- 用户要在已有代码上做大改动、重构、迁移或多模块功能。
- 用户要求按 AutoMQ `specs/changes` / SDD / spec 模式推进。
- 任务明显不是单个原子小需求。

Do not use for:

- 单文件、小 bug、原因已定位且无产品/架构决策的修改。
- 纯咨询，不需要持久变更文档的调研。

## 轻重流程裁剪

裁剪只能在 Step 1 原子边界判断时发生。一旦进入大需求 workflow，不允许为了省文档跳过硬门禁。

可走轻量路径的条件：

- 无产品决策。
- 无工程方案选择。
- 单 repo、单层变更。
- 不涉及跨模块契约、运行时资源、部署、前端用户语义或多版本。
- 验证闭环可在一个短命令/手工步骤完成。

否则必须走重型路径，并完整产出 Source Intake、Code Scope Discovery、PRD/AIP completeness、Semantic Consumption、Decision Registry、Contract、Verification、Task DAG、Rubric Scorecard 等门禁。轻量路径也不能绕过用户明确要求的持久文档。

## 核心模型

如果用户在讨论这套 workflow 的理论、模块圈定方法、`P^N`、`N1/N2`、收敛复盘或 skill 本身的优化，先读取 `ai-dev-methodology`。

大需求收敛来自两类 N：

- `N1`：模块内部子任务。通过正确模块边界、pattern、框架语义、每步验证，理论上应尽量不贡献收敛。
- `N2`：跨模块语义约束。由问题域决定，不可消除，是理论收敛下限；必须显式枚举和锁定。

本 workflow 的目的不是承诺“零收敛”，而是把收敛范围压缩到 `N2`。

## 决策文档纪律

这套 workflow 的输入通常从用户几句话开始。允许不确定性存在于需求讨论阶段，但不允许不确定性穿透到实现阶段。

全流程必须区分三类决策：

| Layer | Rule |
|---|---|
| 产品决策 | 必须由用户确认，或用户明确授权 AI 按推荐方案锁定；PRD 完成后不得残留 open product decision |
| 工程决策 | AIP、设计、考古、迁移、契约、验证阶段可以由 AI 在上层产品约束下自主决策；不得改变产品语义 |
| 实现决策 | 不允许；执行阶段发现新决策时暂停并回到对应阶段 |

每个阶段只要产生或修改决策，就必须同时产出独立阶段决策文档：

```text
specs/changes/<change-id>/decision-reviews/<stage>-decisions.md
```

并同步更新 `plan.md` 的 Decision Registry 和 Decision Document Index。

如果环境有 `lark-cli` 写权限，必须把阶段决策文档同步到飞书，并把 URL 回写到 Decision Document Index；如果失败，记录失败原因和后续命令。

阶段决策文档不是可选补充。它是防止“决策藏在段落里”“上下文压缩后丢失”“实现阶段重新猜”的强制 artifact。

决策文档必须逐决策展开。禁止把多个决策合并成 `PDEC-001..022`、`ADEC-001..004` 或“相关决策同上”这种摘要段。每个决策都必须独立记录问题、最终选择、反选方案、理由、产品约束对齐、影响模块、验证方式和下游 Atomic Issue 影响。

## 阶段地图

本 skill 只负责路由和闭环，不替代阶段 skill。

| 阶段 | Skill | 产物 | 目的 |
|---|---|---|---|
| 产品定义 | `product-requirement-design` | `proposal.md` / `spec.md` / `decision-reviews/prd-decisions.md` / PDEC | 锁定用户视角的功能、状态、错误、权限、验收 |
| AIP 编写 | `aip-template`；`writing-style` 仅用于 `aip.md` 正文 | AIP 文档 / `decision-reviews/aip-decisions.md` | 当 AIP 缺失时，按 AutoMQ AIP 模板产出设计文档；只有生成或改写 `aip.md` 正文时应用用户写作风格 |
| AIP 门禁 | `aip-readiness-review` | blocking questions / `decision-reviews/aip-decisions.md` / DEC | 锁定工程方案、接口、兼容、观测、验证策略 |
| 总门禁 | `requirement-readiness-review` | readiness verdict | 确认产品和 AIP 都足够进入工程阶段 |
| 决策账本 | `decision-registry` | `plan.md` Decision Registry | 贯穿全流程，禁止实现阶段临时决策 |
| 新设计 | `new-feature-design` | `spec.md` / `plan.md` / `decision-reviews/design-decisions.md` | 设计理想模块边界、领域模型、场景 |
| 旧代码考古 | `code-archaeology-sdd` | `plan.md` archaeology / `decision-reviews/archaeology-decisions.md` | 显式化旧系统事实、隐式约束、pattern、框架语义 |
| 差异迁移 | `migration-diff-analysis` | `plan.md` migration / `decision-reviews/migration-decisions.md` | 比较旧/新语义，决定 delete/keep/modify/add |
| 前端契约 | `frontend-contract-design` | `spec.md` / `plan.md` / `decision-reviews/frontend-decisions.md` | UI 字段、状态、交互、i18n、权限具体化 |
| 跨模块契约 | `cross-module-contract-sdd` | `spec.md` / `plan.md` contracts / module contract graph / `decision-reviews/contract-decisions.md` | 锁定 N2 语义约束和模块 consumed/provided contract |
| 验证矩阵 | `verification-matrix` | `plan.md` / `tasks.md` / `decision-reviews/verification-decisions.md` | 将每个需求/契约/迁移映射到证明方式 |
| 原子任务 | `atomic-task-planning` | `tasks.md` + `atomic-issue-packets.yaml` + `atomic-issues/Txxx.md` + `decision-reviews/task-planning-decisions.md` | 把锁定事实转成 per-task sealed context packet，再编译成可独立派发的 Atomic Issues |
| 原子执行 | `atomic-execution-sdd` | code + `task-verification-log.yaml` + `task-semantic-review.yaml` + `workflow-state.yaml.task_receipts` | 先 `begin-execution`，每个 task 先 `admit-task`，改完跑 `validate-task-diff`、task-local semantic review 和 `pass-task` |
| 严格 Mock Acceptance | `mock-acceptance-gate` | sealed mock matrix/case artifacts + `mock-acceptance-execution.yaml` + `mock-acceptance.md` / verification log / backflow updates | 把 mock acceptance / repo-specific acceptance runtime 作为一等交付物，用真实前后端用户流程和严格外部契约 mock 验证组合逻辑 |
| 产品验收 | `product-acceptance-review` | `acceptance/product-acceptance-review.md` | 部署后用真实浏览器和运行时证据发现产品语义冲突、mode 泄漏、状态不一致和验收缺口 |
| 上线收敛评审 | Post-Atomic Launch Convergence Gate | `launch-readiness-review.md` + PR/diff review findings + resolution evidence + human launch decisions | 以生产上线标准评审集成 PR 或等价 diff，区分实现缺口、原子任务缺口、最终上线决策、验收缺口和允许的实现差异；`workflowctl.py validate-launch-readiness specs/changes/<change-id>`；当前 `workflowctl.py pass-stage` 不支持该 gate，不得伪造 stage receipt |
| 收敛复盘 | `convergence-retrospective` | retrospective actions | 区分 N2 下限和 N1 可消除缺口，反哺 current/skill |

## 前置输入

优先要求已有：

1. 需求文档：用户视角的产品行为、范围、非目标、状态、配置、错误语义、用户可见决策。
2. AIP：工程设计决策、方案取舍、接口、依赖、兼容性、观测性、落地计划。

如果产品需求缺失，先走 `product-requirement-design`。
如果用户给了已有需求文档、飞书文档、issue、PRD 草稿、标题或对话描述，也先走 `product-requirement-design`。这些输入一律只是 Propose / Source，不是最终 PRD；真正 PRD 必须由 workflow 重新生成。
如果用户给了补充设计文档、Terraform/API 设计、接口草案、飞书链接或历史方案，这些必须作为 PRD/AIP normalization 的 evidence 输入读取并登记；不得只凭原始 PRD 或现有代码推断。未读取用户提供的补充链接时，不得进入实现。
如果需求依赖外部事实或领域知识，PRD 阶段只能锁定用户语义和产品决策；外部系统真实能力必须进入 `external-capability-research.md`，在 AIP/design 锁定前完成调研和消费。不得用未验证外部假设锁定 ADEC/DEC、契约、mock 或 Atomic Issue。
写 PRD 前必须做与 Propose 相关的当前项目现状理解，产出 `Current Product/Code Understanding`，覆盖相关页面/API/配置/状态/错误/权限/运行时能力及 evidence path。没有该理解，不得生成 locked PRD。
当前项目现状理解必须按 `Code Scope Discovery` 执行：从 propose seed 出发列搜索词/路径、搜索覆盖、证据和停止条件。没有 stop condition evidence，不得声称 PRD 现状理解完成。
如果 AIP 缺失，先用 `aip-template` 写 AIP，再走 `aip-readiness-review`。`writing-style` 只在生成或改写 `specs/changes/<change-id>/aip.md` 正文时使用；不得用于 PRD、readiness review、plan、YAML sidecar、Atomic Issue、代码或其它阶段产物。
生成 `aip.md` 前必须读取 `/Users/keqing/.codex/skills/aip-template/references/steering.md`。`aip.md` 必须保留 AutoMQ AIP 标准模板结构；工程完整度内容只能填入对应章节或作为子表扩展，不能用自定义 engineering outline 替换模板标题。
如果 AIP 已有、接口草案/Terraform/API 设计已有，也一律先视为 Engineering Propose；必须用 `aip-readiness-review` 做 Engineering Propose Extraction、Current Architecture Understanding 和 Engineering Decision Completeness Gate，不能直接当 locked AIP。
如果两者都有但不确定是否可执行，走 `requirement-readiness-review` 做总门禁。

所有入口输入必须先进入 `Source Intake Ledger`。用户提供的 PRD、AIP、飞书链接、issue、补充设计、Terraform/API 草案、历史方案、代码路径、运行时证据，都必须登记读取状态、读取方式、下游映射和冲突。存在 behavior-affecting source 未读或 blocked 时，不得进入设计、契约、任务规划或实现。

PRD normalized 之后、AIP/design 锁定工程方案之前，如果需求涉及云资源、K8s/Helm/Terraform/IAM/network/storage/compute/runtime、第三方 API/SDK、官方协议、autoscaling/scheduling/lifecycle、metrics/logs/events 或 mock acceptance / repo-specific acceptance runtime 外部依赖，必须创建：

```text
specs/changes/<change-id>/external-capability-research.md
```

并使用 `external-capability-research.md` 模板登记官方文档/SDK/API/真实 adapter/source、外部能力事实、不支持/限制、External Mechanism Decision Matrix、约束、设计影响和 mock acceptance / repo-specific acceptance runtime 边界。任何影响设计的外部事实或机制映射必须进入 ADEC/DEC、C、VER、semantic_carrier 和 owner packet，或有 locked N/A / Not Run。没有调研消费闭环时，不得进入 AIP readiness passed、new-feature-design、cross-module-contract 或 atomic-task-planning。

从 PRD 生成后开始，所有阶段必须维护 `Semantic Consumption Matrix`。上游 `REQ/SCN/PDEC/DEC/C/MIG/VER` 不能只靠 ID 被后续引用，必须在每个阶段证明被消费、派生、复制、验证或明确丢弃。任何 `blocked`、无理由 dropped、或只引用 ID 不复制语义的行，都阻塞下一阶段。

## 工作流

### Step 0: 读取上下文

如果在 `automq-workspace` 中工作，先按 `automq-sdd` 规则读取：

- `catalog.md`
- `context/agent-guide.md`
- `specs/README.md`
- `specs/contract/spec-contract-v0.1.md`
- 目标仓库 `.agents/` 或 fallback context

如果不在 workspace 中，也要尽量将持久产物映射为 `proposal/spec/plan/tasks` 四类。

必须创建或更新：

```text
specs/changes/<change-id>/source-intake-ledger.md
```

并使用 `source-intake-ledger.md` 模板登记 Source Inventory、Source To Semantic Object Map 和 Source Conflict Matrix。未读输入不能作为事实使用；冲突未决不能进入 Atomic Task Planning。

### Session Resume Identity Gate

这个 gate 的优先级高于任何新建 worktree / branch 的隔离动作。每次上下文压缩恢复、新 session 继续、当前目录不确定、或用户说“继续/监控/看看当前执行”时，必须先判断是否已有同一需求的 active change，而不是直接创建新 worktree。

必须先执行只读发现：

- `git worktree list`
- 在当前 repo 和 `/Users/keqing/.codex/worktrees/*/<repo-name>` 下查找 `specs/changes/*/workflow-state.yaml`
- 同步读取候选 change 的 `source-intake-ledger.md`、`proposal.md` / `spec.md`、`plan.md` 中的 source title/doc id、base branch、base commit、branch name 和 worktree path

如果候选 change 与当前用户需求匹配，必须切回该 worktree 和 change-id 继续；当前 cwd 不是该 worktree不构成重新开局理由。只有确认没有 active change，或用户明确说“重新开始/废弃旧执行/从头新建”，才允许创建新 worktree、branch 或 change-id。无法唯一判断时报告候选清单并停止，不得自行开新 worktree。

必须把恢复结果写入或追加到 `source-intake-ledger.md#Session Resume Identity Gate` 或 `plan.md#Session Resume Identity Gate`。如果这个 gate 没有通过，不得读取业务代码、生成新 artifact、进入任务规划或实现。

### Step 1: 原子边界判断

判断请求是否已是原子任务。全部满足才可直接实现：

| 条件 | 判断 |
|---|---|
| 零决策 | 产品、架构、字段、错误、UI、兼容性决策已锁定 |
| 单层变更 | 只改后端/前端/DB/部署/文档中的一层 |
| 上下文自包含 | 所需代码和规则能装进当前上下文 |
| 验证闭环短 | 有快速编译/测试/lint/渲染/手动验证 |
| 错误不传播 | 做错不会污染其他任务输入 |

若任一不满足，进入大需求流程。

### Step 2: 产品需求和 AIP 门禁

按缺口选择门禁：

1. 没有清晰产品需求：调用 `product-requirement-design`。
2. AIP 缺失：调用 `aip-template` 产出 AIP；只有写 `aip.md` 正文时调用 `writing-style`。
3. AIP 不完整或工程决策未锁定：调用 `aip-readiness-review`。
4. 产品需求和 AIP 都存在：调用 `requirement-readiness-review` 做总门禁。

缺失 AIP 时，生成的 `specs/changes/<change-id>/aip.md` 必须包含并保持 `aip-template` 的标准标题顺序：

```text
# AIP（AutoMQ Improvement Proposal）模板
## AIP 元信息
## 评审记录
## AIP 正文结构
### 1. 背景
### 2. 问题定义
### 3. 调研论证
### 4. 解决方案
### 5. 原型设计
### 6. 接口设计
### 7. 依赖选型
### 8. 方案详情
### 9. 兼容性问题
### 10. 被拒绝的其他方案
### 11. 落地计划
## AIP 验收
### 发布验收
### 上线验收
```

如果工程完整度需要 Background / selected architecture / data-state-task / observability / verification 等维度，必须作为上述章节内的子表或小节出现，不能替换 AIP 标题结构。

总门禁检查：

- 产品行为是否明确。
- AIP 工程决策是否明确。
- 还有哪些 blocking open questions。
- 是否需要 `spec.md`、`plan.md`、`tasks.md`。

阻塞问题未解决前，不进入考古或实现。

产品需求从几句话或对话开始时，必须先让 `product-requirement-design` 把对话输入登记为 source，输出 Propose Extraction、待决策清单和推荐决策；用户确认或授权 AI 决策后，才能写 locked PRD。

产品需求从已有文档开始时，必须先把原文当作 Propose 标准化成新的 PRD，而不是直接接受原文完整度。标准化必须包含 source trace、gap extraction、decision extraction。

产品需求依赖外部知识时，PRD 只记录“哪些产品语义依赖外部事实”；具体外部能力事实、官方机制/API/resource、产品语义到外部机制的字段映射、不等价/不支持语义、版本/区域差异、失败/权限/指标缺失语义、mock 来源和设计影响必须写入 `external-capability-research.md`，并在 AIP/design 前消费到 ADEC/DEC/C/VER。

PRD 完成前必须通过 PRD Completeness Gate：Propose extraction、Current Product/Code Understanding、用户/场景、对象模型、scope/non-goals、配置、状态、错误、权限、兼容、运行时生命周期、验收场景和产品决策锁定均完整。任一 `Blocks next stage=yes` 的 incomplete 维度阻塞 AIP、设计、考古、契约、验证和任务规划。

如果用户没有明确授权 AI 做产品决策，必须产出 `User Decision Interaction`，把每个 PDEC 的推荐方案、备选、影响、验证和用户响应落盘。无响应或模糊响应保持 `open`，阻塞 PRD 完成。

### Step 3: 初始化 Decision Registry

调用或维护 `decision-registry`：

- 产品决策登记为 `product`。
- AIP 取舍登记为 `architecture/interface/validation`。
- 后续考古、迁移、契约阶段发现的选择继续追加。
- 任何 `open` 决策都阻塞实现。
- 每个阶段产生的决策都必须同步写入对应 `decision-reviews/<stage>-decisions.md`。
- 工程阶段 AI 自主决策必须标注为 `ai-engineering`，并证明不改变产品语义。
- 每个决策必须有 `Decision key`，用于识别同一语义问题。
- 必须维护 Decision Consistency Matrix；两个 active locked 决策不能用同一 key 给出冲突结论。
- 修改 locked 决策时必须 supersede 旧决策，并触发 Backflow Invalidation Matrix。

### Step 3.2: 版本分支对齐门禁

如果需求涉及多仓库、控制面/数据面版本、Terraform/IAC、测试编排、控制面应用、kernel 镜像、部署模板或测试环境，必须先使用 `automq-version-branch-alignment` 并产出 `Version Branch Alignment Matrix`。

任何 `Aligned?=no` 且影响实现或验证的项，必须先路由到 owning repo 或作为 blocker；不得进入 atomic task planning。

### Step 3.5: Open Decision Review Doc

如果 workflow 启动后出现阻塞实现的 `open` 决策、blocking question、`needs-human-decision` 契约，不能只把它们留在 `plan.md` 或聊天里。

必须额外产出一份“决策评审文档”，用于人类评审和锁定决策：

1. 在 `specs/changes/<change-id>/decision-review.md` 写本地 Markdown 源文件。
2. 使用 `lark-cli` 创建飞书文档，优先创建到用户个人知识库：

```bash
lark-cli docs +create --title "<需求名> 决策评审" --markdown @specs/changes/<change-id>/decision-review.md --wiki-space "7460028547143417875" --as user
```

3. 将飞书链接回写到 `proposal.md` 或 `plan.md` 的 Blocking/Open Decision 区域。
4. 在最终回复中提供飞书链接和本地源文件路径。

决策评审文档必须包含：

| Section | Required content |
|---|---|
| 背景与参考输入 | 需求/AIP/spec/代码考古来源 |
| 现有实现参考 | 如果决策涉及已有系统能力，必须对照当前代码 pattern，而不是只按 AIP 推断 |
| 决策清单 | 每个 DEC/BQ/contract gap 单独成节 |
| 推荐决策 | 明确写出推荐选项，不能只列问题 |
| 推荐理由 | 结合产品语义、现有代码、实现复杂度、兼容性、验证方式 |
| 不推荐方案 | 写清备选方案和拒绝原因 |
| 实现影响 | 指向会影响的模块、API、DB、前端、任务、测试 |
| 待确认问题 | 汇总进入实现前必须由人确认的最小问题 |

如果 `lark-cli` 不可用或认证失败，仍必须先生成本地 `decision-review.md`，并在回复中说明未创建飞书文档的原因和后续需要执行的命令。

### Step 4: 选择路径

| 场景 | 路径 |
|---|---|
| 全新能力，旧代码只提供参考 | `new-feature-design` → UI touched then `frontend-contract-design` → `cross-module-contract-sdd` → `verification-matrix` → `atomic-task-planning` |
| 已有代码大改、迁移、重构 | `code-archaeology-sdd` → `new-feature-design` → `migration-diff-analysis` → UI touched then `frontend-contract-design` → `cross-module-contract-sdd` → `verification-matrix` → `atomic-task-planning` |
| 已有 accepted spec，只缺执行 | 确认无 open decision → 运行 `workflowctl.py validate pre-execution` + `validate_artifacts.py` → 通过后读取 `tasks.md` 和编译生成的 `atomic-issues/Txxx.md` → `atomic-execution-sdd` |

若涉及前端页面、表单、路由、i18n、权限按钮、状态展示，`frontend-contract-design` 是强制阶段。

若需求涉及云资源、部署模式、控制面创建流程，或出现“参考现有 X / 与 X 类似 / 从 X 推导配置”，`code-archaeology-sdd` 必须产出参考实现字段矩阵；`product-requirement-design` 必须锁定参数归属；`cross-module-contract-sdd` 必须锁定 Derived Configuration 契约。缺任一项时不得进入 `atomic-task-planning`。

若需求需要 mock acceptance / repo-specific acceptance runtime 支撑开发、验收、demo 或不上云验证，必须在 `cross-module-contract-sdd` 前明确生产外部边界，并在后续阶段强制产生：

| Required stage | Mandatory artifact |
|---|---|
| cross-module-contract-sdd | Production-vs-Acceptance Boundary Matrix；生产实现必须调用的外部 adapter / API / resource 副作用，以及验收适配器只能替代的物理外部依赖 |
| verification-matrix | Mock Drift Guard；path/body/response/enum/state/error/progress/terminal semantics 验证 |
| atomic-task-planning | 独立 mock acceptance / repo-specific acceptance runtime Atomic Issue，或在同模块 issue 中显式包含 mock 文件与验证 |
| atomic-execution-sdd | 业务代码和 mock 代码一起实现并执行短闭环测试 |
| mock-acceptance-gate | backend composition + frontend user-flow + contract drift guard 全部通过 |
| product-acceptance-review | mock 展示环境只在自动化验收后用于人工语义检查 |

缺少 mock artifact 时，不得宣布 no-cloud acceptance 完成。

若目标仓库定义了 repo-specific acceptance runtime，设计到实现前不得读取当前 runtime 代码、
runtime reference、验收适配器实现、packaged 启动或 runtime fixture graph 细节，
除非当前需求本身就是修改 该 runtime module。
实现前只允许锁定生产路径和待验收维度：真实 frontend/API client/controller/DTO/service/
manager/task/repository 必须执行，外部 adapter/API/resource 副作用必须由生产实现触发。
repo-specific runtime architecture facts 必须推迟到 `mock-acceptance-gate`、product acceptance 或 runtime owner task 中重新读取。没有后置读取和验收审计时，不得宣布 no-cloud acceptance 完成。

mock acceptance / repo-specific acceptance runtime 路径还必须执行本地审计 lanes：contract source/drift、frontend user-flow、backend flow DAG、fresh runtime evidence。未完成任一适用 lane 时，mock acceptance 状态必须是 blocked；不得继续刷新 repo-specific acceptance runtime 作为人工验收入口。任一 lane 输出 P0/P1 blocker 时，必须回流到对应 artifact，不能继续刷新 repo-specific acceptance runtime 做人工验收。

若需求的真实用法由多个后端接口、异步任务、状态查询、外部依赖或创建后操作按时间顺序组合而成，必须执行 Backend API Flow DAG Composition Gate：

| Required stage | Mandatory artifact |
|---|---|
| verification-matrix | API Flow Graph、Edge Contract Matrix、Path Coverage Matrix、State/Time Assertion Matrix、Orthogonal Dimension Matrix |
| atomic-task-planning | 独立 backend composition acceptance issue，或 mock acceptance issue 中的 DAG 组合验收章节 |
| mock-acceptance-gate | 按 DAG path coverage 执行 backend composition acceptance |
| product-acceptance-review | 对照 list/detail/progress/status/runtime 等 API 与 UI 状态一致性 |

缺少 API Flow DAG 时，不得用“接口单测都通过”声明后端组合逻辑完成。

若需求新增或修改 deployment/runtime/compute/storage/network mode，必须按“同级模式”处理，而不是把新 mode 当成旧 mode 的子分支：

| Required stage | Mandatory artifact |
|---|---|
| product-requirement-design | 同级模式差异矩阵 |
| requirement-readiness-review | mode readiness gate |
| code-archaeology-sdd | 旧模式语义继承审计 |
| frontend-contract-design | mode-specific UI 契约 |
| cross-module-contract-sdd | mode-specific API/task/cloud/status/log/event contracts |
| verification-matrix | Mode Runtime Acceptance Gate |
| product-acceptance-review | 产品语义验收矩阵 + Mode Semantic Checks |

缺少任一 artifact 时，不得进入 `atomic-task-planning` 或 `atomic-execution-sdd`。旧 mode 的 UI、事件、状态、日志、Worker、Endpoint、Metrics、插件验证、云资源字段、任务状态机不能默认继承；每一项必须有 evidence 证明 same，或在 PRD/契约中定义 different/unavailable。

若需求涉及云资源、异步任务、创建后操作、observability 或运行时自动调节能力，必须额外执行 Runtime Lifecycle Gate：

| Required stage | Mandatory artifact |
|---|---|
| product-requirement-design | 运行时能力与生命周期矩阵 |
| code-archaeology-sdd | Runtime Lifecycle Archaeology |
| cross-module-contract-sdd | Runtime Lifecycle / Runtime Auto-Adjustment / Observability contracts |
| verification-matrix | Runtime Lifecycle Verification Gate，auto-adjust-load 如适用 |
| atomic-task-planning | create/update/delete/failure/observability/auto-adjust 独立 Atomic Issues |
| product-acceptance-review | Runtime Capability Checks |

缺少任一 artifact 时，不得把创建后能力判定为完成。创建成功不能替代删除、修改部署配置、指标链路或自动调节验收。运行时自动调节能力声称支持时，必须有压力触发或等价运行时证据；没有证据只能记录 Not Run risk。

### Step 4.5: 产品验收回流

实现、部署和验证完成后，必须根据风险决定是否执行 `product-acceptance-review`。以下情况强制执行：

- 新增或修改 deployment/runtime/compute/storage/network mode。
- 触达前端页面、表单、详情、进度、日志、Worker、Endpoint、Metrics 或权限入口。
- 触达异步任务、change tracking、云资源或运行时状态。
- 触达创建后操作、删除、observability 或运行时自动调节能力。
- 用户需要验收部署环境。

产品验收发现问题时，不能默认直接改代码。必须按最早缺失阶段回流：

| Finding root | Required backflow |
|---|---|
| `prd-missing-decision` | 更新 PRD / Decision Registry，然后重跑设计、契约、验证、任务 |
| `aip-design-gap` | 更新 AIP/设计决策，然后重跑契约、验证、任务 |
| `archaeology-missed-old-semantics` | 更新考古和 mode inheritance audit，然后重跑迁移/契约/验证/任务 |
| `frontend-contract-gap` | 更新前端契约和决策文档，然后重跑验证/任务 |
| `cross-module-contract-gap` | 更新跨模块契约，然后重跑验证/任务 |
| `verification-gap` | 更新 verification matrix 和 atomic issue 验证 |
| `implementation-bug` | 更新任务验证后修实现 |
| `deployment/runtime-data-gap` | 修部署/环境数据并重新 smoke/验收 |

回流后必须重新部署并重新执行受影响的 verification 和 product acceptance。P0/P1 产品语义问题未关闭时，不得宣布完成。

任何回流都必须创建或更新 `Backflow Invalidation Matrix`：

- 记录 finding、最早缺失阶段和 required backflow。
- 标记失效的 proposal/spec/plan/tasks/atomic-issues/acceptance。
- 标记 superseded DEC/C/T/VER。
- 标记哪些 Atomic Issues 需要重写，哪些 verification 需要重跑。

旧 DEC/C/T/VER 被 superseded 后，仍被 active Atomic Issue 引用时，执行必须阻塞。

### Step 4.6: 严格 Mock Acceptance 最终门禁

实现完成后、展示环境刷新或产品验收结论前，如果需求可以或必须通过 mock 做不上云验收，必须使用 `mock-acceptance-gate`。

本门禁不能只启动 packaged/browser runtime 看页面。它必须先完成自动化和可重复验证：

- 后端真实 controller / DTO / service 组合链路，从用户视角覆盖 create/check/detail/progress/workers/metrics/update/delete/retry 和失败分支。
- 前端真实页面或等价 DOM/browser user-flow，覆盖 mode 切换、表单输入、下一步、提交按钮、API method/path/body、错误展示和成功跳转。
- 外部云/orchestrator/provider/instance/runtime/metrics mocks 必须有 API 规范或事实 evidence，并由 simulator / fixture / guard script 约束。
- 前后端 contract drift guard 必须覆盖 path、request body、response shape、enum/state、error code、progress/change status、terminal state、空值/不可用语义、mode-specific 字段。
- 任何核心用户流程只测 service fixture、payload fixture、静态类型或 source grep，都只能算 partial proof，不能关闭 frontend/browser acceptance。
- 对 automqbox/CMP Connect 功能，必须额外完成 `CMP Playground Coverage Matrix`，覆盖 Connect 功能域完整生命周期和 CMP 全局 top-level 入口；缺 progress/change、submit-flow 或任一核心 top-level smoke 时，不得声明 playground ready。automqbox 非 Connect 功能不得生成该矩阵；其他定义了 repo-specific acceptance runtime 的仓库必须提供等价 coverage matrix，不能套用 CMP playground artifact。

mock acceptance / repo-specific acceptance runtime 代码必须和业务代码一起纳入完成标准：

- `tasks.md` 和 Atomic Issue 中必须列出 mock 文件、fixture、simulator、handler、coverage script 或 browser mock route。
- 如果真实服务有 externalize/normalize/adapter 层，mock 必须复用或等价实现该外部契约，不能直接暴露内部 entity/state。
- 如果 mock 需要与真实实现不同，必须有 locked decision 和用户可理解的验收边界说明。
- 如果 mock 与真实契约不一致，mock acceptance 失败；修复优先级按影响的用户流程 severity 判定。

发现 bug 或验收缺口时，必须执行 loop review：

1. 分类根因：`frontend-contract-gap`、`cross-module-contract-gap`、`verification-gap`、`implementation-bug` 或 `deployment/runtime-data-gap`。
2. 更新 `Backflow Invalidation Matrix`、`Verification Matrix`、sealed task planning artifact 或 execution log、受影响 Atomic Issue 和 acceptance 文档；若需要改 `tasks.md`，必须重新 pass task-planning 并重新 `begin-execution`。
3. 修复代码或 artifact。
4. 重新运行受影响 backend/frontend/mock acceptance。
5. 重新 build/package/restart 环境，并证明运行环境加载了最新产物。

展示环境只能在自动化 mock acceptance 通过后作为人工验收入口。若用户在后端打包产物提供的静态资源端口验收，前端修改后必须重新构建前端、重新生成承载静态资源的后端 package/image 并重启对应进程；只跑前端构建不会更新已经运行的后端静态资源。

### Step 5: 产物映射

最终 reviewable state 必须落到 `specs/changes/<change-id>/`：

| 内容 | 目标文件 |
|---|---|
| 为什么做、范围、非目标、required files | `proposal.md` |
| 用户可见行为、接口契约、场景、成功标准 | `spec.md` |
| 技术方案、模块边界、考古结论、差异迁移、验证策略 | `plan.md` |
| 任务索引、执行顺序 | sealed `tasks.md` |
| 执行状态、task receipt、verification log、semantic review、mock row evidence | `workflow-state.yaml` / `task-verification-log.yaml` / `execution-state.yaml` / `task-semantic-review.yaml` / `mock-acceptance-execution.yaml` |
| 可独立执行的原子任务正文 | `atomic-issues/Txxx.md` |
| 产品语义验收、浏览器/runtime evidence、回流问题 | `acceptance/product-acceptance-review.md` |

若阶段 skill 产生 `.kiro/steering` 或 `docs/design` 风格内容，必须同步或转换到上述文件，不能只留在辅助文档里。

### Artifact Acceptance Criteria

产物不是“写完文档”即合格，必须满足：

| Artifact | 合格标准 |
|---|---|
| `proposal.md` | scope/non-goals/required files 清楚，能解释为什么做和不做什么 |
| `spec.md` | 每个用户可见行为有 REQ/SCN/SC，状态、错误、权限、兼容语义明确 |
| `plan.md` | 模块边界、Decision Registry、考古、迁移、契约、验证矩阵能支持任务拆分 |
| `tasks.md` | 只是任务索引；每个任务必须链接一个 self-contained `atomic-issues/Txxx.md` |
| `atomic-issue-packets.yaml` | 每个 Txxx 的 per-task sealed context packet；sources、semantic_carriers、decisions、contract excerpts、execution preconditions、consumed snapshots、provided obligations、invariants、verification、failure backflow 必须完整 |
| `atomic-issues/Txxx.md` | 必须由 `atomic_issue_compile.py` 从 packet 编译生成；可以直接作为 GitHub issue 独立派发；不读完整全局文档也能独立执行 |

任一 artifact 不满足合格标准时，不进入下一阶段。

详细完整度标准以 `ai-dev-methodology/references/artifact-completeness-spec.md` 为准；本表只是入口级摘要。

### Pre-Execution Hard Gate

进入 `atomic-execution-sdd` 前必须满足：

- `Source Intake Ledger` 已覆盖所有输入，没有 behavior-affecting unread/blocked source。
- `Code Scope Discovery` / `Current Product/Code Understanding` 已覆盖 PRD 相关当前项目现状。
- 若有未授权 AI 产品决策，`User Decision Interaction` 已锁定所有 PDEC。
- 若有工程 propose/AIP/接口草案，`Engineering Decision Completeness Gate` 已通过。
- `Semantic Consumption Matrix` 已覆盖所有上游 REQ/SCN/PDEC/DEC/C/MIG/VER，没有 blocked 或无决策 dropped 行。
- Decision Consistency Matrix 没有 open conflict。
- 若涉及多仓/版本/部署模板，`Version Branch Alignment Matrix` 全部 aligned 或明确 N/A。
- `Verification Feasibility Gate` 已确认 required verification 的环境/fixture/owner；阻塞 Not Run 未被当作 done。
- `Artifact Rubric Scorecard` 无 0 分；1 分必须修复到 2 分，或有用户/明确 owner 本轮显式接受的风险记录。
- 每个 Atomic Issue 的正文为中文，代码/API/命令标识除外。
- 每个 required dense semantic carrier 已从 `semantic-objects.yaml` / `contracts.yaml` / `task-dag.yaml` 追踪到 `atomic-issue-packets.yaml`，并复制到实际执行章节。
- 已完成 Module Boundary Validation Gate。
- 已完成 Module Composition Verification Gate。
- 已完成适用阶段的本地审计 gate；审计结果已写入对应 artifact，且无未关闭 blocker。
- 若需求涉及 mock acceptance / no-cloud acceptance / repo-specific acceptance runtime，已完成 Production-vs-Acceptance Boundary Matrix、Mock Drift Guard 和 mock Atomic Issue 拆分。
- 若需求涉及多接口后端用户流程，已完成 API Flow DAG、Edge Contract Matrix、Path Coverage Matrix、State/Time Assertion Matrix 和 backend composition acceptance issue 拆分。
- 已完成 Contract Materialization Gate；每个 Atomic Issue 的 Execution Preconditions、Consumed Contract Snapshot、Provided Contract Obligation、Invariant Carryover、Preconditions Failure Handling 均为可执行事实和义务，不是 ID、标题或一句摘要。
- 已完成 `Task DAG` 和拓扑顺序校验。
- 已生成 `atomic-issue-packets.yaml`，并运行 `atomic_issue_compile.py specs/changes/<change-id> --check` 确认 `atomic-issues/Txxx.md` 与 packet 同步。
- 已完成 `Backflow Invalidation Matrix` 校验；没有 active issue 引用 superseded DEC/C/VER。
- 每个 Atomic Issue 绑定 exactly one primary module；跨多个模块时必须拆分，除非它是纯 contract verification issue。
- 每个 Atomic Issue 声明 consumed contracts，并说明本 issue 假设这些契约成立。
- 每个 Atomic Issue 声明 provided contracts，并说明本 issue 要为其他模块提供或维护什么契约。
- 每个 Atomic Issue 的 Source Context 复制了必要语义，不只是 REQ/SCN/DEC/C ID 或一句摘要。
- 每个 Atomic Issue 的 Locked Decisions 复制具体决策及本任务影响，不引用“见 Decision Registry”。
- 每个 Atomic Issue 的 Contract Excerpts 包含 Trigger、Normal、Failure、Consistency、Timing、Verification；不能只写 contract 名称。
- 每个 Files To Change 都是可定位路径或明确的文件发现规则；不得只有 “new helper under ...” 这类开放范围。
- 每个 Implementation Step 都是文件级、顺序化步骤；不得要求实现者自行选择字段名、错误码、UI 表现、事务边界或验证方式。
- 每个 Verification 都包含可执行命令/步骤、具体 expected result、证明对象和失败含义。
- Not Run 中 P0/P1 或 `Blocks done=yes` 的项目必须阻塞 done。
- 每个阶段决策文档逐决策展开，没有 range 合并。
- `validate_artifacts.py` 必须通过。若怀疑误报，只有用户或明确 owner 在本轮显式批准后才能记录为 risk-accepted；agent 不得自判误报并继续。任何误报批准都不能绕过 `workflowctl.py validate pre-execution`，也不能允许在 gate 失败时修改 `specs/changes/<change-id>` 之外的文件。

### Step 6: 实现纪律

实现阶段：

- 进入 `atomic-execution-sdd` 前必须先运行 `python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py validate pre-execution specs/changes/<change-id>` 和 `python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/validate_artifacts.py specs/changes/<change-id>`。
- 任一失败时，必须回流到 `atomic-task-planning` 或最早缺失阶段；不得读取手写 Markdown-only issue 开始改代码，也不得修改 `specs/changes/<change-id>` 之外的文件。
- 两个 pre-execution gate 都通过后，必须运行 `python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py begin-execution specs/changes/<change-id>`；没有 `execution_receipt` 时不得修改业务文件。
- 各阶段完成时不能手工编辑 `stage_status` 为 `passed`；必须运行 `python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py pass-stage <stage> specs/changes/<change-id>`。该命令会先运行阶段 validator 和 `validate_artifacts.py --stage <stage>`，再写入 `stage_status` 和 `stage_receipts`。如果后续修改了被签收 artifact，hash 会失效，必须重跑 `pass-stage`。
- 缺少结构化 sidecar 或 `atomic-issue-packets.yaml` 时，视为没有合格 Atomic Issues；即使 `tasks.md` 存在且标 ready/done，也不得执行。
- `atomic-issues/Txxx.md` 必须由 `atomic_issue_compile.py` 从 packet 编译，且 `atomic_issue_compile.py specs/changes/<change-id> --check` 通过；否则不得进入实现。
- 只执行 `tasks.md` 中索引的 Atomic Issue。
- 单个任务执行时，Atomic Issue 是 primary input；`proposal/spec/plan` 只能用于核对 source of truth，不能用于补齐 issue 缺失语义。
- 每个任务改代码前必须运行 `workflowctl.py admit-task Txxx specs/changes/<change-id>`；改完后必须运行 `workflowctl.py validate-task-diff Txxx specs/changes/<change-id>`；通过验证并记录 fresh result 后必须运行 `workflowctl.py pass-task Txxx specs/changes/<change-id>`。
- 如果 diff 超出 admitted file allowlist，必须 backflow/reseal/re-admit；不得用 “mechanical dependency / compile dependency / necessary consequence” 作为豁免。
- 遇到新决策、契约缺口、验证缺口或 Atomic Issue 缺口，暂停并记录 `backflow.yaml` trigger，先分类回流类型。若任务边界基本成立，走 local-reseal backflow：运行 `workflowctl.py backflow specs/changes/<change-id> BF-xxx` 计算局部影响，只修受影响 artifact，并把执行开始后修改过的 planning artifact 列入 `invalidates.artifacts`；若 execution 已 `in_progress`，修复并通过 compile/check/gate 后将 BF 标为 `resolved`/`closed`，再运行 `workflowctl.py reseal-execution-backflow specs/changes/<change-id> BF-xxx --reason "<reason>"`，从最早受影响任务重新 `admit-task`。若任务拆分、owner、contract edge/operation 粒度、Atomic Issue 自包含性或 Task DAG 拓扑错误，走 task-regeneration backflow：回到 `atomic-task-planning` 或更早阶段重新生成受影响 Atomic Issues；影响面跨多个核心 contract/module/DAG 时允许重新生成整批 task-planning artifacts。不得默认新建 clean worktree 重开；clean recovery 只用于 reseal 工具不可用、git 状态无法隔离或用户明确要求。
- 每个任务完成后执行短闭环验证。
- 完成前把实际验证写入 `task-verification-log.yaml` 或 `execution-state.yaml`，把 task-local semantic review 写入 `task-semantic-review.yaml`；mock acceptance / repo-specific acceptance runtime owner task 还必须把 row-level 结果写入 `mock-acceptance-execution.yaml`。再用 `workflowctl.py pass-task Txxx` 签发 task receipt；不得把执行日志写入 sealed `tasks.md` 或 sealed mock matrix/case 文件。

### Step 7: 收敛复盘

以下情况触发 `convergence-retrospective`：

- 初始实现后出现多轮 fix commit。
- review/test 发现的问题超过原子任务预期。
- 用户要求沉淀本次大需求经验。

复盘必须区分：

- `N2-contract`：问题域固有跨模块语义，属于理论下限。
- `N1 avoidable`：需求/AIP/考古/pattern/验证/任务拆分/执行纪律缺口，必须反哺 current 或 skill。

## 输出格式

启动 workflow 时先输出：

```markdown
## Workflow Decision

| 项 | 结论 |
|---|---|
| 是否原子任务 | yes/no + 理由 |
| 路径 | new-feature / major-change / execution-only |
| change-id | YYYY-MM-DD-area-topic |
| required artifacts | proposal/spec/plan/tasks/current |
| blocking questions | none 或列表 |
| next skill | product-requirement-design / aip-readiness-review / requirement-readiness-review / ... |
```

不要在这个入口 skill 中直接展开所有阶段细节。
