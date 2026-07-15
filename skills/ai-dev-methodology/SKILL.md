---
name: ai-dev-methodology
description: AutoMQ 大需求 AI coding 方法论。Use when explaining, reviewing, refining, or applying the theory behind the AutoMQ large-feature workflow, including atomic task boundaries, P^N decay, N1/N2 convergence, module boundary discovery, cross-module semantic contracts, and convergence retrospective.
---

# AI Dev Methodology

## 定位

这是 AutoMQ 大需求 AI coding workflow 的理论层。

使用它来理解“为什么要这样拆 skill 和流程”，不要把它当成执行清单。真正执行时由 `automq-ai-dev-workflow` 路由到各阶段 skill。

## 深度参考

本文件只保留高频理论摘要。按场景完整读取对应 reference：

| Reference | 必须读取的场景 |
|---|---|
| [full-methodology.md](references/full-methodology.md) | 评审、完善、质疑或解释方法论；从收敛事故反推 skill 缺口；映射原始思想与案例 |
| [artifact-completeness-spec.md](references/artifact-completeness-spec.md) | 生成/评审阶段 artifact；判断正交、完备、可验证和表达媒介；更新阶段产物或 gate |
| [experience-shaped-implicit-constraints.md](references/experience-shaped-implicit-constraints.md) | 沉淀收敛经验；识别 lifecycle、frontend、mutation、managed resource、runtime、mock 等问题形状 |
| [generative-decision-surface-discovery.md](references/generative-decision-surface-discovery.md) | 处理未知决策面、经验库不完备，或更新生成型 surface / retrospective 规则 |
| [runtime-resource-routing.md](references/runtime-resource-routing.md) | 执行或修复 workflow；这是模板、sidecar、命令和阶段资源的唯一导航表 |

身份恢复、stage construction、receipt、Atomic Issue compiler 和 execution admission 始终是不可跳过的硬门禁。

## Subagent / Worker Usage Hard Gate

在本方法论中，`subagent`、`worker`、`explorer`、`agent` 和任何 `spawn_agent` 创建的执行体都统一视为 subagent；不能用不同名称绕过权限。Atomic Issue 文档里出现的 `worker` 只是“未来拿到该 issue 的实现执行者”这个抽象角色，不表示当前 workflow 可以启动 subagent/worker 来生成、修复或补齐阶段 artifact。

subagent 只能作为只读 reviewer 使用：读取主 agent 已冻结的 review packet，输出 evidence-based findings。subagent 不得生成、修改、补齐、重写、格式修复、签收任何 canonical artifact，不得运行 gate/validator 或替主 agent 判定 artifact valid / ready / passed；也不得负责 PRD、AIP、readiness、archaeology、design、migration、frontend-contract、contract、verification、atomic-task-planning、mock-acceptance、product-acceptance 或 retrospective 的阶段产物。

gate failure repair、validator error triage、schema/parser 修复、receipt hash 修复、缺失 artifact 补齐、YAML sidecar 生成、verification feasibility 补齐、multi-perspective review 文件创建、context pack 生成、Atomic Issue packet 生成或修复，都必须由主 agent 本地完成。只有 artifact 已成为 frozen review candidate 后，才允许 subagent 做只读审查；subagent 的输出只能是 finding，不能直接成为 DEC/C/VER/T、canonical artifact 或 receipt。

`reviewer_type: readonly-subagent` 只是 artifact 类型字段，不是 review 已执行的证据。阶段级 review、Atomic Issue quality review、task-local semantic review 都必须记录 `subagent_execution`：实际 `spawn_agent` 返回的 agent id、`wait_agent` final status、reviewer final message digest/source、以及 `close_agent` 或明确复用证据。没有真实启动并等待 subagent 的记录时，该 review gate 必须 blocked；不得由主 agent 自己补 reviewer row 后宣称“走过只读 subagent review”。

如果主 agent 已经把 artifact repair 交给 worker/explorer/subagent，必须停止该 delegation，关闭或忽略该 subagent 的改写结果，并从最早失败 gate 重新由主 agent 本地修复。

## 核心问题

AI 对小需求的正确率很高，但大需求不能简单理解为“小需求串起来”。

原因是大需求里存在大量决策点、隐式约束和跨模块语义约束。单点正确率为 `P` 时，整体正确率会随决策数量 `N` 近似按 `P^N` 衰减。即使每个点看起来成功率很高，`N` 足够大时整体偏离也会明显。

目标不是让 AI “一次性无收敛完成所有大需求”，而是把可避免的收敛消掉，把剩余收敛压缩到问题域固有的跨模块语义约束。

方法论的可执行表达是：前置阶段先把大需求转成模块契约图，再把每个模块内的实现工作转成契约闭包完备的 Atomic Issues；当这些 Atomic Issues 都满足原子边界，并被按 `tasks.md` 顺序实现和验证后，大需求应自然完成。PRD、AIP、考古、迁移、契约和验证矩阵不是终点，它们都是生成高质量 Atomic Issues 的素材和门禁。

这还隐含一个更基础的前提：workflow 必须知道“哪些东西算隐式约束，哪些东西必须显式化”。隐式约束不只来自旧代码、PRD 空白和跨模块契约，也来自人类工程经验。人类工程师看到 lifecycle、event、progress、frontend action、mock acceptance / repo-specific acceptance runtime、selector、permission、observability、derived config、persistent mutation / schema compatibility、managed/generated/existing external resource ownership、runtime mode materialization parity 等问题形状时，会自然展开状态、路径、消费者、失败态、fixture、真实状态所有者、写入/readback、资源身份、ownership provenance、运行时 artifact/config/plugin/secret/bootstrap 物化、清理保护和验证；AI 不能稳定依赖这种直觉。因此这些经验型隐式约束必须被方法论化：把常见工程问题形状沉淀为触发器、矩阵、sidecar 和 gate，让“需要建模的东西”先被识别出来，再进入契约和 Atomic Issue。经验目录维护在 `references/experience-shaped-implicit-constraints.md`。

这个前提还要求四个闭环：

- Source intake 闭环：所有输入先登记、读取、映射和冲突决策，不能漏读 source。
- Code scope discovery 闭环：PRD/AIP/design 前必须证明已理解与 propose 相关的当前项目现状，并有停止条件。
- External capability research 闭环：PRD 只说明用户要什么，不能证明外部系统允许怎么做。凡是需求涉及云资源、K8s/Helm/Terraform/IAM/network/storage/compute/runtime、第三方 API/SDK、官方协议、autoscaling/scheduling/lifecycle、metrics/logs/events 或 mock acceptance / repo-specific acceptance runtime 外部依赖，必须在 AIP/design 锁定前调研官方事实、版本/区域差异、默认值、限制、失败语义和不支持项；还必须用 `External Mechanism Decision Matrix` 写清产品语义如何映射到外部机制/API/resource、字段如何映射、哪些语义不等价/不支持、权限/指标缺失/失败如何表现，并把事实和机制映射消费进 ADEC/DEC、C、VER、semantic_carrier 和 owner packet。只把“参考 AWS/K8s 官方文档”写在 AIP 调研段不算闭环。
- Mechanism design 闭环：AIP/readiness 和 design 必须把“怎么实现”锁到机制模型，而不是只写能力方向。凡是需求触发云 API、K8s/HPA、ASG、metrics、IAM、runtime 物化、日志、存储、外部 adapter、资源 lifecycle、progress/change/event 或跨 mode 行为，必须生成 `mechanism-design-model.md`，并把每个 `MECH-*` 降解为 operation sequence、external API parameter map、event state model、runtime materialization model、resource lifecycle model、failure consistency model 和 module interface model 中的具体行；不适用项必须 locked N/A。AIP 正文负责让人读懂方案逻辑，机制模型负责让契约和任务规划不再临场考古。缺少 `MECH/OPSEQ/EXTAPI/EVT/RMM/RLM/FCM/MIM` 行、行中仍有 provider API/runtime carrier/event fields/cleanup/failure/verification 待选择时，不能进入 contract 或 task planning。
- Decision surface discovery 闭环：在锁定 PRD/AIP/契约和生成 Atomic Issue 前，必须先枚举需求触发的决策面，包括 mode consumer、capability、frontend action、post-create consumer、persistent mutation、runtime lifecycle、mock acceptance / repo-specific acceptance runtime、observability、permission 和 compatibility。AI 没有意识到某个决策点，本身就是 workflow 缺陷；因此每个 surface 必须有 owner stage、locked decision/contract/verification、owner issue 或 locked N/A。
- User decision interaction 闭环：未授权 AI 做产品决策时，PDEC 必须由用户确认，模糊回答保持 open。
- Decision consistency 闭环：同一 Decision key 不能有多个冲突的 active locked 决策。
- Engineering propose 闭环：AIP/接口/Terraform/API 草案也只是工程 propose，必须归一化为 locked DEC/ADEC。
- Task DAG 闭环：Atomic Issues 的顺序由 provider/consumer contract、文件 ownership 和 verification gate 决定。
- Backflow invalidation 闭环：任何回流都必须使受影响的 DEC/C/T/VER 失效、重写和重跑验证；能从 invalidated DEC/C/VER 推导的下游 T/VER 必须由 `workflowctl.py backflow` 自动传播后再重写。
- Backflow type 闭环：执行期回流必须先分类。Atomic Issues 是上游 canonical artifacts 的派生产物；上游 PRD/AIP/readiness/design/archaeology/frontend-contract/contract/verification 被重写或重签后，默认是 `task-regeneration backflow`，必须让 task-planning 失效并重新生成任务规划产物；若本 change 存在 migration 阶段 receipt，migration 也作为 optional consumed upstream 参与失效判断。`local-reseal backflow` 只适用于已写明 `Task Planning Impact Proof`，且证明任务边界、provider/consumer owner、semantic carrier、Task DAG、files_to_change 模块边界和 verification loop 都不变的情况。`task-regeneration backflow` 必须写明 `Task Planning Regeneration Evidence`，列出 regenerated artifacts、source upstream receipt hashes、compiler/review/gate evidence。`task-regeneration backflow` 适用于任务拆分错误、canonical owner 错误、contract edge/operation 粒度错误、Atomic Issue 不自包含、需要新增/删除/合并/拆分 Txxx，或 Task DAG 拓扑需要重建的情况。后者必须回到 `atomic-task-planning` 或更早阶段重新生成受影响 Atomic Issues；如果影响面跨多个核心 contract、多个 primary module 或 DAG 拓扑，则允许重新生成整批 task-planning artifacts。两类回流都必须记录 BF、invalidates、supersession、重新 compile/check/review/gate；区别只在重写范围，不在质量门禁。
- Execution-stage local reseal 闭环：执行已经 `in_progress` 后发现契约、验证或 Atomic Issue 缺口时，不得默认新建 clean worktree 重新开局。正确流程是记录 `backflow.yaml` trigger，运行 `workflowctl.py backflow specs/changes/<change-id> BF-xxx` 计算影响，只重写受影响 DEC/C/VER/T 和 planning artifact；执行开始后被修改的 planning artifact 必须逐项列入 `BF-xxx.invalidates.artifacts`。修复后 active DEC/C 必须重新 locked，direct impacted T 必须离开 blocked/pending-rewrite，VER/T 必须回到可执行状态或明确 pending-rerun，`BF-xxx.status` 必须改为 `resolved` 或 `closed`；compile/check 和 gate 通过后运行 `workflowctl.py reseal-execution-backflow specs/changes/<change-id> BF-xxx --reason "<reason>"` 刷新 sealed hashes、失效受影响 task receipts，然后从最早受影响任务重新 `admit-task`。已有业务 diff 只能作为被 reseal invalidated 的当前任务 allowlist 内 diff 进入新 admission baseline；无关业务 diff 仍阻塞。clean worktree 只作为工具损坏、git 状态无法隔离或用户明确要求时的兜底，不是局部回流常规路径。
- Semantic consumption 闭环：每个阶段必须证明已完整消费、派生、复制或显式丢弃上游语义对象，不能靠后续阶段回读 PRD 补信息。
- Verification feasibility 闭环：实现前必须确认验证环境、fixture、账号、云资源和浏览器证据是否可用。
- Version/branch alignment 闭环：多仓、多版本、Terraform/IAC/测试编排/控制面应用/kernel 相关变更必须先确认版本和分支一致。
- Rubric scorecard 闭环：结构校验通过后仍必须落盘 0/1/2 评分；任何 0 阻塞下一阶段。
- Structured sidecar 闭环：Markdown 是人读产物，YAML sidecar 是机器可执行约束；Atomic Issue Markdown 必须由 `atomic-issue-packets.yaml` 编译生成，task planning 之后必须能通过 `workflowctl.py validate pre-execution`。
- Stage receipt 闭环：`workflow-state.yaml.stage_status` 不是可信来源；`passed` 依赖可重算 hash 的 `stage_receipts`，整个阶段 `not_applicable` 依赖 profile 允许且可重算 hash 的 `stage_na_receipts`。缺失、伪造、命令不匹配或 artifact hash 过期都必须 fail 并回流。
- Workdir identity 闭环：`workflow-workdir.md` 是 workflow 身份锚点，必须早于 `purpose.md` / `source-intake-ledger.md` 创建，并被所有阶段 receipt 封存。恢复后如果 cwd、branch、change dir 或 change-id 与该文件不一致，当前执行必须 blocked；不能因为当前 worktree 没有 `specs/` 就创建新的 change。
- Stage boundary receipt 闭环：每个阶段进入下一阶段前都必须运行 `workflowctl.py validate <stage>` 和 `workflowctl.py pass-stage <stage>`，并确认 `stage_receipts.<stage>` 有效。`validate <stage>`、本地审计、文件已创建、无 open/blocker、compiler 局部通过都不能替代 `pass-stage`。修改任何已签收 artifact 会使覆盖它的阶段 receipt 失效，必须从最早失效阶段重签后才能继续下游。
- Receipt hash hygiene 闭环：receipt hash 只封存 workflow artifact 和任务输出语义，不把 `.DS_Store`、gitignored build/cache 文件、`target/`、`node_modules/` 等系统噪音当成 sealed artifact 或业务 diff；这些文件也不能作为任何阶段产物或验证证据。
- Execution lease 闭环：`pre-execution` 通过后仍不能直接改业务代码；必须先运行 `workflowctl.py begin-execution specs/changes/<change-id>` 写入 `execution_receipt`。没有该 receipt，任何非 specs 业务 diff 都是非法执行。
- Task admission 闭环：每个 Txxx 必须先运行 `workflowctl.py admit-task Txxx specs/changes/<change-id>`，再改代码；完成前运行 `workflowctl.py validate-task-diff Txxx ...` 和 `workflowctl.py pass-task Txxx ...`。task passed 只能由 `workflow-state.yaml.task_receipts` 派生，不能手写进 `tasks.md`。
- Task allowlist feasibility 闭环：Atomic Issue 的 `files_to_change` 必须足以承载其语义。API/VO、持久化、domain、runtime/event/progress、frontend action route 等语义如果缺对应文件落点，必须在任务规划阶段 fail 并回流；执行阶段不得用绕路存储、相邻页面、hidden helper 或未列文件补齐。
- Task diff baseline 闭环：`admit-task` 会记录 admission 时已有 changed path hash，避免前序已通过但未提交 diff 污染当前任务；当前任务若改动 baseline 中非 allowlist 文件，hash 变化仍会被 `validate-task-diff` 拦住。
- Pre-execution Atomic Issue quality review 闭环：`atomic_issue_compile.py --check` 和结构 validator 通过后，仍必须由只读 reviewer subagent 同步阻塞审查编译出的 Atomic Issues 是否为了过 validator 堆词、把 Source Context 写成当前任务要求、用 DS/REQ/C gate phrase 代替具体行为、把 provider proof 放到 frontend task 或把 DOM proof 放到 backend task、因 brief 超限压缩关键词、或让单个 issue 失去原子边界。审查结果写入 `atomic-issue-quality-review.yaml`；任一 blocker 必须回流 task planning，不能进入 pre-execution。
- Task-planning repair ledger 闭环：task-planning 阶段每个 compiler、workflowctl 或只读 reviewer blocker 都必须写入 `templates/task-planning-repair-ledger.yaml` 对应的 `task-planning-repair-ledger.yaml`。每个修复项必须有稳定 `failure_signature`、`owner_invariant`、`forbidden_regression` 和可重复 `regression_checks`。每次重新生成 `task-dag.yaml`、`atomic-issue-packets.yaml`、`tasks.md` 或 `atomic-issues/Txxx.md` 后，必须先跑 ledger 中所有 active/fixed regression check；若 fixed signature 再次出现，当前阶段必须 blocked，归类为 generator invariant failure，回到 owner model、carrier projection 或 task split 修复。不得继续靠替换 `task/runtime/resource/readback/provider` 等同义词让 compiler 静默。若同一类 failure 在同一 change 中出现第二次，或来自 readonly reviewer 的 blocker 暴露出生成器/owner 投影规则缺口，必须把它提升到 `known_regressions`：写明稳定签名、owner invariant、禁止回归位置和可重复检查命令；不得只在当前 iteration 里标 fixed。
- Task-local semantic review 闭环：Atomic Issue 已经写清楚，不等于实现一定遵守。每个非纯文档、非 trivial task 在 `pass-task` 前必须对照当前 Txxx、当前 diff 和验证日志做语义审查，确认 provided obligations、negative assertions、验证 proof、测试断言和 diff scope 与 issue 一致。审查结果写入 `task-semantic-review.yaml`，带当前 changed path hash；无 review、review 有 blocking finding、或 review hash 过期时 `pass-task` 必须失败。该闭环允许只读 reviewer subagent 作为独立视角，但禁止其改代码、改 canonical artifact 或签收任务。
- Multi-perspective review 闭环：关键阶段可以引入多个只读 reviewer subagent，但它们不是并行设计或执行 lane。主 agent 先产出 frozen canonical artifacts、context pack、decision-surface-discovery / Generative Surface Stress Tests / Surface Obligation Projection Matrix（如适用），再按阶段给不同 reviewer 一个窄视角 packet。reviewer 只能输出 evidence-based finding；主 agent 必须同步等待 required reviewers，裁决 accepted / rejected / deferred / backflow，写入 `multi-perspective-reviews/<stage>.yaml`，再更新 canonical artifacts 和重跑 gate。没有主 agent disposition 的 reviewer finding 不得进入 DEC/C/VER/T，也不能让阶段通过。
- Subagent lifecycle / repair discipline 闭环：validator/gate failure repair 期间不得启动 subagent 分担修复；主 agent 必须本地读取 validator 输出和 canonical artifacts 后修复。subagent 只在 artifact 已成为 frozen review candidate 后做只读审查。每轮 reviewer 完成并被主 agent 裁决后必须关闭；若 subagent 池满，先关闭已完成/不再需要的 agents，再重试一次，仍失败则记录 `subagent pool exhausted after cleanup` 并让当前 review gate 保持 `blocked`。不允许 main-local fallback、主线程自审或 deterministic check 替代只读 reviewer。
- Execution log 隔离闭环：`tasks.md` 是 sealed planning artifact，只保存索引、DAG 和初始状态。执行日志、Not Run、Decision Gap 和 verification result 写入 `task-verification-log.yaml` / `execution-state.yaml`；修改 `tasks.md` 会使 task-planning receipt stale。
- Mock execution ledger 闭环：mock/backend、mock/frontend、event-state、packaged/runtime representative case 的 matrix/case YAML 是 sealed planning artifact，只表达要测什么、由谁测、怎么测。执行期不得把这些行改成 passed；row-level command/result/assertion/evidence 写入 mutable `mock-acceptance-execution.yaml`。这样既保留矩阵的 hash 封存，又能让 `pass-task` 和 mock-acceptance gate 检查每个计划行是否真的被执行。
- 经验型隐式约束闭环：每次收敛事故如果暴露出某类人类工程直觉没有被 AI 稳定识别，必须判断它是否是通用问题形状；若是，就要把它抽象成触发条件、结构化 artifact、Atomic Issue carrier 和验证 gate，而不是写成一次性提示词。
- Persistent mutation / schema compatibility 闭环：凡是新 mode、新资源类型、新生命周期或 create/update/delete/resize/save/scale 等 mutation 让旧字段从“必然存在”变成“某些模式下不存在/派生/禁止写入”，必须把旧 schema/DO/mapper/VO/API 必填约束、真实 state owner、writer、readback consumer 和 mode-specific null/default/compat 策略显式化。不能把“persisted / saved / canonical state”这种泛化词当成实现义务；必须进入迁移决策、DB/Migration contract、semantic carrier、owner Atomic Issue 和 mock/backend matrix 的 write+readback proof。
- Dense semantic carrier 闭环：字段矩阵、selector/default/auto-create、managed resource ownership、禁止 raw text、action route、错误/状态/时序、mock fixture 等密集语义必须从 `REQ/DEC/C` 进入 `semantic_carriers`，再进入具体 Txxx packet 的执行章节；不能被压缩成 “use selectors / mode-specific / follow existing pattern”。
- Semantic carrier projection 闭环：全局 `REQ/SCN` 是场景级语义，常常混有多个 owner 的责任。task-planning 必须先把 dense `REQ/SCN` 投影成 `SCP-xxx` owner slice，再把 slice 复制到对应 Txxx packet；validator 只能要求当前 task 携带自己 owner 的 slice，不能要求每个引用 `REQ/SCN` 的 task 背完整全局语义。缺少 projection 时应回流补分账，而不是扩大 packet、合并 task 或让 API/frontend/acceptance task 承担 runtime/resource/provider owner 语义。
- Decision surface owner assignment 闭环：`decision-surface-discovery.md` 的每一行都必须进入 downstream DEC/C/VER/T，且被复制进 owner packet 的执行层。只写在 Source Context、context pack、plan appendix 或全局矩阵中不算消费成功；没有 owner issue 或 locked N/A 时不得进入 pre-execution。
- Surface-to-obligation projection 闭环：抽象 surface 不能直接关闭为粗粒度 Txxx。凡是 surface 涉及 mode consumer、post-create consumer、runtime tabs、managed resource、baseline/default、user-visible event、browser selector、mock acceptance 或 handoff command，必须先展开成 `Expanded obligation ID` 行；每行必须有 concrete production anchor、consumer owner、mock/acceptance owner 或 locked N/A、contract/verification、negative assertion 和 owner Txxx。frontend consumer 不能关闭 backend/provider 能力，mock 不能关闭 production side effect，DB readback 不能关闭 provider write，browser smoke 不能关闭 backend contract。没有 concrete anchor 或 negative assertion 的行属于填表噪音，阻塞 pre-execution。
- Routed decision closure 闭环：`routed-to-PRD/AIP/readiness/design/archaeology/migration/frontend-contract/contract/verification/task-planning` 只允许作为中间状态。对应 owner stage 正在签收或已经 `passed` 时，该 surface / DEC / ADEC 必须关闭为 locked decision、locked N/A、blocked backflow、C/VER 或 Txxx owner；不得在 owner stage passed 后继续保留 `routed-to-*`、`stage-owned` 或“后续发现/后续决定”。这类遗留不是当前阶段合理风险，而是 owner stage 未完成。
- Dense semantic inference 闭环：`workflowctl.py` 和 `atomic_issue_compile.py` 会从 source/contract/task/packet 文本推导 dense semantics。只把语义写在 source excerpt、scope 或 contract excerpt，而没有分配成 carrier，会直接 fail；尤其是 AIP 缺失、ASG selector/raw text、explicit failure vs unknown、frontend action-flow。
- Stateful behavior 闭环：凡是需求、旧代码或契约出现 lifecycle、progress、event、status、terminal、polling、retry、task step、change tracking、mock state graph、用户可见状态推进之一，都必须把自然语言展开成 `stateful-behavior-matrix`。矩阵至少列出 operation、mode/variant、from/to state、trigger、guard、event/step、status、terminal、failure reason、producer、consumer、frontend assertion、mock fixture 和 verification。不能把“实现 event graph / progress state / mock state graph”留给 Atomic Issue worker 自行判断完整性。
- Frontend action-flow 闭环：凡是需求或旧代码出现用户可见按钮、操作下拉、行操作、tab action、wizard submit、update-config、resize、progress、events、metrics/logs/workers 入口之一，都必须把“用户从哪里点、点到哪里、落在哪个组件、调用哪个 API、显示什么反馈、哪些旧 mode 字段不得出现”展开成 `frontend-route-component-matrix`、`frontend-mode-field-display-matrix`、`frontend-form-state-matrix` 和 `frontend-browser-verification-matrix`。每个 `UI-ACT-*` 必须有 owner issue，并被复制进 packet；owner issue 的文件范围必须包含 source component、handler/router、landing component。build/lint 不能关闭 action-flow，未运行的浏览器证明必须回流或绑定具体 mock frontend case。
- Atomicity readability 闭环：语义完整性不能靠把所有 carrier 堆进更少的 Atomic Issue 实现。经验型隐式约束、frontend matrix、mock matrix 和 stateful matrix 的作用是触发更准确的任务拆分，而不是扩大单个任务。Atomic Issue 必须同时满足语义完整、足够原子、执行层可读三件事；机器审计材料保存在 sidecar/appendix，worker 执行说明必须短、自然、可验证。若出现重复 carrier、奇怪同义词替换、为了 validator 堆词、brief 超限后只保留关键词、或一个 issue 覆盖多个用户动作/状态机 operation，必须回流 task planning 重新拆分、移交 owner 或分层承载，不能压缩掉真实语义。
- Compiler signal hygiene 闭环：compiler 的关键词只能作为风险信号，不能替代 typed owner 判定。优先使用 `decision_surfaces.surface_type`、`semantic_carriers.semantic_type/owner_module`、contract obligation owner、Task DAG owner 和 `files_to_change` 共同判定；`task`、`payload`、`runtime`、`readback`、`resource/provenance` 等泛词单独出现不得把当前 Txxx 升级成 runtime、persistent mutation 或 managed-resource owner。负向边界说明（例如“不由本任务创建/清理资源，proof 在 Txxx”）不得被当成正向义务。若 validator 只能靠替换同义词通过，说明 gate 规则或 owner projection 有缺口，必须修规则或回流，而不是诱导 AI 写无意义字。

## 小需求原子边界

一个任务能被 AI 高概率零返工完成，通常同时满足五个条件：

| 条件 | 含义 |
|---|---|
| 零决策 | 产品、架构、字段、错误、UI、兼容性等选择已前置 |
| 单层变更 | 只触达一个细层，例如后端 service、API、前端 types、Terraform schema |
| 上下文自包含 | 执行所需代码、规则、pattern 能放进当前上下文 |
| 验证闭环短 | 完成后能立刻编译、测试、lint、render、plan 或手动验证 |
| 错误不传播 | 当前任务失败不会污染后续任务输入 |

大需求 workflow 的本质，是先圈定模块、锁定模块之间的契约，再把不满足这五条的需求改造成一组满足五条的模块内契约闭包 issue。任何阶段的产物如果不能被下游 Atomic Issue 消费，就不是合格产物。

## 模块契约图优先

“原子”不是把需求切得越小越好，而是把实现单元限制在一个模块内部，并让它的契约输入输出闭包完整。

每个模块必须明确：

| 项 | 含义 |
|---|---|
| Owned state/data/resources | 模块拥有并负责维护的数据、状态、资源 |
| Provided contracts | 模块承诺给其他模块的 API、事件、状态、数据、错误、时序、观测语义 |
| Consumed contracts | 模块依赖其他模块提供的契约；实现时可以假设这些契约已被对应模块保证 |
| Internal invariants | 模块内部必须保持的状态机和一致性 |
| Verification responsibility | 哪些 proof 证明模块对外契约成立 |

当模块拥有状态机、生命周期、事件或进度语义时，“状态机自洽”不能只写一句结论。必须输出 `stateful-behavior-matrix`，把每个用户可达 operation 和 terminal/failure transition 变成行。人类工程师会自然识别“这里有事件机制需要研究事件名、状态和消费者”，但 AI 不能稳定依赖这种直觉；skill 必须把这类工程经验制度化，让缺失矩阵成为 gate failure，而不是实现阶段的自由发挥。

不允许未知决策出现，本质是：

- 不允许未知模块边界进入实现。
- 不允许未知模块责任进入实现。
- 不允许未知 consumed/provided contract 进入实现。
- 不允许实现 issue 临场重新定义跨模块契约。

合格实现 issue 的形态是：

```text
Module M 内部 issue：
  Given consumed contracts C-in 已成立，
  implement / preserve provided contracts C-out，
  without changing module boundary or cross-module semantics.
```

如果一个 issue 需要同时改变两个模块的契约定义，它不是实现 issue，而是 contract gap 或 design gap。

## 从模块契约图到 Atomic Issue

模块拆分和契约锁定之后，还需要一个确定性降解步骤，不能让 AI 凭经验把模块和契约压成 Txxx。

正确顺序是：

```text
Module Contract Graph
  -> edge + semantic type + operation/surface
  -> canonical provider owner
  -> provider obligation
  -> consumer implementation/proof decision
  -> merge/split decision
  -> Task DAG
```

关键原则：

- 一条模块边不是最小任务单位；最小候选是 `edge + semantic type + operation/surface`。
- Provider/consumer 不等于调用方向。canonical owner 由 authoritative state/schema/validation/resource writer/event producer/UI action owner 决定。
- 每个 decomposed row 至少要有 provider obligation；consumer 只有在需要改代码时才生成 implementation task，否则只需要 regression/acceptance proof。
- 任务合并必须同时满足：同一 primary module、同一 primary semantic type、同一 operation/surface、同一短验证闭环。任一不满足就拆。
- Contract 阶段输出的 `Contract Executable Obligation Matrix` 行是一等输入。每个 `Sub-obligation ID`（如 `C-001-OBL-002`）和专用矩阵行 ID（如 `ESE-*`、`PCP-*`、`RMM-*`）必须映射到独立 Txxx、明确 owner packet carrier/proof/files、proof-only/locked N/A，或 backflow。只消费粗 `C-xxx` 不算把 obligation 消费到 Atomic Issue。
- `decision-surface-discovery.md#Surface Obligation Projection Matrix` 行也是一等输入。每个 `DS-xxx-OBL-*` 必须映射到 DEC/C/VER/T、proof-only/locked N/A，或 blocked backflow。只消费粗 `DS-xxx` 不算把决策面消费到 Atomic Issue。
- `mechanism-design-model.md` 行也是一等输入。每个影响实现的 `MECH-*`、`OPSEQ-*`、`EXTAPI-*`、`EVT-*`、`RMM-*`、`RLM-*`、`FCM-*`、`MIM-*` 必须被 contract obligation、verification 和 Txxx packet 消费，或有 locked N/A / blocked backflow。task-planning 不得把多个机制行按 owner 直接合成一个大任务；只能在满足同一 primary module、同一 semantic type、同一 operation/surface、同一短验证闭环时合并。
- 最小可执行义务优先于 owner 合并。owner 合并只能作为后置优化，且必须证明 same primary module、same semantic type、same operation/surface、same short verification loop。external side effect、runtime materialization/parity、managed resource ownership cleanup/protect、HPA/autoscaling/scaling policy、progress/change/event producer、failure consistency/residual cleanup 这些高风险义务默认拆分，除非逐 row 给出强合并证明。
- Consumer task 只能消费已锁定契约，不能重新定义 provider 语义；发现缺口必须回流 contract/design。

常见必须分开的语义：

| 不应混在一个任务里的语义 | 原因 |
|---|---|
| Wire/API shape 与 UI action closure | API canonical shape 通常由 schema/API provider 拥有，UI 只是 consumer。 |
| Resource ownership 与 selector UI | 选择资源不等于拥有资源生命周期、identity、cleanup/protect。 |
| External side effect 与 DB-only persistence | 写入状态不能替代真实 provider/K8s/runtime 副作用。 |
| State machine/event 与 frontend progress display | UI 应消费事件契约，不定义终态和失败语义。 |
| Fast backend/frontend mock matrix 与 packaged playground acceptance | 前者穷举组合，后者代表性集成和 freshness。 |

这一步的目标不是增加任务数量，而是防止 N2 决策被塞进实现阶段。已有 task 可以合并多个 decomposed rows，但必须显式证明满足同模块、同语义类型、同 operation、同短验证四个条件。

## 模块划分与组合必须验证

模块划分不是设计者的主观切法，必须被验证。否则会出现“每个 issue 局部正确，但模块划分错误或组合后需求不成立”的 N1 收敛。

### Module Boundary Validation

模块边界验证回答：这个模块为什么这样切是合理的？

必须证明：

- 数据/状态/资源所有权清楚。
- 模块内部状态机自洽。
- 外部依赖能枚举成 consumed contracts。
- 对外承诺能枚举成 provided contracts。
- 模块粒度不太大：没有混入多个独立状态机或过多上下文。
- 模块粒度不太小：不会因契约过密导致实现时总要跨模块共改。
- split / merge / keep 是决策，有 alternatives、reason 和 verification。

它必须产出可被后续消费的 `Module Boundary Validation`，而不是自然语言评价。任何 `needs-review`、`unknown`、未证明的 split/merge/keep 都阻塞跨模块契约和任务规划。

### Module Composition Verification

模块组合验证回答：模块各自正确以后，组合起来是否满足用户需求？

必须证明：

- 每个 REQ/SCN 被一个或多个 provided contracts 覆盖。
- 每个 consumer 的 consumed contract 都能找到 provider。
- provider 的 normal/failure/timing/consistency 满足 consumer 假设。
- 每条关键跨模块路径有组合级 proof，例如 integration、E2E、route smoke、browser、runtime smoke 或明确 manual step。
- 模块内部单测不能替代组合验证；只能证明模块局部行为。

没有组合验证的需求只能标 Not Run risk，不能宣布完成。

它必须产出三类可追溯 artifact：

- `Provider/Consumer Assumption Matrix`：证明 provider guarantee 满足 consumer assumption。
- `Module Composition Verification Matrix`：证明组合路径实际成立。
- `Requirement Composition Coverage`：证明每个关键 REQ/SCN 都能追到 provided contracts、verification 和 Atomic Issue。

如果这些 artifact 不能生成，说明契约或模块边界未闭合，不能进入 Atomic Execution。

## SDD 只是容器

AutoMQ 大需求 workflow 可以复用 SDD 的文件入口，但质量标准不由 SDD 模板决定。

`proposal.md` / `spec.md` / `plan.md` / `tasks.md` 只是 review、落库和导航入口。它们不限制内容粒度，也不禁止增加更多文件。如果 AI coding 方法论需要更多 artifact，就必须新增，而不是为了适配轻量模板而丢失上下文。

原则：

- SDD defines artifact slots; AutoMQ AI workflow defines artifact quality.
- `tasks.md` 不是原子任务本体，只是执行索引和状态表。
- 真正的原子执行单元必须是 self-contained atomic issue。
- 如果一个 worker 必须阅读完整 `proposal/spec/plan` 才知道怎么做，该任务不合格。

## 跨阶段语义消费

PRD 可以作为产品语义源头，但不能成为后续阶段的隐式上下文依赖。每个阶段都必须维护 `Semantic Consumption Matrix`：

```markdown
| Upstream object | Consuming stage | Required by stage? | How consumed | Derived object | Copied semantics | Dropped semantics | Drop reason / decision | Verification / gate | Status |
|---|---|---:|---|---|---|---|---|---|---|
```

规则：

- PRD 产生的 `REQ/SCN/PDEC` 必须被设计、考古、契约、验证和任务规划逐阶段消费，或明确 N/A。
- 工程阶段产生的 `DEC/C/MIG/VER` 必须继续进入后续消费矩阵，直到 Atomic Issue。
- `Dropped semantics` 只有在有 locked decision 或明确 N/A 理由时允许存在。
- `Status=blocked` 阻塞进入下一阶段。
- 下游 artifact 可以保留上游 ID 做审计，但必须复制执行所需语义。
- Atomic Issue 如果只引用 PRD ID，不复制必要语义，说明 semantic consumption 失败。

证明链路是归纳式的：Stage N 的 consumption matrix 证明 Stage N-1 的每个语义对象被消费或阻塞；最终 Atomic Issue 的 source/decision/contract/verification 摘录证明 worker 不需要回读 PRD。

## 文档语言原则

持久文档默认使用中文以保证 PRD、决策和 Atomic Issue 的语义一致；代码/API/命令/错误码/枚举/日志原文或用户明确要求时可用英文。完整规则见 [artifact-completeness-spec.md](references/artifact-completeness-spec.md#language-policy-means)。

## Atomic Issue 标准

原子任务的交付物不是 checklist item，而是一份可独立派发给 AI worker 的 Atomic Issue。

一个 Atomic Issue 必须满足：

| 条件 | 合格标准 |
|---|---|
| 自包含背景 | 说明为什么做、解决哪一块需求、与整体需求的关系 |
| 明确范围 | 写清只改哪些 repo/file/module，明确不改什么 |
| 决策闭包 | 摘录相关 DEC/PDEC 结论，不能只引用 ID |
| 契约闭包 | 摘录相关 contract 的 Trigger/Normal/Failure/Consistency/Timing/Verification |
| 代码参考 | 指定要照的现有类、页面、测试、框架 pattern |
| 行为细节 | 输入、输出、错误、权限、状态、边界条件具体化 |
| 实现步骤 | 文件级步骤可执行，不要求实现者重新拆解方案 |
| 验证闭环 | 写清命令、预期结果、失败含义和 Not Run 风险 |
| 禁止事项 | 写清不能做的临时决策、顺手重构、scope 扩张 |

判定规则：

> 一个 worker 只拿到 `atomic-issues/Txxx.md` 和其中列出的文件路径，就能完成任务、验证结果、且不做新决策；否则该任务不是原子任务。

Atomic Issue 可以引用 `proposal/spec/plan` 作为 source of truth，但不能把必要语义只留在那些全局文档里。

Atomic Issue 必须能直接创建为 GitHub issue 或派发给 worker。更准确地说，它是“模块内契约闭包 issue”。合格 issue 的判定不是“包含模板章节”，而是：

- issue 绑定一个 primary module。
- issue 声明 consumed contracts：它依赖哪些外部契约，并假设它们成立。
- issue 声明 provided contracts：它负责实现或维护哪些对外契约。
- worker 只读该 issue 和其中列出的文件路径，不需要完整读全局文档。
- worker 不需要重新做产品、架构、字段、错误、UI、兼容性、验证方式选择。
- worker 能按文件级步骤实现，并用 issue 内验证命令/步骤判断成功或失败。
- issue 失败不会污染后续 issue 的输入。

不合格的常见表现：

- Source Context 只有 `REQ-001`、`C-002` 或一句概括。
- Locked Decisions 写“见 Decision Registry”。
- Files To Change 写 “new helper under ...” 但没有可定位路径或发现规则。
- Implementation Steps 写“根据现有 pattern 实现”，却没有指定 pattern 文件/方法/约束。
- Verification 只有命令，没有 expected result、proves 和失败含义。
- 一个 issue 同时包含多个页面、多个服务层、多个状态机或多个验证闭环。

## 零耦合不是解法

直觉上，可以尝试通过高度内聚、低耦合模块消除 `P^N`。但这不可能解决所有问题。

原因是软件价值来自多个实体的协作。只要业务规则需要同时观察或影响多个实体，跨模块语义耦合就是问题域固有属性，不是工程实现缺陷。

例子：如果“Connector 是否能创建取决于 Worker 集群是否就绪”，这条规则天然涉及 Connector 和 Worker 两个实体。无论用同步调用、事件、消息队列还是接口抽象，都只是改变耦合表达形式，不能消除语义耦合本身。

所以优化方向不是追求零耦合，而是：

1. 让模块内部足够自洽，降低内部错误传播。
2. 显式枚举跨模块语义约束。
3. 将所有必须选择的点前置成决策和契约。

## N1 / N2 模型

把大需求中的 `N` 拆成两类：

| 类型 | 含义 | 优化方式 |
|---|---|---|
| `N1` | 模块内部子任务、工程纪律、pattern、局部实现细节 | 通过模块边界、上下文包、pattern、短验证消除收敛 |
| `N2` | 跨模块语义约束，由问题域决定 | 不能消除，只能显式枚举、锁定、验证 |

理论最优不是零收敛，而是收敛范围只剩 `N2`。

如果实现后出现大量编译修复、字段遗漏、UI 文案、旧约束漏改、验证补救，这些通常不是理论下限，而是 `N1 avoidable`。

## 模块边界如何圈定

模块边界不是按文件夹、类名或技术层随意划分，而是按“错误是否能被限制在内部、上下文是否能自包含、跨模块交互是否可枚举”来划分。

### 模块必须满足的性质

| 性质 | 判断 |
|---|---|
| 内部错误不传播 | 模块内部实现错误不应改变其他模块的输入语义 |
| 上下文可自包含 | 理解和修改模块不需要装入过多外部上下文 |
| 跨模块交互可枚举 | 与其他模块的依赖边和语义契约能列出来 |

### 三个判定信号

| 信号 | 如何使用 |
|---|---|
| 数据所有权 | 先问写权限归谁：DB 表、缓存、配置、内部 topic、云资源、前端状态的 writer 决定 owning module；只有 reader 的模块必须通过接口消费 |
| 状态机自洽性 | 逐个状态转换检查 guard / precondition 是否只依赖自身数据；外部前置条件就是跨模块契约候选 |
| 变更独立性 | 旧代码用最近约 50 个相关 commit 统计文件共改；新功能用“未来会独立修改哪些行为”替代 git history |

模块不等于 Java 类。模块可以是 backend service、DB migration、OpenAPI/VO、async task、Terraform resource、Helm/K8s deployment、AWS resource、frontend page、observability。

### 粒度判断

| 风险 | 信号 | 处理 |
|---|---|---|
| 太大 | 超过约 10 个核心类/资源、多个独立状态机、对外接口超过约 15 个方法、上下文装不下 | 拆分 |
| 太小 | 1-2 个类、两个模块交互点超过 5 个、总是与另一模块共改、接口只被一个调用方使用 | 合并或稳定接口 |
| 合适 | 3-8 个核心类/资源、对外接口 3-10 个、与其他模块交互点 1-3 个、状态机自洽或只有 1-2 个外部前置条件 | 保留 |

### 操作流程

模块边界判定必须按顺序产出结构化证据：

1. 列出所有数据存储和资源，标明 writer、reader、mutation rule，按 writer 分组形成模块候选。
2. 画出每个实体/资源的状态机，逐个状态转换标明 guard/precondition；外部依赖标为 contract candidate。
3. 旧代码从最近约 50 个相关 commit 统计文件共现；新功能用未来独立变更假设替代。
4. 用粒度阈值检查太大/太小，输出 keep/split/merge 决策。
5. 输出模块清单：模块名、包含类/资源、owned data/resource、writer、对外接口、交互点数量、边界证据。

如果无法完成这些证据，不能把模块边界视为 locked。

## 决策前置

大需求失败的常见原因不是 AI 不会写代码，而是实现阶段还在做本该由需求/AIP/设计阶段完成的选择。

必须前置的决策包括：

| 决策类型 | 示例 |
|---|---|
| product | 用户可见行为、状态、错误、配置、权限 |
| architecture | controller-driven 还是 native autoscaler，是否引入新组件 |
| interface | API 字段、Terraform schema、错误码、兼容字段 |
| migration | 旧字段删除/保留/重命名/兼容 |
| contract | 跨模块时序、一致性、失败处理 |
| pattern | UI 照哪个页面做、框架方法语义照哪个模块 |
| validation | 用什么测试、plan、render、runtime smoke 证明完成 |

任何 `open` 决策进入实现，都会把 AI 拉回“自作主张”模式。

阶段决策文档必须逐决策展开。把 `PDEC-001..022`、`ADEC-001..004` 合并成一个详情段，会让下游 Atomic Issue 无法消费每个决策的替代方案、反选理由、影响面和验证方式，属于不合格。

每个决策还必须有稳定的 `Decision key`。如果两个 active locked 决策使用同一个 key 却给出不同结论，说明 workflow 内部已经自相矛盾，必须先 supersede、拆 key 或回流澄清，不能进入实现。

## 跨模块契约

跨模块契约是 `N2` 的显式化形式。每条契约至少回答：

| 问题 | 目的 |
|---|---|
| Trigger | 什么时候发生交互 |
| Normal path | 正常路径两边状态如何变化 |
| Failure path | 对方失败、不可用、超时时怎么办 |
| Consistency | 要保持什么一致性，机制是什么 |
| Timing | 顺序、并发、幂等、重试要求 |
| Verification | 怎么证明契约被满足 |

契约必须覆盖后端、前端、API、DB、异步任务、Terraform、Helm/K8s、云资源、观测等所有被需求触达的边界。

## 前端特殊性

前端收敛经常来自自然语言描述不精确，而不是业务逻辑难。

必须前置：

- 参考页面、组件、截图或明确字段表。
- 字段 source of truth。
- loading/empty/error/unknown/null 展示。
- 权限、路由、按钮可见/可用条件。
- i18n key 和文件。
- 浏览器或截图验证方式。

没有 reference 或字段契约时，不应让实现阶段自由设计。

## 验证前置

验证不是实现后的补救，而是设计的一部分。

每个 REQ、SCN、contract、migration decision 都必须能映射到证明方式：

- unit
- integration
- e2e
- frontend lint/typecheck/build/browser
- Terraform fmt/validate/plan/provider test
- Helm template/lint/schema
- cloud runtime smoke
- observability metric/event/log/alert validation
- manual step with risk

无法验证的行为，要么补验证，要么显式写入风险。

Not Run 不是“跳过”。任何 P0/P1 场景、核心 REQ/SCN、关键跨模块契约或 `Blocks done=yes` 的 Not Run 都阻塞完成声明；只能交付为带 owner/approval 的风险状态。

## 任务 DAG 与错误不传播

Atomic Issues 的顺序必须由 DAG 证明：

- provider contract 的 issue 必须在 consumer issue 前完成并验证。
- schema/migration/infra 先于依赖它的服务/API/UI。
- verification gate 必须在依赖它的场景宣布完成前执行。
- 并行只允许在文件集合不重叠、契约不依赖、失败不污染对方输入时使用。

如果无法画出 DAG，说明任务边界或契约闭包仍不完整。

## 回流失效重算

实现、验证、验收或 review 发现 gap 时，不能只修当前代码。必须判断最早缺失阶段，并重算受影响 artifact：

- PRD/AIP 改变会失效相关 design、contract、verification、Atomic Issues。
- 模块边界改变会失效 Module Contract Graph、Contract Closure Coverage、Task DAG。
- 契约改变会失效 provider/consumer issue 和组合验证。
- 验证策略改变会失效 Atomic Issue 的 Verification 和 tasks.md 结果。
- 产品验收 P0/P1 问题未关闭时，不能宣布 done。

## 收敛复盘

实现后的 fix/review/test 问题必须分类：

| 类别 | 含义 |
|---|---|
| `N2-contract` | 问题域固有跨模块语义，属于理论下限 |
| `requirement-gap` | 产品需求缺决策 |
| `aip-decision-gap` | AIP 缺工程取舍 |
| `archaeology-miss` | 旧代码隐式约束漏挖 |
| `contract-miss` | 跨模块契约漏列 |
| `migration-diff-miss` | 旧/新语义差异没处理 |
| `pattern-miss` | UI/框架/代码 pattern 没指定 |
| `atomic-task-too-large` | 原子任务仍包含多个层或多个决策 |
| `verification-miss` | 本可通过验证前置发现 |
| `execution-discipline` | 没按任务逐步验证或扩大 scope |
| `semantic-review-miss` | Atomic Issue 已写清楚，但实现/测试偏离 issue，且 pass 前语义审查本应发现 |
| `atomic-issue-not-self-contained` | 任务只是 checklist item，缺少独立执行上下文 |
| `sdd-template-overfit` | 产物为适配 SDD 轻量模板而牺牲 AI coding 所需粒度 |

复盘目标是改进 workflow，不是解释失败。每个 `N1 avoidable` 都应反哺 skill、current spec、pattern 或验证矩阵。

## 与 Skill Suite 的关系

阶段 owner skill、模板、sidecar 和命令的唯一导航见 [runtime-resource-routing.md](references/runtime-resource-routing.md)。理论规则不得在各阶段 skill 中复制成第二份事实源。

## 使用原则

讨论或优化 workflow 时读取本 skill；真正执行需求必须由 `automq-ai-dev-workflow` 路由到阶段 skill。不要把方法论 skill 写成项目需求或 AIP。
