---
name: atomic-task-planning
description: 把需求、AIP、spec、plan、考古、差异分析和跨模块契约转成 AutoMQ specs/changes/tasks.md 索引和 self-contained atomic-issues/Txxx.md。Use before implementation to create or review executable Atomic Issues with exact repo/file paths, copied source/decision/contract context, dependency ordering, expected verification results, and no unresolved decisions.
---

# Atomic Task Planning

## 目的

把已锁定的设计转换成 `tasks.md` 索引和 `atomic-issues/Txxx.md`，使实现阶段只执行 Atomic Issues，不再做产品或架构决策。

本阶段是整个大需求 workflow 的收敛点。前面所有 PRD、AIP、考古、迁移、前端契约、跨模块契约和验证矩阵，最终都必须被压缩成可独立派发的 Atomic Issues。更准确地说，是压缩成“模块内契约闭包 issue”：在某个 primary module 内，消费已锁定的 consumed contracts，并实现/维护该模块对外 provided contracts。若 Atomic Issue 不能独立实现，说明上游阶段没有完成，不能把缺口留给实现阶段。

它位于：

```text
proposal/spec/plan/contracts -> tasks.md + atomic-issues/Txxx.md -> atomic-execution-sdd
```

`tasks.md` 只是索引，不是原子任务本体。真正的执行单元必须是 `specs/changes/<change-id>/atomic-issues/Txxx.md`。

SDD 模板只提供文件入口。任务内容标准以 AutoMQ AI coding 方法论为准：每个任务必须是可独立派发给 AI worker 的 Atomic Issue。

所有本阶段生成的持久文档默认使用中文。代码标识、API path、命令、类名、字段名、错误码和日志原文保留原文。

执行或评审本阶段时，必须先读取并应用 `ai-dev-methodology/references/full-methodology.md` 的 “Atomic Boundary” 原文，再按 `ai-dev-methodology/references/artifact-completeness-spec.md` 的 “Stage 9: Atomic Task Planning” 检查正交维度、Required Artifacts、Completeness Criteria 和 Exit Gate。

生成任何 Txxx 前，必须把方法论中的 Atomic Boundary 当成硬定义，而不是经验提示：

| Boundary | 必须证明的问题 |
|---|---|
| 零决策 | worker 是否还需要选择产品、架构、字段、错误、UI、兼容性方案；如果需要，任务不合格 |
| 单层变更 | 是否只触达一个细层或一个已锁定的模块内契约闭包；如果跨层，是否已有不可拆的 contract/materialization 证明 |
| 上下文自包含 | 只拿 `atomic-issues/Txxx.md` 和列出的文件路径能否执行；如果必须读完整 `proposal/spec/plan`，任务不合格 |
| 验证闭环短 | 是否有一个短命令/短浏览器/短集成 proof 能证明当前 closure；如果要靠需求级大验收才能证明，任务不合格 |
| 错误不传播 | 当前任务失败是否会污染下游输入、共享状态、sealed artifact 或后续任务前提；如果会，必须拆分或重排 DAG |

这 5 条必须写入每个 packet 的 `atomicity_review.atomic_boundary_check`，并进入 compiled issue 的 `Atomicity Review`。只写“满足五条”不合格；必须逐条说明本任务为什么满足，或说明不满足时的 backflow/split。

创建 Atomic Issue 时必须使用 `ai-dev-methodology/templates/atomic-issue.md`。评审质量时使用 `ai-dev-methodology/references/artifact-review-rubric.md` 的 Atomic Issue Rubric，并参考 `golden-atomic-issue.md` / `bad-atomic-issue.md`。

本阶段还必须使用 `ai-dev-methodology/templates/task-dag.md` 产出 `Task DAG`。如果发现输入漏读、决策冲突、契约缺口或验证阻塞，必须使用 `source-intake-ledger.md` / `backflow-invalidation.md` 对应回流，不能继续生成实现 issue。

本阶段还必须使用 `ai-dev-methodology/templates/atomic-task-decomposition.md` 产出 `specs/changes/<change-id>/atomic-task-decomposition.md`。它是从模块契约图降解为 Txxx 的机器可审计记录，必须包含 Contract Granularity Admission Matrix、Contract Edge Decomposition Matrix、Owner Legitimacy Matrix、Provider Consumer Task Decision Matrix、Task Merge Split Decision Matrix 和 Provider Ownership Propagation Check。不能只在聊天记录、`tasks.md` 段落或单个 issue 里解释拆分理由。

本阶段还必须生成结构化 YAML sidecar。Markdown 是 reviewer 和 worker 的阅读入口；YAML 是机器校验入口。缺少 YAML sidecar 时不得进入 `atomic-execution-sdd`。

Atomic Issue 不再允许从全局文档自由手写总结产生。必须先生成 per-task sealed context packet，再编译成 Markdown：

```text
atomic-issue-packets.yaml -> atomic-issues/Txxx.md
```

`atomic-issue-packets.yaml` 是每个 Txxx 的高质量上下文包，必须包含 sources、semantic_carriers、decisions、contract excerpts、execution preconditions、consumed snapshots、provided obligations、invariants、verification 和 failure backflow。Markdown issue 只是该 packet 的渲染结果。如果 packet 无法填出这些字段，说明上游 contract/design/verification 没闭合，必须回流，不能生成薄 issue。

`semantic_carriers` 用于保存最容易在压缩中丢失的密集语义载荷，例如字段矩阵、selector/default/auto-create 规则、managed resource ownership、禁止 raw text 主路径、action->route->API 链路、explicit unreachable vs unknown、状态/错误/时序/默认值/权限/兼容规则，`external-capability-research.md` 中的官方事实/限制/失败语义/mock 外部边界，以及 `decision-surface-discovery.md` 中的 mode consumer、capability、frontend action、post-create consumer、persistent mutation、managed resource ownership、runtime lifecycle、runtime mode materialization parity、mock acceptance / repo-specific acceptance runtime surface。它不是摘要标签，必须写具体可执行细节。

密集 `REQ/SCN` 不能整段塞进每个相关 task。凡是一个 `REQ/SCN` 同时包含多个 owner 的语义，必须先在 `semantic-objects.yaml.semantic_carrier_projections` 或对应 `REQ/SCN.semantic_carrier_projections` 中拆成 `SCP-xxx` owner slice，再把 `SCP-xxx` 复制进对应 owner packet。task 可以在 `sources` 引用全局 `REQ/SCN` 作为来源，但执行语义只能来自它 owner 的 projection slice；frontend/API/acceptance/proof task 不得为了携带完整 source excerpt 而背 runtime/resource/provider owner 语义。

如果存在 `mechanism-design-model.md`，本阶段必须把每个影响实现的 `MECH/OPSEQ/EXTAPI/EVT/RMM/RLM/FCM/MIM` 行作为一等上游对象处理。Atomic Issue 必须从机制行 -> contract obligation -> verification -> task owner 的链路生成，不能从 AIP 摘要或 owner module 直接合并出小需求式 Txxx。

## Compiler Failure Triage Gate

如果 `atomic_issue_compile.py` 在 task planning 中失败，主 agent 不得直接修改 `atomic-issue-packets.yaml`、`task-dag.yaml`、`contracts.yaml`、`verification.yaml` 或编译出的 `atomic-issues/` 来“让 compiler 过”。必须先创建或更新：

```text
specs/changes/<change-id>/compiler-failure-triage.yaml
```

模板使用 `ai-dev-methodology/templates/compiler-failure-triage.yaml`。每条 compiler error 必须先分类：

- `current-task-owner`：当前 Txxx 确实是该层、资源、动作、状态或契约 owner，才允许在当前 packet 补执行语义。
- `move-to-existing-owner`：carrier/proof 属于已有 Txxx，必须移交 owner，并更新 DAG edge。
- `split-new-task`：当前 Txxx 过载，必须拆新任务。
- `upstream-backflow`：上游 contract/design/verification 缺失，必须回流。
- `validator-gap-blocked`：validator 规则过保守或歧义，记录为 blocked，不能靠扩大 task 通过。

没有 triage row 时，不得把 compiler failure 解释成“当前 packet 缺 proof 所以补 proof”。尤其禁止：

- 因 allowlist feasibility 报错而把 repository/runtime/frontend/page 目录加入不拥有这些层的 task。
- 在 `files_to_change` 写 `allowlist ceiling`、`validator feasibility`、`not an implementation instruction`、`support only` 等话术。
- 先改 packet 让 compiler 过，再反向同步 `task-dag.yaml` / `contracts.yaml` 合法化当前 packet。
- 对 frontend task 补 provider mutation / ownership readback / cleanup-protect proof。
- 对 API/check/readback consumer task 补 persistence/runtime/ownership proof，除非 triage 证明它是不可拆的同一模块内契约闭包。

`files_to_change` 永远是 worker 真实允许修改的文件范围，不是 validator allowlist ceiling。若当前任务只允许读某路径作为 pattern，应放入 `existing_code_references` 或 reference matrix，不能放入 `files_to_change`。

compiler failure 修复后，`atomic-issue-quality-review.yaml` 必须审查 `compiler-failure-triage.yaml`，确认每条错误是 owner/split/backflow 决策后的结果，而不是 compiler-driven owner 扩张。

Reference UI pattern 也属于容易丢失的密集语义，但不能只作为普通 carrier。凡是上游出现“参考某现有页面/组件/体验”“follow existing UI pattern”“像 Instance 创建体验”等信号，task planning 必须消费 `frontend-reference-pattern-matrix.md`，并把 owner 行复制到前端 packet 的 `reference_ui_patterns`。Compiled Atomic Issue 中必须出现 `Reference UI Pattern Obligations` 执行段，明确 reference file/component、must reuse/adapt、must not inherit、visual/layout obligation、interaction/state obligation 和 browser/visual proof。只写“参考现有实现”“使用 selector”“保持一致”不合格。

持久化 mutation / schema compatibility 也属于 dense semantic carrier。当上游出现 create/update/delete/resize/save/scale/import/bind、新 mode/资源类型、旧字段兼容、DB/Migration contract 或 “旧字段在新 mode 下合法缺失” 时，carrier 必须包含：authoritative state owner、writer path、旧 required field/resource、new null/default/derived/forbidden/compat rule、readback consumer、write proof 和 readback proof。只写 “persist canonical state / add ASG fields / additive migration” 不合格。

Managed resource ownership 也属于 dense semantic carrier。当上游出现 auto-create、default-created、generated resource、managed resource、select-existing 或 existing external resource 时，task planning 必须创建一个 owner issue，或写 locked N/A。owner packet 必须包含 `managed_resource_ownership` 行，并把 selection mode、create timing、provider writer、resource identity、owned/existing provenance、persistence owner、runtime/readback consumer、update rule、delete cleanup/protect rule、idempotency、failure behavior 和 verification 复制进执行章节。selector/UI/API validation issue 不能关闭该 ownership 生命周期，除非 packet 明确 locked N/A。

API wire shape / frontend-backend payload 也属于 dense semantic carrier。当上游契约、前端矩阵或 verification 出现 HTTP method/path/body、payload、DTO/VO、`deploymentConfig`、`workerSpec`、`capacity`、legacy compatibility、raw/top-level fields、resolvedConfig、forbidden payload 或 browser network assertion 时，task planning 必须消费 `API Wire Shape Matrix` 和/或 `frontend-api-payload-contract-matrix.md`。owner packet 必须包含：

- method/path/query/body canonical path。
- allowed keys 和 forbidden keys / semantic aliases。
- required/nullable/default/derived rule。
- legacy compatibility rule。
- exact-key verification。

只写 “active fields only”、“payload negative assertions”、“hidden fields absent”、“no raw ID textbox main path” 不合格；这些只能作为辅助 UI 负向断言，不能替代 wire-shape carrier。

但 carrier 不是执行说明。Atomic Issue 必须分两层：

- **Execution Brief**：给 worker 执行，只放目标、范围、文件、行为、步骤、验证、禁止事项和必要矩阵。语言必须短、自然、可操作。
- **Traceability Appendix / sidecar**：给机器审计和回流，保存 sources、semantic carriers、contract excerpts、decision trace。

carrier 的语义必须被物化到执行层的行为、步骤、验证或矩阵中，但不得把 carrier 原文整段重复塞进执行步骤。只写 “use selectors”“mode-specific”“参考现有实现” 不合格；为了通过 validator 复制大段 carrier、重复同一句语义、把 `frontend` 改成 `downstream UI` 等同义词游戏也不合格。

Worker brief 超限不是压缩关键词的理由，而是回流信号。若 `atomic_issue_compile.py` 报 execution brief / worker brief 过长，唯一允许的处理是：

- 拆分任务：说明该 Txxx 承载了过多 owner、operation、user action-flow、state transition 或 verification loop。
- 移交义务：说明某些 REQ/DS/C carrier 不属于当前 task owner；前端任务不能兜 provider mutation、ownership readback、cleanup/protect proof，后端任务不能兜 DOM/browser proof。
- 分层承载：机器审计所需长语义留在 packet structured fields / appendix，worker brief 只保留当前 owner 必须执行的具体行为、步骤、验证和禁止事项。

禁止为了 brief 变短而只保留 `DS-xxx`、`REQ-xxx`、`must materialize`、`validator needs`、`proof handoff` 等 gate phrase。若压缩后 worker 只能看到关键词而看不到具体字段、route/API、状态、错误、资源、owner 和 proof，必须回流重新拆分或改 owner assignment。

状态机类语义必须额外从 `stateful-behavior-matrix` 进入 packet。凡是 issue 的 source/contract/verification 出现 lifecycle、progress、event、status、terminal、polling、retry、task step、change tracking、mock state graph，packet 必须包含 `stateful_behavior` 行，且每行复制 operation、mode/variant、from/to state、trigger、guard、event/step、status、terminal、failure reason、producer/consumer、fixture 和 verification。不能只把 “实现 event graph / progress state / mock state graph” 写进 scope 或 carrier。

## No Broad Skeletonization

本阶段不得批量铺 `tasks.md`、空 sidecar、薄 packet 或只有标题的 Markdown 来制造进度。候选 packet、局部 Txxx、未锁定任务树、compiler 同步结果都不能进入执行。

任务规划必须按高密度语义对象先深后广：

```text
REQ/SCN/PDEC/external-fact/decision-surface/DEC/C/MIG/VER -> semantic_carrier -> Txxx packet -> compiled issue -> task DAG edge -> validator
```

每闭合一组语义对象后再扩展下一组。若任一 required upstream object 无法映射到 concrete carrier、contract、verification 和 Txxx packet section，当前阶段保持 `blocked`，只允许补 `specs/changes/<change-id>` artifact，不得生成可执行任务或开始改代码。

进入本阶段前必须确认所有 owner stage 已 `passed` 的 `routed-to-*` / `stage-owned` decision surface 已关闭。若 `decision-surface-discovery.md` 仍显示某个 surface 由已通过的 PRD、AIP、readiness、design、archaeology、migration、frontend-contract、contract 或 verification 决定，但状态仍是 routed/stage-owned，本阶段不得替它临场猜决策或生成兜底 Txxx，必须回流对应 owner stage。

禁止行为：

- 用未锁定候选 Atomic Issues 进入下游阶段。
- 只为通过 compiler 填表，但没有把 carrier 复制到执行章节。
- 用模板句替代真实执行语义。以下内容一律不算 source/fact/decision/carrier/files_to_change 的有效内容：`REQ-xxx 针对本任务的执行输入`、`Executable requirement semantics for REQ-xxx must be preserved`、`FACT-xxx constrains provider resources...`、`Decision xxx is locked...`、`Implement/prove xxx owned behavior here`、`Allowlist owner path ... when this backend contract requires it`。必须写真实字段、真实资源、真实状态、真实错误、真实 route/API、真实 provider call、真实 readback/verification。
- 为了让 validator 通过而收窄 `task-dag.yaml.sources`、packet sources 或 Semantic Consumption Matrix。任何上游 source/object 被移出某个任务，必须有 locked N/A / dropped decision、原因和下游替代 owner；不能因为 packet 没复制到就把 source 从任务里删掉。
- 部分 packet/issue 通过后先执行这些任务。
- 把 `atomic_issue_compile.py --check` 输出当成 pre-execution admission。

必须创建或更新：

```text
specs/changes/<change-id>/workflow-state.yaml
specs/changes/<change-id>/semantic-objects.yaml
specs/changes/<change-id>/contracts.yaml
specs/changes/<change-id>/verification.yaml
specs/changes/<change-id>/task-dag.yaml
specs/changes/<change-id>/backflow.yaml
specs/changes/<change-id>/atomic-issue-packets.yaml
```

模板来源：

```text
ai-dev-methodology/templates/workflow-state.yaml
ai-dev-methodology/templates/semantic-objects.yaml
ai-dev-methodology/templates/contracts.yaml
ai-dev-methodology/templates/verification.yaml
ai-dev-methodology/templates/task-dag.yaml
ai-dev-methodology/templates/backflow.yaml
ai-dev-methodology/templates/atomic-issue-packets.yaml
```

结构化 sidecar 必须和 Markdown 保持一致：

- `semantic-objects.yaml` 记录 `SRC/REQ/SCN/PDEC/DEC/MIG`、消费关系、required dense semantic carriers，以及 dense `REQ/SCN` 到 owner task 的 `semantic_carrier_projections`。
- `contracts.yaml` 记录每条 `C-xxx` 的 provider、consumer、trigger/normal/failure/consistency/timing/verification、provider/consumer issue、materialized_in 和 required dense semantic carriers。
- `verification.yaml` 记录每条 `VER-xxx` 的 command/step、expected_result、proves、required、blocks_done。
- `task-dag.yaml` 记录每个 `Txxx` 的 primary_module、sources、decisions、consumes/provides、owner-specific `semantic_carriers`/`SCP-xxx` projections、verification、files、issue 和 DAG edges。
- `backflow.yaml` 记录 `BF-xxx`、invalidated DEC/C/VER/T 和 supersession。
- `atomic-issue-packets.yaml` 记录每个 `Txxx` 的 per-task sealed context packet，并作为 `atomic-issues/Txxx.md` 的唯一生成源。

生成后必须运行：

```bash
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/atomic_issue_compile.py specs/changes/<change-id>
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py validate task-planning specs/changes/<change-id>
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py validate pre-execution specs/changes/<change-id>
```

任一失败都必须回流修上游 artifact、packet 和对应 Markdown；不得手改 `atomic-issues/Txxx.md` 绕过 packet，也不得只改 packet 让机器通过而不重跑 compiler。

`workflowctl.py` 会推导 dense semantics，不只检查手工声明的 carrier。凡是 `REQ/SCN/DEC/C/T` 或 packet source excerpt 中出现 selector/default/auto-create/no raw text、explicit failure vs unknown、action route/API/feedback 等语义，却没有分配到 `semantic_carriers` 并复制到 Txxx packet 执行章节，`task-planning` 或 `pre-execution` 必须 fail。不要把 “Source Context 已经写了” 当成 carrier；source excerpt 只证明来源，不承担执行语义。

`mechanism-design-model.md` 也是如此。`MECH/OPSEQ/EXTAPI/EVT/RMM/RLM/FCM/MIM` 只出现在 Source Context、atomic-planning context pack 或 plan appendix 时不算消费成功；必须进入 owner packet 的 execution-facing 字段，例如 behavior_details、stateful_behavior、runtime_materialization、managed_resource_ownership、external_side_effects、persistent_mutation_proofs、implementation_steps、verification 或 done_criteria。

本阶段必须在 `atomic-task-decomposition.md` 增加：

```markdown
## Mechanism Row To Task Map

| Mechanism row | Design model row type | Contract obligation | Verification | Candidate owner module | Candidate Txxx | Packet execution section | Merge/split decision | Backflow if not executable |
|---|---|---|---|---|---|---|---|---|
```

规则：

- 每个实现相关的 `MECH-*`、`OPSEQ-*`、`EXTAPI-*`、`EVT-*`、`RMM-*`、`RLM-*`、`FCM-*`、`MIM-*` 必须有行。
- `Merge/split decision` 不能只写 same owner/module。允许合并只在 same primary module、same semantic type、same operation/surface、same short verification loop 同时成立时；否则必须拆独立任务或 proof-only row。
- 对 runtime parity、autoscaling policy/evaluator、HPA create/update/prune、event producer、managed resource cleanup/protect、partial failure/residual cleanup、post-create consumers、frontend action/payload/readback 这些高风险机制，默认拆分，除非逐机制行给出强合并证明。
- 如果 row 的 provider API、event fields、runtime carrier、resource lifecycle、failure consistency、verification 仍需 worker 决策，必须回流 AIP/design/contract，不得生成 executable Txxx。

`decision-surface-discovery.md` 的每一行都必须进入 owner assignment：要么有 owner `Txxx` 并复制到 packet 执行层，要么有 locked N/A / Not Run risk / backflow blocker。尤其是 post-create consumer、logs/metrics/workers/connectors/update-config/delete/action dropdown 等 surface，不能因为 primary create flow 有任务就视为已覆盖。

`frontend-reference-pattern-matrix.md` 的每一行也必须进入 owner assignment。每个 `Reference ID` 必须映射到具体前端 `Txxx`，并复制到该 packet 的 `reference_ui_patterns`；browser verification 必须证明视觉/布局/组件/交互一致性，而不是只证明字段存在、payload 正确或 K8s 字段缺席。

`frontend-api-payload-contract-matrix.md` 和 cross-module `API Wire Shape Matrix` 的每一行也必须进入 owner assignment。每个 action/operation 必须映射到具体前端/API Atomic Issue，且对应 packet 的执行层必须出现 exact-key network/API verification。只在 `frontend-mode-leakage-negative-matrix.md` 中写 forbidden payload 不算 wire-shape 消费成功。

`external-capability-research.md` 中每个影响设计或验证的 Fact/Constraint 也必须进入 owner assignment：要么被消费为 ADEC/DEC、C、VER 和 `semantic_carriers`，并复制到 owner packet 的执行层；要么有 locked N/A / Not Run risk / backflow blocker。官方事实只出现在 research 文档、AIP 调研论证、Source Context 或 contract excerpt 时，不算 worker 可执行语义。

对 ASG infrastructure selector，至少按职责拆分并携带这些 carrier 内容：VPC、Subnet、SecurityGroup/SG、IAM Role/Profile、InstanceType；selector/default/auto-create/select-existing/derived display；禁止 raw AWS ID/text box 普通主路径；空列表、权限错误、wrong parent、invalid existing candidate、unknown reachability warning/non-blocking；UI render/DOM 或 service validation 的 verification。

本阶段还必须通过 Allowlist Feasibility Gate：`files_to_change` 不是估计范围，而是执行者唯一允许修改的文件集合。packet 中任何执行语义只要要求 API/VO/DTO、持久化/DO/mapper/migration、domain/service/entity、runtime/task/executor、frontend action source/handler/router/landing，就必须在 `files_to_change` 中包含对应真实文件或可定位目录。缺少对应层文件时，不能把任务交给执行阶段“想办法”，必须回流补考古、补契约或重拆任务；禁止用 properties JSON、private adapter、相邻页面、隐藏 helper 这类绕路实现来规避缺失文件范围。

对持久化 mutation，Allowlist Feasibility Gate 还必须检查旧 schema/resource 约束文件。若 owner issue 需要让某个 mode 合法缺失旧字段，`files_to_change` 必须包含实际 DDL/migration/schema、repository/mapper/DAO/DO 和 readback VO/API 落点，或有 locked N/A 说明这些层不适用。只包含新增字段迁移文件但不包含旧 required constraint 所在文件时，不能生成 executable issue。

每个持久化 mutation owner issue 的执行层必须包含：

- `behavior_details.state_persistence` 写清 state owner、writer、schema/null/default/compat rule 和 readback consumer。
- `backend_behavior_verification` 至少一行证明真实 writer write 成功，至少一行证明 detail/list/query/progress/event readback。
- `provided_contract_obligations` 中的 observable output 不能只写 persisted；必须写具体表/资源/事件存储或 readback surface。
- `preconditions_failure_handling` 中写明如果发现旧 required constraint 未被契约锁定，必须 backflow 到 migration/contract，不能实现阶段猜默认值或绕路存储。

如果任务规划或后续验收发现上游 DEC/C/VER 需要回流，必须先在 `backflow.yaml` 记录 `BF-xxx`，再运行：

```bash
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py backflow specs/changes/<change-id> BF-xxx
```

该命令会沿 contract source、provider/consumer issue、verification source 和 Task DAG 推导 direct tasks、downstream tasks 与 pending-rerun verification。运行后必须重写被标记的 Atomic Issue / verification / Markdown 矩阵，并重新执行 `validate pre-execution`。

本阶段必须维护最终 `Semantic Consumption Matrix`：消费所有上游 `REQ/SCN/PDEC/DEC/C/MIG/VER`，以及 `external-capability-research.md` 中影响实现/验证/mock 的 Fact/Constraint，派生 `Txxx` 和 Atomic Issue 摘录。进入执行前，每个 required upstream object 必须映射到至少一个 issue，或有 locked N/A / blocked reason；每个 issue 必须复制自己 owner 对应的 `SCP-xxx` / contract / decision slice，不能只保留 ID，也不能因为引用全局 `REQ/SCN` 就复制 sibling owner 的完整语义。

最终消费矩阵还必须消费每个 `Surface ID`。每个 surface 必须映射到至少一个 `Txxx`、`VER-xxx`、mock/frontend/backend matrix 行或 locked N/A；`Surface ID` 只出现在 source/context/appendix 时不合格。

本阶段产生的任务边界、依赖顺序、scope、prohibited changes 和验证拆分决策，必须写入 `specs/changes/<change-id>/decision-reviews/task-planning-decisions.md`，使用或等价满足 `ai-dev-methodology/templates/stage-decision-document.md`，并同步进入 Decision Registry。任务规划不能用“拆任务”掩盖上游未锁定的产品、设计或契约决策。

如果需求涉及 mock acceptance / no-cloud acceptance / repo-specific acceptance runtime，本阶段必须把 mock acceptance / repo-specific acceptance runtime 作为一等实现任务拆分。mock 代码、fixture、simulator、handler、coverage script、browser mock route 与业务代码一样需要明确 owner、文件范围、契约摘录和验证闭环。

这不是一句任务描述，而是必须在 task-planning 阶段生成的严格 case system。只要需求、AIP、contract、verification 或 frontend matrix 中出现 mock、外部依赖、无云验收、browser acceptance、provider/runtime/orchestrator/metrics/logs、repository-specific acceptance runtime 等信号，进入 `pre-execution` 前必须已经存在并通过 planning-mode 校验。automqbox/CMP 中 `playground` 也属于 repository-specific acceptance runtime 信号：

```text
specs/changes/<change-id>/mock-test-dimensions.yaml
specs/changes/<change-id>/mock-backend-matrix.yaml
specs/changes/<change-id>/mock-frontend-action-matrix.yaml
specs/changes/<change-id>/mock-event-state-matrix.yaml   # lifecycle/progress/event/status/terminal 存在时必需
specs/changes/<change-id>/mock-fixture-graph.yaml
specs/changes/<change-id>/mock-acceptance-cases.yaml
specs/changes/<change-id>/mock-acceptance.md
```

task-planning 阶段这些文件的 `result` 可以是 `planned` / `not_run`，但 case 行必须已经具体到可执行：dimensions、fixture_refs、真实被测 frontend/API/controller/service、只 mock 的外部依赖、browser_steps、network_assertions、DOM assertions、negative assertions、expected_result、proves、planned command/manual step 都必须写清楚。Backend matrix、Frontend action matrix、Event-state matrix 和 Packaged case 每一行都必须有 `command` 或 `manual_step`；packaged/runtime case 不能只写“浏览器打开并检查”，必须写清楚由哪个 Playwright/脚本/手工 runner 执行、会产生哪些 trace/HAR/screenshot/log evidence refs。缺少这些文件时，不能把 T005 写成“后续补验收”，也不能进入实现。

mock acceptance / repo-specific acceptance runtime 任务至少拆成三个契约闭包，不得默认合并成一个大 Txxx：

| Layer | Atomic issue responsibility | Required artifact | Verification boundary |
|---|---|---|---|
| Backend Mock Matrix | controller/service/mock-handler/mock-service/API/state 组合、fixture graph、fallback guard | `mock-backend-matrix.yaml` / `mock-fixture-graph.yaml` | 快速后端矩阵，证明真实 controller/service 没被 mock 掉 |
| Frontend Action Matrix | route/component/API-client/DOM/payload/user action 组合、mode leakage 负向断言 | `mock-frontend-action-matrix.yaml` | 快速前端 action 矩阵，证明真实页面动作和 payload |
| Packaged / Repo-Specific Representative Cases | packaged/runtime freshness、handler wiring、真实浏览器代表链路、handoff QA；automqbox/CMP 还包含 CMP top-level smoke | `mock-acceptance-cases.yaml` / `mock-acceptance.md` | 慢速打包集成样本，不承担全组合穷举 |

只有在某层完全不适用，并且有 locked N/A decision 和验证理由时，才能合并或省略。否则一个 Txxx 同时承担“补 mock 实现 + 设计 fixture graph + 前端 action matrix + packaged/runtime 验收”视为不原子。

`mock-acceptance-cases.yaml` 的 packaged case 必须通过 `backend_matrix_refs` 和 `frontend_action_refs` 回指前两层矩阵。若 frontend fixture need 已存在，每一行 fixture need 必须能追到 `mock-fixture-graph.yaml` 的 fixture id，并被至少一个 case 的 `fixture_refs` 消费。

本阶段必须运行：

```bash
python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/validate_mock_acceptance_cases.py \
  specs/changes/<change-id> --mode planning
```

`workflowctl.py validate task-planning`、`workflowctl.py validate pre-execution` 和 `validate_artifacts.py --stage task-planning/pre-execution` 会在检测到 mock acceptance / repo-specific acceptance runtime 信号时自动执行 planning-mode 校验。为了“先推进实现”而不生成这些 case artifact，属于门禁违规。

执行阶段还必须为这些 sealed 矩阵生成 row-level execution ledger，但不能把 `mock-backend-matrix.yaml`、`mock-frontend-action-matrix.yaml`、`mock-event-state-matrix.yaml` 或 `mock-acceptance-cases.yaml` 本身改成 passed。矩阵/case 文件是 sealed planning artifacts；执行证据必须写入 mutable `mock-acceptance-execution.yaml`。`task-verification-log.yaml` 只能做汇总，不能替代矩阵行证据。mock acceptance / repo-specific acceptance runtime owner task 的 `pass-task` 会自动运行：

```bash
python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/validate_mock_acceptance_cases.py \
  specs/changes/<change-id> --mode execution
```

因此每个 `MB-*` / `MFA-*` / `MES-*` / `MAC-*` blocking row 必须在 `mock-acceptance-execution.yaml` 中有对应 terminal entry：`target`、`row_id` / `case_id`、`result`、`command`、`command_exit_code` 或 manual verdict、`executed_by`、`assertion_refs`、`evidence_refs`、`completed_at`。一个聚合测试可以覆盖多行，但每一行都必须指向具体测试方法/断言；不得只在 verification log 里写“覆盖了 MB-001..MB-008”。

执行回写不是改一个总状态，也不是修改 sealed matrix/case 文件。自动命令行必须补 `command_exit_code: 0`，手工/浏览器步骤必须补 `manual_result` 或 `manual_verdict`；`evidence_refs` 必须指向真实测试报告、surefire 报告、Playwright trace、HAR、截图、日志或等价持久文件。`task-verification-log.yaml`、`execution-state.yaml`、`workflow-state.yaml`、`tasks.md`、`mock-acceptance.md` 和 `mock-acceptance-execution.yaml` 自身只能当汇总索引或证据账本，不能作为行级 evidence_ref。

本阶段必须执行 Contract Materialization Gate：把契约从全局文档中的引用，物化成每个 Atomic Issue packet 内的执行前提、可依赖事实、交付义务、不变量和失败回流规则，再编译成 Markdown。Atomic Issue 不能只写契约 ID 或一句总结。

## Contract Granularity Admission Gate

生成任何 Txxx 前，必须先检查每个 consumed/provided contract 是否已满足类型粒度。该门禁防止把未锁定 N2 决策压进实现阶段。

本阶段的最小输入不是粗 `contracts.yaml.contracts[C-xxx]`，而是 `contracts.yaml.contracts[C-xxx].executable_obligations[]` 和/或 `plan.md#Contract Executable Obligation Matrix` 中的 `C-xxx-OBL-yyy` 行。若某个 active contract 没有 `executable_obligations`，或只有粗 `C-xxx`、自然语言标题、`C-xxx-O1` 这类不可机器追踪 ID，必须回流 `cross-module-contract-sdd`，不能直接生成 task DAG。

每个 `C-xxx-OBL-yyy` 必须是 owner 单一的最小义务。task-planning 只能让 `semantic_contract_edge` 的 canonical owner task `provides` 这条 obligation。API wire、DTO/request carrier、frontend DOM proof、mock backend matrix、packaged acceptance proof 只能生成 carrier/proof/consumer edge，不能因为同属粗 `C-xxx` 就进入 `task-dag.yaml.tasks[Txxx].provides`。

进入本阶段先执行 Contract Ingress Invariant Check：

- `contracts.yaml.contracts[C-xxx].provider_module` 必须 owner-single。出现 `MOD-A / MOD-B`、逗号分隔、`and/or`、`和/或/及`、frontend proof owner、acceptance proof owner 时，必须回流 contract；不能在 task-planning 里任选一个 owner，也不能让多个 task 共同 `provides C-xxx`。
- 每个 active `contracts.yaml.contracts[C-xxx].executable_obligations[]` 必须有 `edge` 和 `edge_type`，且与 Markdown `Contract Executable Obligation Matrix` 同构。YAML 缺 `edge` 不允许靠 Markdown 行补；这说明机器入口不完整。
- Markdown `Contract Executable Obligation Matrix` 必须严格 16 列。`Edge type` 值只能出现在 `Edge type` 列；如果 `semantic_contract_edge` / `carrier_order_edge` / `verification_prerequisite_edge` / `proof_only_edge` 出现在 `Sub-obligation type`、`Semantic type`、`Operation / surface`、`Canonical owner` 或 `Owner module`，说明列漂移，必须回流 contract 重写表格。
- `Canonical owner` 是语义角色，例如 resource writer / event producer / UI action owner；`Owner module` 才是具体 `MOD-*`。`Owner module` 只能写 `MOD-*`，不能写 `VER-*`、`Txxx`、proof 名称或语义角色。
- `Sub-obligation type`、`Semantic type`、`Operation / surface` 不能被 `edge_type` 值填充。`Semantic type` 必须是 contract semantic type，例如 `Wire/API shape`、`External side effect`、`Resource ownership`；`Operation / surface` 必须是具体 operation，例如 `create ASG provider mutation`。
- `semantic_contract_edge` 只允许和 `Sub-obligation type=provider guarantee` 一起进入 provider ownership。`semantic_contract_edge + consumer assumption / verification proof / carrier-only` 是非法输入，必须回流 contract 重写；不能在 task-planning 中把它解释成 frontend/proof provider。
- 如果一个粗 `C-xxx` 只有 `proof_only_edge` / `carrier_order_edge` / `verification_prerequisite_edge`，它不是生产 semantic provider contract。它不能有生产 `provider_module/provider_issue`，也不能进入任何 task 的 `provides`。

```markdown
### Contract Granularity Admission Matrix

| Txxx | Contract / matrix row | Semantic type | Required details copied into packet | Missing detail | Backflow target | Admission |
|---|---|---|---|---|---|---|
```

规则：

- `Admission` 只能是 `admitted`、`blocked-backflow`、`locked-na`。
- `Contract / matrix row` 必须使用最小可执行义务行 ID，而不是只写粗 `C-xxx`。来自 `Contract Executable Obligation Matrix` 的每个 `Sub-obligation ID`，以及 `ESE-*`、`PCP-*`、`RMM-*`、`VIM-*`、`UI-ACT-*` 等专用矩阵行，都是一等 planning input：要么映射到独立 `Txxx`，要么进入某个 packet 的 `semantic_carriers` / `provided_contract_obligations` / `verification` / `files_to_change` 并有强合并理由，要么写 locked N/A / proof-only / backflow。只消费 `C-xxx` 不算 admitted。
- 对 `Wire/API shape`，`Required details copied into packet` 必须包含 canonical path、allowed keys、forbidden aliases、legacy rule、exact-key verification。
- 对 `State machine`，必须包含 operation、from/to state、trigger、guard、terminal、failure reason、producer/consumer。
- 对 `Resource ownership`，必须包含 writer、identity、provenance、cleanup/protect、idempotency。
- 对 `External side effect`，必须包含真实 adapter/API/resource call、desired/actual result、failure mapping、mock boundary。
- 对 `UI action closure`，必须包含 route/component、enabled/disabled、validation scope、API side effect、success/failure feedback。
- 对 `Error/warning`，必须包含 block/allow、error code/category、field/global location、warning readback。
- 对 `Compatibility/migration`，必须包含 old input/schema、new canonical model、mode-scoped mapping、forbidden retired fields、write/readback proof。

如果 `Missing detail` 非空，不能把该 detail 作为 worker 的实现判断题；必须回流到 design、frontend contract、cross-module contract 或 verification matrix。

前端/API payload 特殊阻塞：

- Txxx 涉及 API client、controller、DTO、VO、form submit 或 browser network proof，但没有 exact-key row。
- 任务只说 “no forbidden payload” 却没有列 forbidden fields。
- forbidden fields 只覆盖 inactive mode，没有覆盖 same-mode duplicate semantic aliases。
- same semantic data 在两个路径可传递，但任务没有 canonical path 和另一路 forbidden assertion。

## Module Contract Graph To Atomic Task DAG Gate

原子任务不是从文件目录、模块名或自然语言需求直接切出来的；必须从 `Module Contract Graph`、`Contract Semantic Type Matrix`、`API Wire Shape Matrix`、frontend/action/state/mock matrices 降解成任务。该 gate 是从模块契约图到 `tasks.md` / `task-dag.yaml` 的确定性拆分算法。

### Step A: Contract Edge Decomposition

先把每条跨模块边展开成 `edge + semantic type + operation/surface`，再考虑任务。边本身不是最小单位；一条边可能同时包含 API shape、状态机、副作用、错误、readback 和 UI action。

重要：`Contract Edge Decomposition Matrix` 不是把 `C-004` 复制一行到 `T004`。每条 active `C-xxx` 的 provider guarantee、consumer assumption、failure path、timing、state/resource owner、verification proof 都必须在 edge row 中可见。若一条 contract 内有多个资源、多个 consumer、多个失败路径、多个 state/event producer 或多个验证命令，必须拆成多行 edge，再进入 Step B/C 判断是否合并。

Step A 不允许“补救式考古拆契约”。它只能消费 contract 阶段已经 canonical 化的 `Contract Executable Obligation Matrix` 和专用矩阵行。如果上游 obligation row 缺少显式 `Edge type`、`Edge`、`Semantic type`、`Canonical owner`、`Fields/resource/state`，仍把多个 operation/resource/consumer/readback/proof 压在一行，或 `Split hint` 只是泛化句，当前阶段必须回流 `cross-module-contract-sdd` 重写 contract obligation；不得在 task-planning 中直接展开后继续，也不得通过扩大 `files_to_change`、扩大 current Txxx owner、补 carrier 或同步 `task-dag.yaml` 来合法化粗粒度契约。

高质量专用矩阵的语义必须从 contract 阶段沉淀到 canonical obligation row 后再进入本阶段。例如 `external-side-effect-contract-matrix.md` 的 ESE-001/003/004/006、`progress-change-producer-chain-matrix.md` 的 PCP-002/003/004/005 不能只作为 context pack 附录；它们必须对应到独立 edge row，或有 locked N/A/proof-only/merge rationale。否则视为 upstream contract granularity gap。

`Contract Executable Obligation Matrix` 的每个 active row 必须进入 `Contract Edge Decomposition Matrix`。`Edge ID` 必须保留 `Sub-obligation ID` 或专用 row ID（例如 `C-001-OBL-002`、`ESE-002`、`PCP-004`），让 validator 能追踪到 `task-dag.yaml` 和 `atomic-issue-packets.yaml`。禁止只把 `C-001` 写入 task consumes/provides 后声称整条 contract 已消费。

如果一个粗 `C-xxx` 内部包含多个 canonical owner，例如同一 contract 同时写了 API exact-key carrier、ASG runtime side effect、managed resource lifecycle、frontend DOM proof、acceptance packaged proof，当前阶段不得选择其中一个 task 去 `provides C-xxx`。必须先回流 `cross-module-contract-sdd` 把它拆成 owner 单一的子 contract，或至少在 task DAG 只提供 owner 合法的 `C-xxx-OBL-yyy` / 专用矩阵行，并把粗 `C-xxx` 保留为组合覆盖索引。此时 `contracts.yaml.provider_module/provider_issue` 也不能继续代表整条粗 `C-xxx`；真正 provider ownership 必须落在 owner-single `executable_obligations[].owner_module` 和 `task-dag.yaml.tasks[Txxx].provides_obligations`。不能出现 contract provider 是 `MOD-ASG-RUNTIME`，但某个 API-shape obligation 的 owner/provides 落到 `MOD-CONNECT-API-SERVICE` 后仍让粗 `C-xxx` 作为 ASG provider contract，也不能出现 acceptance packaged proof 提供生产语义 contract。

`task-dag.yaml.tasks[Txxx].provides` 的粗 `C-xxx` 只允许在一个严格条件下使用：该 Txxx 同时在 `provides_obligations` 中列出了该 contract 下全部 `semantic_contract_edge` obligations，并且这些 obligations 的 canonical owner 都等于该 Txxx 的 primary module。否则只能列 `provides_obligations`，或把粗 `C-xxx` 保留为组合覆盖索引。`provides_obligations` 只能列 owner-single `semantic_contract_edge` row；`carrier_order_edge`、`verification_prerequisite_edge`、`proof_only_edge`、proof 文件、fixture、browser harness、build freshness 都不能出现在这里。

```markdown
### Contract Edge Decomposition Matrix

| Edge ID | Source contract / row | Sub-obligation | From -> To | Operation / surface | Semantic type | Canonical owner | Owner module | Consumer module(s) | Provider guarantee to create/preserve | Consumer assumption to use | Failure / timing detail | State/resource owner | Verification proof | Candidate task owner |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
```

规则：

- 正式产物必须使用上面的完整表头，不能删列、改名、调换列或合并列。尤其必须包含 `Source contract / row`、`Sub-obligation`、`Failure / timing detail`、`State/resource owner`，否则 validator 会按列漂移处理并要求重写。
- `Canonical owner` 是 authoritative state/schema/validation/resource writer/event producer/UI action owner 这类语义角色；`Owner module` 是具体 `MOD-*`，不由调用方向决定。
- `From -> To` 是运行时调用方向；`Owner module` 是契约 provider 模块，不一定等于调用方向左侧。例如 `MOD-FRONTEND -> MOD-API` 的 request body canonical shape 通常由 `MOD-API`/schema validation 拥有。
- `Operation / surface` 必须具体到 create/check、update-config、resize、worker_spec update、delete、progress、detail tab、provider resource create/delete 等；不能只写“frontend/backend interaction”。
- `Candidate task owner` 先写 provider owner；consumer 是否需要 task 由 Step B 决定。

### Step B: Provider / Consumer Task Decision

每个 decomposed edge row 至少要有 provider obligation；是否生成独立 consumer implementation task，取决于 consumer 是否需要改代码。

```markdown
### Provider Consumer Task Decision Matrix

| Edge row | Provider task needed? | Provider task / existing task | Consumer task needed? | Consumer task / proof-only | Reason | Regression / acceptance proof |
|---|---:|---|---:|---|---|---|
```

规则：

- Provider 侧要新增/修改 guarantee 时，必须有 provider owner task；如果已有同 module/same semantic type/same operation task，可并入该 task 的 provided obligation。
- Consumer 侧需要修改调用、序列化、展示、状态消费、错误处理或权限 guard 时，必须有 consumer task；如果 consumer 已天然满足契约，只需要 proof-only verification 或 acceptance row。
- Consumer task 不能重新定义 provider 语义，只能写 “Given C-xxx/edge row 已成立，我按该 canonical contract 消费/提交/展示”。
- 如果 provider guarantee 和 consumer assumption 不匹配，不得拆任务，必须回流 `cross-module-contract-sdd`。

### Step B2: Owner Legitimacy Gate

先证明 owner 合法，再讨论是否合并。契约 owner 不是“和这个主题有关的任务”，而是能让这条 guarantee 变成真的模块：它拥有 authoritative state、schema/validation、resource writer、external adapter call、event producer、UI action source、mock/acceptance proof 或对应 readback proof 中的一个。

```markdown
### Owner Legitimacy Matrix

| Edge row | Row kind | Edge type | Canonical owner | Owner module | Proposed provider task | Proposed task primary module | Owner legitimacy | If not provider: carrier/proof edge | Backflow if invalid |
|---|---|---|---|---|---|---|---|---|
```

规则：

- `Row kind` 只能表达最小义务角色：`provider guarantee`、`consumer assumption`、`failure/timing`、`verification proof`、`carrier-only`、`locked N/A`。
- `Edge type` 必须显式区分：`semantic_contract_edge`、`carrier_order_edge`、`verification_prerequisite_edge`、`proof_only_edge`。默认是 `semantic_contract_edge`，只有 `semantic_contract_edge + Row kind=provider guarantee` 能进入 task `provides` / `provides_obligations` 语义契约。
- `semantic_contract_edge` 的 proposed provider task 必须是 `Owner module` 的 primary task，且 row kind 必须是 `provider guarantee`。若 `Owner module=MOD-ASG-RUNTIME`，API/DTO/frontend task 不能提供该 runtime/resource/external side effect contract；它只能通过 `carrier_order_edge` 排在 runtime owner 之前，或通过 consumer/proof row 消费该契约。
- `Row kind=consumer assumption` 表示“本任务依赖别人已经提供的语义”，不能出现在 `provides_obligations`，也不能用 `semantic_contract_edge` 关闭 provider 缺口。frontend progress/detail/browser 行如果只是消费 backend event/readback，应建成 consumer/proof edge；只有 frontend 自己提供 UI 可见承诺时，才写 `provider guarantee`，并由 `MOD-FRONTEND-*` owner task 提供。
- `carrier_order_edge` 表示“为了后续 owner 能实现，先准备 API shape、DTO、request carrier、route 或 schema carrier”。它只能形成 DAG 顺序边，不能写成当前 task `provides C-xxx-OBL-yyy`，也不能让 carrier task 成为 external side effect / resource ownership / runtime materialization 的 provider。
- `verification_prerequisite_edge` 表示某个 proof 文件、fixture、build freshness、browser harness 先于验证执行。它只能进入 Proof Owner Allowlist / DAG prerequisite，不能被建模成生产语义 provider。
- `proof_only_edge` 只能证明已有 provider guarantee 已成立；它不创建 provider guarantee，也不能关闭 provider task 缺失。
- 如果 proposed task primary module 与 canonical owner module 不一致，必须写明 `carrier_order_edge` / `verification_prerequisite_edge` / `proof_only_edge`，并从 provider obligation 中移除；否则 owner legitimacy 为 `invalid-backflow`。
- 同一个 provider guarantee 不能有多个 provider task owner。多个 task 可以有 consumer/proof/carrier 关系，但 provider owner 必须唯一；需要多人协作时用 DAG edge，而不是把同一个 provided obligation 分给多个 Txxx。
- Owner Legitimacy Matrix 不通过时，禁止进入 Task Merge Split Decision Matrix。合并不能修复 owner 错误。
- `atomic-planning-context-pack.md` 也必须遵守 owner 边界：Module And Contract Pack 的 `Provided contracts` 只能列 canonical provider module 真正提供的 semantic contract。API/DTO/wire carrier、frontend consumer、acceptance proof 不得因为参与同一需求就写成 `Provided contracts C-xxx`；必须写成 consumed/carrier/proof edge 或独立 API wire contract。

### Step B3: Semantic Carrier Projection Gate

Owner 边界通过后，必须先把全局 `REQ/SCN` 的密集语义按 owner 分账，再写 task packet。`REQ/SCN` 是用户场景级对象，常常同时包含 frontend selector、API payload、runtime side effect、managed resource lifecycle、event/readback、acceptance proof。它不是单个 task 的执行语义包。

```markdown
### Semantic Carrier Projection Matrix

| Projection ID | Global source | Owner module | Owner task | Operation / surface | Semantic type | Owner-specific semantics copied into packet | Excluded sibling owner semantics | Packet carrier row | Verification |
|---|---|---|---|---|---|---|---|---|---|
```

规则：

- `Projection ID` 使用 `SCP-xxx` 或 `SCP-xxx-Tyyy`。当同一个全局 `REQ/SCN` 要按多个 task 分账时，优先使用 `SCP-xxx-Tyyy`，并同步写入 `semantic-objects.yaml.semantic_carrier_projections` 或对应 `REQ/SCN.semantic_carrier_projections`。
- `Global source` 是 `REQ-xxx` / `SCN-xxx`；`Owner module` 必须等于该 slice 的 contract owner module；`Owner task` 必须是该模块下的 Txxx。
- `Owner-specific semantics copied into packet` 只写当前 owner 要兑现的字段、资源、状态、错误、route/API、proof。不能把同一个 `REQ/SCN` 的完整 dense carrier 复制给所有 task。
- `Excluded sibling owner semantics` 必须写清楚哪些同源语义不属于当前 task，例如 runtime/provider/resource ownership、frontend DOM proof、acceptance proof、API wire carrier。这个字段不是废话，它用来防止 validator 或 planner 把 sibling owner 的语义重新塞回当前 packet。
- `task-dag.yaml.tasks[Txxx].semantic_carriers` 应引用 `SCP-xxx` / `SCP-xxx-Tyyy` 或对应 owner-specific payload；`atomic-issue-packets.yaml.packets[Txxx].semantic_carriers` 必须带同一个 `projection_id`。
- 如果一个 Txxx 引用 dense `REQ/SCN`，但没有对应 `SCP-xxx` owner slice，`workflowctl.py validate task-planning/pre-execution` 必须失败。修复方式是补 projection 或移交 owner，不是把完整 `REQ/SCN` 塞进 packet。
- 如果 validator/compile 报 carrier 缺失，必须先判断缺的是当前 owner slice 还是 sibling owner slice。只有当前 owner slice 才能补进当前 packet；sibling owner slice 必须移交已有 owner task、拆新 task 或回流 contract/design。

### Step C: Merge Exception / Split Decision

不要机械地“一条边两个任务”，也不要把一个模块内所有义务塞成大任务。对这套方法论，默认动作是拆分到最小 owner closure；合并只是例外，不是目标。任务合并必须在 Owner Legitimacy Matrix 已通过后，同时满足四个条件。

```markdown
### Task Merge Split Decision Matrix

| Candidate rows | Proposed Txxx | Owner legitimacy passed for all rows? | Same primary module? | Same semantic type? | Same operation/surface? | Same short verification? | Decision | Reason / backflow |
|---|---|---:|---:|---:|---:|---:|---|---|
```

合并条件：

- 每个候选 row 都先通过 Owner Legitimacy Matrix，且没有 `invalid-backflow`。
- 同一个 primary module。
- 同一种 primary semantic type。
- 同一个 operation / user action / state transition / resource lifecycle step。
- 同一个短验证闭环能证明所有 rows。
- 若候选 rows 包含高风险义务，默认拆分。高风险义务包括 external side effect、runtime materialization/parity、managed resource ownership cleanup/protect、HPA/autoscaling/scaling policy、progress/change/event producer、failure consistency/residual cleanup。只有在四个合并条件全部为 yes，且 `Reason / backflow` 明确列出每个 obligation row ID、相同 owner、相同 operation/surface、相同 proof command 时，才允许合并。
- 合并不是压缩任务数量的目标。最小可执行义务优先于 owner 合并；owner 合并只是后置优化。若合并导致 worker brief 超限、carrier 堆词、文件范围跨 API/persistence/runtime/frontend 多层，或 task title/scope 退化成 “backend implementation / frontend UX / ASG support”，必须拆分或回流。

任一条件不满足，必须拆分或写 locked reason。典型必须拆分：

- `Wire/API shape` 和 `UI action closure` 分开；UI task 消费 wire contract。
- `Resource ownership` 和 `selector UI` 分开；selector task 不能关闭 create/delete ownership lifecycle。
- `External side effect` 和 `DB persistence/readback` 分开，除非同一 service method 的短测试同时证明真实 writer 和 readback。
- `State machine/event` 和 `frontend progress display` 分开；frontend 消费 event contract。
- `Runtime side effect` 和 `progress/change producer` 分开，除非同一个 primary module、同一个 operation、同一个短 backend/API proof 同时证明 provider/resource side effect、canonical change writer、last-change readback 和 change detail readback。
- `Mock/acceptance packaged runtime` 和 backend/frontend fast matrix 分开，除非某层 locked N/A。

### Step D: Task Shape

合格任务必须能用下面一句话描述：

```text
Given consumed contract rows R-in 已成立，
在 primary module M 的 semantic type S / operation O 内，
实现或保持 provider guarantee R-out，
用 verification V 证明，且失败不会污染下游输入。
```

如果一句话里出现多个 primary module、多个 semantic type、多个 operation，或 verification 需要需求级大验收，说明还没拆对。

### Step E: DAG Edges

Task DAG 由 provider/consumer 和 verification 关系生成，不由文件顺序生成：

- `semantic_contract_edge`: provider task -> consumer task。consumer 使用 provider guarantee；这类边才对应 task `provides` / `consumes`。
- `carrier_order_edge`: schema/API/wire/request carrier task -> 真正 provider 或 frontend/API-client task。它只表达顺序，不表达 carrier task 提供了 runtime/resource/external side effect contract。
- `verification_prerequisite_edge`: proof file、fixture、build freshness、browser harness task -> verification/acceptance task。它只表达验证前提，不表达生产语义 provider。
- `proof_only_edge`: provider task -> proof-only/acceptance task。proof 只能证明已实现路径，不反向定义生产语义。
- persistence/readback task -> runtime/endpoint/event/frontend read task：下游消费 readback 时使用 `semantic_contract_edge`；只准备 readback DTO/key 时使用 `carrier_order_edge`。
- resource ownership/provider side-effect task -> runtime/cleanup/readiness task：runtime 消费资源 identity/provenance 时使用 `semantic_contract_edge`。
- event/state-machine task -> progress/detail/browser task：UI 消费 terminal/failure/readback semantics 时使用 `semantic_contract_edge`。

执行顺序必须从这些 typed DAG edges 推导；不能因为文件互不冲突就并行执行 consumer task，也不能把 carrier/order/prerequisite 边伪装成 semantic contract provides/consumes。

## Atomicity Re-Splitting Gate

前置阶段越强，任务不能越粗。Task planning 必须先做强制重新原子化，再写 packet。判断标准不是“目录少不少”，而是 worker 是否还需要在实现阶段重新做取舍。

任一 Txxx 命中以下信号，必须优先拆分，而不是往同一个 packet 堆更多 carrier：

- 同时拥有多个独立用户动作闭环，例如 create、detail、update-config、resize、progress、event、delete 中超过 3 个。
- 前端任务同时覆盖多个页面/Tab/表单状态，且 `action_route_component` 超过 3 行、`mode_field_display_matrix` 超过 6 行或 `form_state_matrix` 超过 4 行。
- 状态机任务的 `stateful_behavior` 超过 5 行，或同时覆盖 create/update/resize/scale/delete 多个 operation。
- packet 需要超过 8 个 implementation steps、超过 8 个 source rows、超过 6 个 contract excerpts、超过 18 个 carrier rows。
- mock acceptance / repo-specific acceptance runtime 任务同时承担 backend mock matrix、frontend action matrix 和 packaged/runtime acceptance；除非有 locked N/A decision，否则必须拆成 Backend Mock Matrix、Frontend Action Matrix、Packaged Representative Cases。automqbox/CMP 中 packaged/runtime acceptance 才叫 packaged playground acceptance。
- 后端任务同时触达 API/VO、domain/service、persistence、runtime 四层，且不是一个明确的兼容机械改动。

拆分优先级：

```text
用户动作闭环 > 状态机 operation > provided contract > 文件 ownership > 验证闭环
```

合格 Atomic Issue 的执行形态应该像：

```text
Given provider contract C-in 已成立，
在一个 primary module / 一个用户动作 / 一个状态机 operation 内，
实现 provided contract C-out，
用一个短验证闭环证明。
```

如果一个 issue 看起来像“小型大需求”，即使 validator 能过，也必须回流重拆。

## Execution Readability And Anti-Gaming Gate

Atomic Issue 是执行工具，不是给 validator 的作文。编译后的 Markdown 必须满足：

- 执行主体先出现 `Execution Brief`，worker 读前半部分就知道改什么、怎么验、什么不能做。
- 完整 traceability 放在 `Traceability Appendix`，不得污染实现步骤。
- 执行层不得出现 “materialized task-planning carrier”“为了满足 validator”“exact proof”“regex”等机器门禁措辞。
- 不得用奇怪同义词绕 allowlist，例如把 `frontend` 改成 `downstream UI`、把 raw text 写成不自然短语。
- 同一句长 carrier 不得在多个执行章节重复出现；需要重复时应拆成矩阵行或更小 issue。
- 后端任务不能在执行层声明 browser/DOM proof；mock 任务需要引用前端 proof 时，写成 consumed/provided proof reference，不要伪装成自己实现 UI。
- frontend 任务不能只用 build/lint/payload 关闭用户动作；必须有 action-id 级 click/network/DOM/screenshot-or-trace 证明。

`atomic_issue_compile.py` 会检查过胖任务、重复 carrier、机械替换和执行层堆词。遇到失败时，正确修复顺序是：

1. 重新拆 Txxx owner。
2. 把跨层语义改成 consumed/provided obligation。
3. 把审计材料移到 sidecar/appendix。
4. 用自然语言把必要语义写成执行行为、矩阵行和验证断言。

不得通过删除 source、换同义词、扩大 allowlist 或复制更多 carrier 绕过。

## Atomic Issue Packet Compilation Gate

任务规划拆出 `Txxx` 后，先写 `atomic-issue-packets.yaml`，不要直接写 `atomic-issues/Txxx.md`。

`task-dag.yaml` 是 provider ownership 的唯一结构化来源。写 packet 时必须逐 task 重新从 `task-dag.yaml.tasks[Txxx].provides` 和 `provides_obligations` 派生 `provided_contract_obligations`、`atomicity_review.provided_contracts`、`primary_closure`、scope 和 module responsibility。禁止复用旧 packet 里的 provided/owns/guarantees 文案；只要 task DAG 的 provides/consumes 发生变化，该 Txxx packet 必须从空 packet 重新生成。

硬规则：

- `provided_contract_obligations` 只能列 `task-dag.yaml` 当前 Txxx 的 `provides` 或 canonical `provides_obligations`。若 T001 只是 API wire carrier，且 `provides: []`，它的 packet 不能写 `owns C-003`、`provided contract C-003`、`guarantees C-003-OBL-001`。
- 如果 `task-dag.yaml.tasks[Txxx].provides_obligations` 没有某个 `C-xxx-OBL-yyy`，packet 和 compiled issue 任何位置都不能用 `owns/provides/guarantees/implements/preserves` 语言声明该 obligation。可以写 `consumes/assumes/carrier for/proof of/prerequisite for/owned by Tyyy`。
- API wire shape、DTO/request carrier、frontend action carrier、fixture、proof file、browser harness、build freshness、packaged acceptance prerequisite 只能写入 `semantic_carriers`、`execution_preconditions`、`consumed_contract_snapshots`、`verification`、`Proof Owner Allowlist Matrix` 或 typed DAG edge；不能写入 `provided_contract_obligations`，也不能塞进 `task-dag.yaml.provides_obligations` 伪装成 provider obligation。
- Carrier/proof/consumer task 可以提到下游 contract，但必须用 “consumes / assumes / carrier for / proof of / prerequisite for / owned by Tyyy” 语言；不能用 “owns / provides / guarantees / implements C-xxx” 语言。
- 编译后的 `atomic-issues/Txxx.md` 必须与 packet 同步遵守该边界。Markdown issue 中的 `模块契约闭包`、`Provided Contract Obligation`、`Atomicity Review`、scope、完成标准不能出现 task DAG 没有授权的 provider 声明。
- Proof-only / acceptance task 不提供生产 semantic contract。它只能证明已有 provider guarantee，或提供独立 acceptance/proof artifact；若需要把 acceptance guarantee 建成 semantic contract，必须在 `contracts.yaml.provider_module/provider_issue` 和 task DAG 中显式建成独立 canonical owner，而不是在 acceptance packet 里顺手声明 `provided C-xxx`。
- Acceptance / proof-only task 的 `files_to_change` 只能包含 mock/fixture/playground/acceptance test/harness/evidence ledger 这类 proof owner 文件。可以在 `existing_code_references`、`consumed_contract_snapshots` 或 verification 里引用生产 controller/service/runtime 路径来证明真实路径被调用，但不能把生产业务源码放进 `files_to_change`。如果 proof 失败需要改生产代码，必须回流到对应 provider owner Txxx，而不是扩大 acceptance task。

每个 packet 必须回答：

- 本任务为什么存在，来自哪些 `REQ/SCN/PDEC/DEC/C/VER`，执行语义是什么。
- 本任务为什么是原子任务：先填写 `atomicity_review`，说明唯一 primary closure、用户动作闭环、状态机 operation、provided contract、验证闭环、考虑过的拆分候选，以及若合并多个闭环为什么不能拆。
- 本任务必须携带哪些 `semantic_carriers`：字段、状态、错误、默认值、selector、禁止路径、action route、mock fixture、runtime timing 等具体语义，且这些语义复制到了哪些执行章节。
- 执行前世界已经成立哪些事实，证据是什么；前提不成立时回流到哪一阶段。
- 当前任务能依赖哪些 provider guarantee，包含字段、状态、错误、时序、幂等、默认值、兼容边界。
- 当前任务必须向哪些 downstream consumer 提供什么 observable guarantee。
- 必须保留哪些旧行为、不变量、权限、错误、兼容语义。
- 修改哪些精确文件，按什么步骤修改，禁止哪些临时决策。
- 用什么验证证明，expected result、proves、failure meaning 是什么。

编译规则：

```bash
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/atomic_issue_compile.py specs/changes/<change-id>
```

检查规则：

```bash
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/atomic_issue_compile.py specs/changes/<change-id> --check
```

`--check` 只证明 `atomic-issue-packets.yaml` 与已生成的 `atomic-issues/Txxx.md` 同步，不证明任务树可执行。进入执行仍必须通过 `workflowctl.py validate pre-execution` 和 `validate_artifacts.py`。

compiler 失败不是格式问题，而是上游语义未物化。典型失败必须回流：

- `consumed_contract_snapshots` 只有 `C-001` 或一句摘要。
- `semantic_carriers` 缺失，或只写 “use selectors / mode-specific / same API paths / 参考现有实现”。
- 上游 `REQ/PDEC/DEC/C` 的密集语义没有出现在对应 Txxx packet，例如 selector/default/auto-create、no raw text、action route、错误码、状态机、mock fixture 状态没有进入 issue。
- `execution_preconditions` 只有 `T001 done`，没有 already-true observable facts。
- `provided_contract_obligations` 没有 downstream consumer、observable output 或 verification。
- `verification` 缺 expected result / proves / failure meaning。
- packet 出现 `见 plan`、`see spec`、`according to Decision Registry`。
- packet 的语义要求修改 API/VO、持久化、runtime lifecycle、event/progress、frontend action route，但 `files_to_change` 没有对应层文件；这是 allowlist feasibility gap，不是执行者可以临场扩 scope 的普通缺口。

## Context Rehydration Gate

开始生成 `tasks.md` 和 Atomic Issues 前，主 agent 必须从磁盘上的 canonical artifacts 重新恢复上下文，不能依赖聊天历史、压缩摘要或 subagent 记忆。

必须重新读取或等价核对：

- `source-intake-ledger.md`
- `proposal.md` / `spec.md`
- `plan.md`
- Decision Registry 和 `decision-reviews/*.md`
- code archaeology / new-feature design / migration diff 产物
- frontend contract、cross-module contract、verification matrix
- Backflow Invalidation Matrix，如存在
- mock acceptance / repo-specific acceptance runtime、runtime lifecycle、mode semantic、frontend action route、API flow DAG 等适用矩阵

必须先生成或更新 `specs/changes/<change-id>/atomic-planning-context-pack.md`，再写 `tasks.md` / `atomic-issues/Txxx.md`。

Context Pack 必须包含：

```markdown
## Source Rehydration Ledger
| Artifact | Path | Read status | Last relevant update | Consumed for task planning? | Missing/blocked reason |

## Upstream Semantic Index
| Object ID | Type | Executable semantics copied | Semantic carriers that must survive | Source artifact | Required downstream issue? | Status |

## Module And Contract Pack
| Module | Owned state/resources | Provided contracts | Consumed contracts | Boundary decision | Verification implication |

## Frontend Action Pack
| Action | Source component | Route builder/API | Router definition | Landing component/file | Mode branch | Forbidden inherited UI/API | Verification |

## Mock / Acceptance Runtime Pack
| Area | Mock/runtime boundary | Real contract source | Progress/change semantics | Handoff QA requirement | Verification |

## Verification Pack
| Verification | Command/step | Expected result | Proves | Failure meaning | Environment/owner |

## Task Generation Constraints
| Constraint / carrier | Source | Applies to | Must appear in packet section | Verification |
```

阻塞条件：

- 任一 required canonical artifact 未重新读取且无 N/A 理由。
- 任一 REQ/SCN/PDEC/DEC/C/MIG/VER 只出现在聊天记忆或压缩摘要中，没有落盘 source。
- Context Pack 的 `Executable semantics copied` 只有 ID、标题或一句摘要。
- Context Pack 没有列出 dense semantic carriers，或者 carrier 没有映射到 Txxx 和 packet section。
- Frontend action、mock/runtime、mode、progress/change、verification expected result 任一适用维度缺失。
- Stateful behavior、event/progress、terminal/polling、mock state graph 任一适用维度缺失，或只存在自然语言摘要而没有矩阵行。
- 任何非主 agent 生成的 context pack 或最终 task tree 未经过主 agent 本地重建和 validator/rubric 复核。

## No Subagent 任务规划纪律

Atomic Task Planning 的生成工作不使用 subagent；主 agent 必须亲自生成 canonical task tree、packet、DAG 和编译产物。

硬规则：

- 主 agent 必须亲自生成 `tasks.md` 和 `atomic-issues/Txxx.md`，并维护 Semantic Consumption Matrix、Contract Materialization Coverage、Requirement Composition Coverage 和 Task DAG。
- 不启动 subagent 生成 atomic tasks、修 packet、修 Markdown、签 receipt 或决定 task tree。
- 不得让任何外部并行 agent 只拿 PRD/AIP/草案从零生成 atomic tasks。这样会绕过 source consumption、module boundary、contract closure 和 verification expected-result 证明。
- 任何候选任务包必须由主 agent 对每个 Txxx 逐项映射 REQ/SCN/DEC/C/VER、primary module、Files To Change、Consumed/Provided Contract Snapshot、Verification expected result 和 Task DAG predecessor。
- 本地审计指出的 blocker 未关闭时，本阶段保持 blocked；不得把 blocker 改写成 “risk” 后进入 execution，除非用户或 owner 明确接受对应 Not Run / risk。
- 如果 Atomic Issue 不自包含，正确动作是回流重写 issue，而不是要求执行者去读完整 `proposal/spec/plan` 补语义。

唯一受控例外：在 `atomic_issue_compile.py --check`、`validate_artifacts.py --stage task-planning`、mock planning validator 和 `workflowctl.py validate task-planning` 通过之后，`workflowctl.py validate pre-execution` / `pass-stage task-planning` 之前，必须启动只读 reviewer subagent 做 **Pre-execution Atomic Issue Quality Review**。这是同步阻塞 review，不是并行 lane。主 agent 启动 reviewer 后必须等待 final findings，单次等待超时必须设置为至少 30 分钟；30 分钟内未返回时不得 fallback 到 `main-local` pass，只能继续等待或将本阶段标记为 `blocked`。等待期间禁止继续修 artifact、运行 pass-stage、进入 execution 或把部分输出当成通过证据。

reviewer subagent 只读以下上下文：

- `proposal.md` / `spec.md`：仅作为 source ID 和验收背景，不允许据此重设计。
- `plan.md`、`design-context-pack.md`、`contract-context-pack.md`、`atomic-planning-context-pack.md`。
- `contracts.yaml`、`verification.yaml`、`task-dag.yaml`、`atomic-task-decomposition.md`、`compiler-failure-triage.yaml`、`atomic-issue-packets.yaml`。
- 编译出的 `atomic-issues/`。
- 存在即读的阶段矩阵：`frontend-*matrix.md`、`api-wire-shape-matrix.md`、`external-side-effect-contract-matrix.md`、`runtime-materialization-parity.md`、`stateful-behavior-matrix.*`、`progress-change-producer-chain-matrix.md`、`runtime-test-topology-matrix.md`、mock planning case artifacts。
- 最新 validator 输出。

reviewer 不读聊天思考过程，不接收主 agent 的修复意图，不改文件，不运行 pass-stage，不新增产品/架构决策。reviewer 只输出 findings：是否存在 validator-driven wording、Source Context 写成当前任务要求、DS/REQ/C gate phrase、错 owner proof、frontend/backend proof 跨层、brief 超限后压缩关键词、不原子任务、漏消费矩阵，或 compiler failure 后通过扩当前 task / 扩 `files_to_change` / 反向同步 task-dag 来过 gate。

reviewer 审查 atomicity 时必须先使用方法论原文的 Atomic Boundary 五条定义，而不是普通“小任务”直觉，也不是只看 `primary_closure`：

- 零决策：worker 不需要选择产品、架构、字段、错误、UI 或兼容性方案。
- 单层变更：只触达一个细层或一个已锁定的模块内契约闭包。
- 上下文自包含：只拿 `atomic-issues/Txxx.md` 和列出的文件路径能执行，不需要回读完整 `proposal/spec/plan`。
- 验证闭环短：有短命令、短浏览器、短集成或短人工 proof 证明当前 closure。
- 错误不传播：当前任务失败不会污染下游输入、共享状态、sealed artifact 或后续任务前提。

`primary_closure`、`user_action_flows`、`stateful_operations`、`provided_contracts` 和 `verification_loops` 只是拆分辅助证据，用于判断单层变更和验证闭环是否成立。它们不能替代上述五条定义；一个 issue 即使只有一个 primary closure，只要仍需要决策、不自包含、跨太多层、验证过长或错误会传播，就必须判定 atomicity blocked 并回流拆分、移交 owner 或重写 packet。

主 agent 必须把 review 结果写入 `specs/changes/<change-id>/atomic-issue-quality-review.yaml`。任一 blocking finding 必须回流 task-planning 重新拆分、移交 owner 或重写 packet，并重跑 compile/validators/review；不能把 finding 改写成非阻塞风险。只有 subagent 不可用、系统禁用、用户明确禁止或当前任务规划为纯文档/trivial 时，才允许 `main-local` fallback，并且必须在 review artifact 写明 `subagent_fallback_reason` 和 `subagent_fallback_scope`。

## 输入

- `source-intake-ledger.md`，且没有 behavior-affecting `unread` / `blocked` source
- `atomic-planning-context-pack.md`，由主 agent 从 canonical artifacts 重新读取后生成，且无 missing/blocked required object
- `proposal.md`
- `spec.md`，如果存在
- `plan.md`，如果存在
- Decision Registry，且没有 `open` 决策
- Decision Consistency Matrix，且没有 active conflict
- `code-archaeology-sdd` 产物
- `cross-module-contract-sdd` 契约清单
- Contract Discovery Coverage Matrix，且没有未处理 residual risk
- Module Boundary Validation，且没有 `needs-contract-review` / `needs-design-review` / `unknown`
- Module Composition Verification，覆盖关键 REQ/SCN 的模块组合路径
- `migration-diff-analysis` 迁移计划
- `frontend-contract-design` 产物，如果涉及 UI
- `verification-matrix` 产物
- Backflow Invalidation Matrix，如发生过回流、supersession 或设计/契约/验证变化
- `Semantic Consumption Matrix`，覆盖 PRD 到验证阶段所有上游语义对象
- Verification Feasibility Gate，确认每条 required verification 的环境/fixture/setup owner
- Version Branch Alignment Matrix，如涉及多仓/版本/部署模板
- Artifact Rubric Scorecard，所有 required 维度无 0 分
- 如已存在结构化 YAML sidecar，必须读取并更新；如果不存在，必须从本阶段开始创建。

这些输入不是背景材料，而是 Atomic Issue 的来源闭包。任何 source 未读、决策冲突、contract discovery residual risk、P0/P1 Not Run、active issue 引用 superseded DEC/C/VER，都阻塞本阶段。

## Local Audit Gate: Planning Input Readiness Audit

任务规划开始前，主 agent 必须本地二次审计输入闭包和 `atomic-planning-context-pack.md`。审计不补设计、不写任务，只判断是否允许进入拆分。

输出：

```markdown
### Planning Input Local Audit Report

| Input/context area | Auditor finding | Missing canonical read | Missing executable semantics | Required backflow | Blocks task planning |
|---|---|---|---|---|---:|
```

阻塞条件：

- behavior-affecting source unread/blocked。
- Decision Registry open/conflict 或 supersession 未闭合。
- Contract Discovery residual risk 未处理。
- P0/P1 Not Run 或 `Blocks done=yes` verification 被放行。
- frontend/action/mock/runtime/cross-module artifact 缺失但需求适用。

## 原子任务标准

每个任务必须同时满足：

1. 零决策：任务中不存在“选择一种方案”。
2. 单层变更：后端、前端、DB、部署、Terraform、文档、测试分开。
3. 上下文自包含：任务描述包含所需 source reference。
4. 验证闭环短：任务有可执行的短验证。
5. 错误不传播：任务失败不污染后续任务输入。

不满足就继续拆。

### Atomicity Understanding / Re-Splitting Pass

生成任何 `Txxx` packet 前，主 agent 必须先做一次原子性理解与重拆，而不是把“原子任务”理解成“一个模块一个任务”。

输出必须进入 `atomic-planning-context-pack.md` 或 `task-planning-decisions.md`：

```markdown
### Atomicity Re-Splitting Review

| Candidate | Primary closure | User action-flow(s) | Stateful operation(s) | Provided contract(s) | Verification loop(s) | Fileset reason | Split candidates considered | Decision | Owner issue / backflow |
|---|---|---|---|---|---|---|---|---|---|
```

判断顺序固定：

```text
用户动作闭环 > 状态机 operation > provided contract > 验证闭环 > 文件 ownership
```

一个候选任务如果包含多个用户动作、多个状态机 operation、多个 provided contract 或多个验证闭环，默认拆分。只有满足以下任一强理由才可合并，并且必须写入 packet 的 `atomicity_review.merge_rationale`：

- 同一表单提交、同一后端事务、同一状态写入路径或同一状态迁移无法拆开验证。
- 同一个 source component、landing component、route/API 和 browser proof 同时证明两个紧耦合 action，例如打开 modal + modal submit。
- 拆开会导致中间态无法编译、无法表达同一契约，或破坏 schema/contract 兼容迁移。
- 同一条测试方法/命令必须同时断言该闭包的正向与负向边界。

弱理由一律不合格：同一模块、同一页面、相关工作、任务数少、方便、为了覆盖、为了过 validator、一次做完。

`atomicity_review` 是生成期证明，不是后补作文。每个 packet 必须填写：

- `primary_closure`：只能命名一个用户动作闭环、一个状态机 operation 或一个 provided contract。
- `user_action_flows`：本任务实际拥有的动作闭环；不适用时写 `N/A: ...` 并说明原因，不能留空。多于一个真实动作时必须有强合并理由。
- `stateful_operations`：本任务实际拥有的状态操作；不适用时写 `N/A: ...` 并说明原因，不能留空。多于一个真实 operation 时必须有强合并理由。
- `provided_contracts`：本任务提供或维护的对外契约。
- `verification_loops`：本任务的短验证闭环；不适用时写 `N/A: ...` 并说明为什么这是纯人工审计或被上游验证覆盖。多于一个真实验证闭环时必须有强合并理由。
- `fileset_reason`：为什么这些文件属于同一 closure，而不是目录便利。
- `split_candidates_considered`：至少列出被考虑拆出去的候选；若没有，也要说明为什么没有。
- `merge_rationale`：只在合并多个 closure 时使用；空白不影响单 closure 任务。
- `still_atomic_because`：用一句话证明 worker 不需要在实现阶段做取舍。
- `if_not_atomic`：固定写回流方式，不允许让执行者临场拆。

缺少 `atomicity_review` 或合并理由薄弱时，不得生成 `atomic-issues/Txxx.md`，也不得把失败解释成 validator 误报。

后端任务的“单层”必须按细层判断，不是按 `cmp-*` 目录判断：

| Backend layer | Typical ownership |
|---|---|
| backend-api | Controller、Param/DTO/VO、OpenAPI、鉴权/HTTP path |
| backend-domain | service/manager/domain entity、业务校验、错误语义 |
| backend-data | DO/repository/mapper/migration、兼容读取/写入 |
| backend-runtime | async task、payload、executor、provider/cloud runtime lifecycle |
| backend-observability | event/metric/log/progress state exposure |

一个后端 issue 同时触碰 3 个以上细层时，默认不原子。只有在“同一契约必须一次性迁移，否则中间态无法编译/无法表达兼容”的情况下，才允许作为 exception，并且 packet 必须填写 `backend_layer_boundary`：primary layer、touched layers、split decision、why not split、forbidden cross-layer decisions、verification boundary。

## Atomic Issue 标准

每个任务必须生成独立文件：

```text
specs/changes/<change-id>/atomic-issues/Txxx.md
```

Atomic Issue 必须是 self-contained，而不是只引用全局文档 ID。一个没有读过完整 `proposal/spec/plan` 的 AI worker，只拿到该 issue 和 issue 中列出的文件路径，应能完成实现和验证。

Atomic Issue 必须达到“可直接创建 issue”的粒度：标题说明动作，正文闭包语义，文件范围可定位，步骤可执行，验证可判断。它不是 checklist item，也不是 `plan.md` 摘要。

每个 Atomic Issue 必须绑定一个 primary module。跨模块一致性通过 consumed/provided contract 和 verification 表达，而不是把多个模块实现塞进同一个 issue。

### Contract Materialization 标准

Atomic Issue 必须是 sealed execution packet。一个无上下文 worker 只拿到 issue，应知道“执行时世界已经是什么样、当前任务要把世界变成什么样、哪些判断禁止重新做”。

每个非纯文档 issue 必须包含以下章节；纯 verification issue 也必须包含适用的前提和断言。

```markdown
## 执行前提
| Upstream task/contract | Already true before this task starts | Evidence / verification that should have passed | If false |
|---|---|---|---|

## Consumed Contract Snapshot
| Contract | Provider task/module | This task may assume | Field/state/error/timing details | Forbidden interpretation |
|---|---|---|---|---|

## Provided Contract Obligation
| Contract | Downstream consumer | This task must guarantee | Observable output / state | Verification proving it |
|---|---|---|---|---|

## Invariant Carryover
| Invariant | Source | Must remain true after this task | Regression check |
|---|---|---|---|

## Preconditions Failure Handling
| Failure | Classification | Required backflow | Do not do |
|---|---|---|---|
```

内容要求：

- `Already true` 必须写事实，例如 schema 字段存在、API 路径已命中、状态映射已 externalize、前置验证已通过；不能只写 “T001 completed”。
- `This task may assume` 必须复制 consumed contract 的完整语义：输入、输出、字段、状态、错误、时序、幂等、默认值、兼容边界。
- `This task must guarantee` 必须写 downstream consumer 的假设和当前任务需要提供的可观察事实。
- `Forbidden interpretation` 必须写本任务不得重新解释的点，例如不得改变外部 enum、不得把内部状态暴露给 consumer、不得换 API path、不得改变错误码语义。
- `If false` 必须写停止和回流路径；发现前提不成立时不能临时修上游或自作主张改契约。

缺少这些章节，或章节只有 ID/一句话摘要，Atomic Issue 不合格。

### 必须包含的章节

```markdown
# Txxx: <中文动宾短标题，保留代码/API 标识原文>

## 目标
说明本任务解决什么问题、对应哪块用户/工程价值。

## 范围
| In scope | Out of scope |
|---|---|

## 来源上下文
摘录必要 REQ/SCN/DEC/PDEC/MIG/Contract 内容。不能只写 ID。

## 模块契约闭包
| Item | Content |
|---|---|
| Primary module |  |
| Module responsibility |  |
| Owned state/data/resources touched |  |
| Consumed contracts assumed true |  |
| Provided contracts implemented/preserved |  |
| Internal invariants |  |

## 锁定决策
| Decision | Exact decision | Why it matters here |
|---|---|---|

## 契约摘录
| Contract | Trigger | Normal path | Failure path | Consistency | Timing | Verification excerpt |
|---|---|---|---|---|---|---|

## 执行前提
| Upstream task/contract | Already true before this task starts | Evidence / verification that should have passed | If false |
|---|---|---|---|

## Consumed Contract Snapshot
| Contract | Provider task/module | This task may assume | Field/state/error/timing details | Forbidden interpretation |
|---|---|---|---|---|

## Provided Contract Obligation
| Contract | Downstream consumer | This task must guarantee | Observable output / state | Verification proving it |
|---|---|---|---|---|

## Invariant Carryover
| Invariant | Source | Must remain true after this task | Regression check |
|---|---|---|---|

## Preconditions Failure Handling
| Failure | Classification | Required backflow | Do not do |
|---|---|---|---|

## 现有代码参考
| Pattern/reference | Exact path | What to follow | What not to inherit |
|---|---|---|---|

## 修改文件
| Path | Required change | Ownership / notes |
|---|---|---|

## 行为细节
| Item | Detail |
|---|---|
| Inputs |  |
| Outputs |  |
| Error behavior |  |
| State / persistence |  |
| Compatibility |  |
| Boundary conditions |  |

## 实现步骤
1. ...

## 验证
| Check | Command/manual step | Expected result | Proves | Failure meaning / Not Run risk |
|---|---|---|---|---|

## 禁止事项
- ...

## 完成标准
- [ ] ...
```

不合格信号：

- 只写 `REQ-001/C-002/DEC-003`，没有摘录具体语义。
- Consumed / provided contract 只写 ID、标题或一句话，没有物化成可依赖事实和交付义务。
- Execution Preconditions 只写前置任务 ID，没有写前置任务完成后已经成立的事实。
- Provided Contract Obligation 没有写 downstream consumer 或 observable output。
- Preconditions Failure Handling 缺失，导致 worker 发现前提不成立时会临时补猜或改上游。
- Source Context 只有一句摘要，缺少输入、输出、错误、状态、边界条件。
- 缺少 primary module、consumed contracts 或 provided contracts。
- 一个 issue 同时改多个模块的 provided contracts。
- issue 需要重新定义模块边界或跨模块契约。
- Locked Decisions 引用 “Decision Registry” 或 “见 plan”，没有复制具体决策。
- Contract Excerpts 缺少 Failure / Consistency / Timing / Verification。
- Files To Change 没有 repo-relative exact path，或只写 “new helper under ...” 而没有命名规则、包路径和发现规则。
- Files To Change 与行为语义不匹配：例如 issue 要求 API 返回字段但没有 VO/controller/client 文件，要求持久化兼容但没有 DO/mapper/migration，要求事件/progress/runtime lifecycle 但没有 task/executor/event 文件，要求操作下拉或 update route 但没有 source component、handler/router 和 landing component。
- Implementation Steps 要求实现者自行选择字段名、错误码、UI 表现、路径拼接、事务边界或验证方式。
- 验证只写“run tests”，没有 expected result。
- 写“参考现有实现”，但没有列具体文件/方法/页面。
- 要求实现者自行选择错误码、字段名、UI 表现、路径拼接、事务边界或验证方式。
- 单个 issue 必须读完整 `plan.md` 才能知道怎么做。
- `atomicity_review` 没有证明唯一 primary closure，或多动作/多 operation/多验证闭环只用“同一模块/同一页面/相关”合并。
- 标题是 “post-create consumers / frontend UX / fixture graph / representative acceptance / 完整前端” 这类集合词，但没有被拆成独立 action、stateful operation 或 verification owner。
- 执行层出现 `planned browser action`、`rows do not execute tests yet`、`score 2 planned`、`future Playwright` 却把任务当作可执行 proof。

缺少 Atomic Issue 的任务会让 AI 在实现阶段重新推理并引入 N1 收敛。

## 任务生成步骤

### Step 1: 校验 Source Intake Ledger

先读取或创建：

```text
specs/changes/<change-id>/source-intake-ledger.md
```

必须确认：

- 用户提供的 PRD、AIP、飞书链接、issue、补充设计、Terraform/API 草案、历史方案、代码路径、运行时证据都在 Source Inventory。
- `Read status=unread/blocked` 的 source 没有被下游 REQ/SCN/DEC/C/MIG/VER 使用。
- 每个 behavior-affecting source 都映射到 Source To Semantic Object Map，或明确 `ignored/superseded` 并写原因。
- Source Conflict Matrix 中没有 `Status=open` 的冲突。

然后建立任务规划用的来源索引：

```markdown
| Source | ID | Summary |
|---|---|---|
| spec | REQ-001 |  |
| spec | SCN-001 |  |
| plan | PLAN-API |  |
| contract | C1 |  |
| migration | MIG-DELETE-1 |  |
| decision | DEC-001 |  |
| frontend | UI-001 |  |
| verification | VER-001 |  |
```

来源索引只能来自已读 source 和 locked semantic object。不能把未读链接、聊天记忆或全局 plan 段落直接压进 Atomic Issue。

### Step 2: 按层拆分

推荐层级顺序：

1. 数据模型 / DB migration
2. 后端 domain / manager / service
3. API / VO / permission
4. 部署 / cloud resource / Terraform / Helm
5. 观测 / event / metrics / logs
6. 前端 API client / types
7. 前端页面 / UI / i18n
8. Mock acceptance / acceptance runtime / fixture / simulator / strict acceptance
9. 测试 / docs / runbooks

跨层任务必须拆开。若跨层一致性需要保证，用契约和验证连接，不要合并成一个任务。

如果涉及 mock acceptance / no-cloud acceptance / repo-specific acceptance runtime，必须拆出独立任务，或在同一 primary module 的 issue 中显式包含 mock files 与 mock-drift verification。不能把 mock 作为“测试顺手补一下”留在验证任务或最终部署步骤里。

任务规划阶段只允许使用生产实现契约和验收维度来规划 mock/backend/frontend/packaged rows。若目标是 automqbox/CMP，不得读取或复制当前
`cmp-playground` 代码、`mock-acceptance-gate/references/cmp-playground.md`、验收适配器实现、
controller routing guard、packaged 启动或 playground fixture graph 细节，除非当前 Atomic
Issue 的 primary module 就是 playground 基础模块。实现前的 issue 必须写清真实生产代码
要调用的 adapter/API/resource 副作用，例如 provider create/update/delete、K8s
apply/scale/delete、Connect REST call、DB write/readback、event/progress write/readback。
后续 no-cloud adapter 或 automqbox/CMP playground 只在 mock-acceptance 阶段证明这些生产调用被验收适配器接住。

如果涉及 mock acceptance / no-cloud acceptance / repo-specific acceptance runtime，任务规划还必须为最终 `mock-acceptance` 阶段预留严格 case 系统，不允许只写 “packaged/browser smoke”：

- 生成或在 Txxx 中明确 owner `mock-test-dimensions.yaml`：维度、取值、coverage_sets、excludes/N/A 决策。
- 生成或在 Txxx 中明确 owner `mock-backend-matrix.yaml`：后端/controller/service/mock-handler/mock-service/API path/state 组合、fixture refs、命令、证据和 result。它是后端组合穷举或准穷举的快速证明面，不依赖 packaged/browser runtime。
- 生成或在 Txxx 中明确 owner `mock-frontend-action-matrix.yaml`：真实 route/component/API-client/DOM/payload/user action 组合、fixture refs、network/DOM/negative assertions、命令、证据和 result。它是前端动作组合穷举或准穷举的快速证明面，不依赖 packaged/browser runtime。
- 生成或在 Txxx 中明确 owner `mock-acceptance-cases.yaml`：每个 case 的 frontend route、real code under test、mocked external dependencies、browser steps、network assertions、DOM assertions、API assertions、negative assertions、fixture refs、evidence refs、result。
- 生成或在 Txxx 中明确 owner `mock-fixture-graph.yaml`：selector/detail/progress/capability 数据源、引用图、consumer page/API、contract source。
- 对 automqbox/CMP，task-planning 只生成或在 Txxx 中明确 owner `CMP Playground Coverage Matrix` 的 planned rows：每个用户流程必须能追到真实 frontend action/API client/controller/service、生产外部 adapter 副作用、backend/frontend matrix row 和 packaged case id。`CMP Playground Architecture Matrix`、验收适配器实现、real-controller routing guard、packaged runtime freshness 等当前 playground 架构事实必须推迟到 `mock-acceptance-gate` 执行阶段读取和填写。
- `mock-acceptance-cases.yaml` 中的 packaged cases 必须通过 `backend_matrix_refs` 和 `frontend_action_refs` 追溯到前两层矩阵；packaged/runtime case 只做代表性集成、freshness、真实浏览器路由和 handoff QA，不承担全组合穷举。automqbox/CMP 中这些 case 才是 packaged playground case。
- T008/acceptance issue 不能用 API smoke、route smoke、browser smoke、build、payload helper 测试关闭用户流程；必须引用 strict case validator、backend/frontend matrix row-level evidence 和 packaged case browser/network/DOM evidence。
- `mock-acceptance` stage 没有 receipt 时，product acceptance 必须保持 blocked。

Mock Atomic Issue 必须包含：

- mock 边界：真实被测模块、被替代外部依赖、禁止 mock 的 API/controller/service。
- real-vs-mock contract 摘录：path、body、response shape、enum、错误码、状态、progress/change terminal semantics、空值/不可用。
- fixture/simulator 状态表：happy path、failure path、edge case、terminal state、retry/partial failure。
- drift guard：可执行测试或脚本，证明 mock 输出与真实外部契约和前端消费方一致。
- display freshness：如果 mock 通过打包环境展示，列出 bundle/package/process freshness 验证。
- stateful behavior：如果 mock 涉及 progress/change/event/status/terminal，必须复制 `stateful_behavior` 行或等价 event-state fixture rows，覆盖每个 operation/mode/status/terminal/failure。只写 “mock state graph/progress fixtures” 不合格。

mock acceptance / repo-specific acceptance runtime 任务必须按三层拆分或在同一 primary module issue 中清楚分段；automqbox/CMP 的第三层名称可以使用 packaged playground：

```text
T-mock-backend-matrix -> T-mock-frontend-action-matrix -> T-packaged-representative-acceptance
```

如果只生成一个“大而全 packaged/browser 验收”任务，且没有把 backend/frontend 快矩阵作为独立 owner 和验证输入，该任务不合格。矩阵任务可以和对应 mock/frontend 实现任务合并，但完成标准必须独立列出对应 YAML、命令、evidence_refs 和 result。

Mock 任务完成标准不能只写“page/runtime can open”。必须证明自动化 mock acceptance 通过；浏览器/display 只是附加验收。

如果涉及前端，必须按 `frontend-contract-design` 的输出拆出 API client/types、page shell、data binding、layout、i18n、permission/actions、loading/empty/error、form/action-flow contract、browser/mock acceptance verification。

前端任务规划必须消费这些 frontend-contract artifact，不能只读 `plan.md` 里的摘要：

```text
frontend-page-inventory.md
frontend-action-inventory.md
frontend-route-component-matrix.md
frontend-mode-field-display-matrix.md
frontend-form-state-matrix.md
frontend-mode-leakage-negative-matrix.md
frontend-fixture-need-matrix.md
frontend-browser-verification-matrix.md
```

它们必须进入 `atomic-planning-context-pack.md#Frontend Action Pack` 和每个前端 packet 的专用字段。宽泛标题如“实现前端 UX”“完善创建页”“补详情页”“支持新 mode 页面”不合格，除非 packet 已拆到具体用户任务、页面入口、action、route/API、form 状态、fixture 和浏览器验证。

前端 Atomic Issue packet 必须包含：

```yaml
frontend_user_task:
  user_task_id: ""
  user_goal: ""
  entry_points: []
  page_routes: []
  visible_controls: []
  required_data: []
  primary_action: ""
  loading_empty_error_states: []
  success_next_state: ""
  failure_feedback: ""
action_route_component: []
mode_field_display_matrix: []
form_state_matrix: []
mode_negative_assertions: []
fixture_needs: []
browser_verification:
  required: true
  steps: []
  network_assertions: []
  dom_assertions: []
  screenshot_or_trace: []
  negative_assertions: []
  failure_meaning: ""
experience_rubric: {}
```

这些字段不是补充说明，而是执行契约。只要 packet 的文件范围、标题或 primary module 表明它是前端/UI/page/form/route/action/browser 任务，`atomic_issue_compile.py` 必须校验这些字段。

反过来，非前端 packet 不要生成空的 `browser_verification`、`experience_rubric`、`frontend_user_task`、`action_route_component`、`mode_field_display_matrix`、`form_state_matrix` 或 `fixture_needs` 段来写 `N/A`。后端/API/runtime/managed-resource/acceptance-boundary 任务如果需要说明浏览器证明属于别的 owner，只能写在 `consumed_contract_snapshots`、`prohibited_changes` 或 `done_criteria` 的 handoff/禁止项里；不能把 `Not applicable browser proof` 当成本任务 verification section。否则 planner 会重新把 proof owner 和 provider owner 混在一个 packet 里。

前端 Atomic Issue 还必须把 action 落点和字段展示拆到可执行粒度：

- 每个按钮、下拉项、tab action、行操作、创建后操作都必须有 `action_route_component` 行，包含 source component、handler/route builder、final route/API、router definition、landing component、mode branch、forbidden inherited UI/API 和 browser verification。
- 每个详情页、配置 tab、summary、update-config、resize、workers/metrics/logs/progress surface 都必须有 `mode_field_display_matrix` 行，包含当前 mode must show 字段、must hide 旧 mode 字段、fixture ref 和 DOM absence assertion。
- 如果一个 issue 标题类似“详情/resize/progress/capability 前端消费”，但没有字段级矩阵和 action-route 矩阵，必须回流重写 issue；不得进入执行。

如果涉及前端 mutation action 或 wizard/form submit，必须消费 `frontend-contract-design` 的 User-Flow / Submit-Flow 契约：

- UI issue 的完成标准必须包含真实 action side effect proof，例如 `click Submit -> POST /api/...` 或字段级错误。
- API client/types issue 不能声明用户流程完成。
- build/source inspection/page screenshot 不能关闭 mutation user-flow。
- build、lint、typecheck、tsc、payload helper、API client unit test 只能作为 supporting proof；没有 browser/DOM/network action-flow proof 时，UI/form issue 只能是 `implemented-pending-action-flow`，不能标 `passed/done/completed`。
- 如果缺少 `frontend-action-flow` verification，UI issue 必须保持 blocked，或回流到 `frontend-contract-design` / `verification-matrix`。

如果涉及已有或新增用户可见 action，必须同时消费 `frontend-contract-design` 的 Action-To-Route-To-Component 契约：

- UI issue 必须复制每个 action 的 visible text/i18n key、source component、route builder/click handler、final route/API、router definition、landing component/file。
- `Files To Change` 必须包含真实 landing component/file；不得只写“update page”或错误的相邻页面。
- 如果 action 落点复用旧页面，issue 必须复制 `Mode branch required` 和 `Forbidden inherited UI/API`，并要求在该 landing component 中实现 mode-specific 分支。
- `Verification` 必须包含 route/component render proof 和 negative inherited-mode proof；mutation action 还必须包含 action side-effect proof。
- API client/payload helper 测试不能关闭 route/component render proof。
- 若 Action-To-Route-To-Component 表缺失或与 issue 文件清单冲突，当前 UI issue 必须标 `blocked-pending-action-route-trace`，回流到 code archaeology / frontend contract；不得进入 atomic execution。

如果前端流程依赖 mock 数据验收，UI issue 不能只依赖 mock service fixture。必须引用 mock-drift verification，并证明真实页面消费的 mock response 与真实 API 外部契约一致。

如果 `verification-matrix` 产出了 Backend API Flow DAG，必须拆出独立 backend composition acceptance issue，或在 mock acceptance issue 中建立独立章节。不能让单接口 service/controller 测试声明 DAG 级用户流程完成。

Backend Composition Atomic Issue 必须包含：

- API Flow Graph 摘录：节点、入口、终态。
- Edge Contract Matrix 摘录：字段传递、前置状态、失败语义、时序/幂等。
- Path Coverage Matrix 摘录：覆盖哪些 happy path、branch、failure、terminal、state transition、retry/idempotency。
- State/Time Assertion Matrix 摘录：跨接口状态一致、终态停止、删除后行为、重复请求行为。
- Orthogonal Dimension Matrix 摘录：强耦合全组合，弱耦合 pairwise/representative，不可达组合 N/A。
- 测试文件/脚本路径和 expected result。

如果后端 issue 提供事件、进度、生命周期、状态机或自动调节决策契约，必须包含：

- `stateful_behavior` packet rows：operation、mode/variant、from/to state、trigger、guard、event/step、status、terminal、failure reason、producer、consumer、fixture、verification。
- Provider obligation 明确 downstream frontend/mock/API consumer 如何消费每个状态或事件。
- Verification 逐行说明哪些测试覆盖哪些 transition、terminal、failure 和 polling stop。

如果 issue 只写“Add mode-specific progress/change step graph”“Add tests for event graph”“Implement mock state graph”，没有具体矩阵行，当前 issue 必须回流到 `cross-module-contract-sdd` / `verification-matrix` / `task-planning`，不能进入 execution。

完成标准必须证明“用户场景 API 调用链路成立”，不能只证明每个接口单独通过。

### Backend Behavior Verification Gate

任何修改 Java/API/service/domain/persistence/runtime/provider 行为的后端 issue，packet 必须包含 `backend_behavior_verification`。编译、构建、checkstyle 只能作为 supporting proof，不能关闭行为任务。

每行至少写清：

- `behavior_id`：例如 `BE-T001-compat-old-k8s`、`BE-T002-explicit-unreachable-blocks`。
- `source`：对应 REQ/SCN/C/VER。
- `entrypoint`：Controller API、service method、manager method、task factory 或 executor 方法。
- `code_path`：被测真实生产路径，不能是替身逻辑。
- `input_or_fixture`：request、DB row、provider response、runtime state 或 fixture variant。
- `expected_state_or_output`：typed error、warning、persisted field、event、progress、response body 或 state transition。
- `failure_or_edge`：负向/边界分支；不适用必须写 N/A 原因。
- `command`：fresh unit/integration/API/runtime test command，不得是 compile-only。
- `assertion`：具体断言对象。
- `proves`：证明哪个 contract/source 行为成立。

后端 issue 禁止用 browser/DOM/render proof 作为自身完成证据；UI proof 属于 frontend/mock acceptance issue。反过来，后端 provider selector/API task 必须证明 typed validation、warning/blocking、fixture/API response、service/runtime state，而不是证明页面没有 raw text。

### Local Audit Gate: Task Decomposition Audit

Step 2 初版任务拆分完成后，主 agent 必须本地二次审计任务是否按层、primary module 和验证闭环拆分。

输出：

```markdown
### Task Decomposition Local Audit Report

| Candidate task | Auditor finding | Layer/module violation | Missing verification issue | Required rewrite | Blocks issue writing |
|---|---|---|---|---|---:|
```

阻塞条件：

- 单个 issue 跨层、跨 primary module 或跨多个 provided contracts。
- frontend action 没有 route/render/side-effect verification。
- derived config 的字段来源、UI payload、后端推导和拟真验证混在一个任务。
- runtime lifecycle 被“支持新模式”大任务吞掉。
- mock acceptance / repo-specific acceptance runtime 只作为测试附属物，没有 owner issue。

如果涉及前端调用后端 API，必须额外拆出 API route contract verification：

- 后端 Controller/OpenAPI 路径测试独立成任务，覆盖最终 method/path/query/body。
- 前端 API client 任务必须引用同一个最终 URL 契约，不得重新拼自然语言 API 名称。
- 带 `:action` 的路径必须有 404 防回归测试，例如证明 `/templates:match` 命中而不是只支持 `/templates/:match`。
- 需要登录的接口也必须能用未登录态 smoke 验证路由存在，预期为鉴权错误，不是 404。

### Frontend Action-Flow 拆分规则

如果一个前端任务提供用户可见 action，包括 create/update/delete/save/submit/scale/bind/import/export、wizard final submit、modal confirm、批量操作、mode switch 后提交，必须拆出或引用 action-flow verification。

拆分要求：

- 前端 API client/types：只负责 path、types、payload builder，不负责证明用户点击。
- 前端 UI/form：负责可见字段、active/inactive fields、validation scope、按钮 enabled/disabled、错误展示。
- Action-flow verification：负责真实 DOM/browser/mock acceptance 中的 `user action -> API/event -> feedback -> next state`。
- UI/form issue 的 Done Criteria 必须依赖 action-flow verification；如果 verification 单独后置，UI/form issue 只能是 `implemented-pending-action-flow`，不能 completed。
- 对 mode-specific 表单，Atomic Issue 必须复制 active fields、inactive fields、unregister/reset/defaultValue、hidden field submit participation。
- 对 wizard，Atomic Issue 必须复制每一步 Next validation 和最终 Submit validation 的区别。
- 对 async selector，Atomic Issue 必须复制 options loaded/empty/error/parent-change-reset 行为。

### Selector / Derived Configuration UI 规则

如果需求包含“参考 Instance 创建体验”“selector/default/auto-create”“从已有资源派生配置”“普通用户不填 raw ID”这类语义，不能压缩成 “use selectors”。必须拆出并在 packet `semantic_carriers` 中逐项携带：

- 资源对象清单：例如 VPC、Subnet、SecurityGroup、IAM Role/Profile、InstanceType、AMI、LaunchTemplate 等；按实际需求裁剪，不得用 “etc.” 代替。
- 每个对象的 UI 表达：selector、default derived value、auto-create、select-existing、read-only resolved display、warning/error state。
- 父子关系和重置规则：例如 subnet 属于 VPC，VPC 变化后 subnet/SG 选项如何 reset。
- raw text 禁止边界：哪些 raw ID 不能作为普通用户主路径；是否存在高级/只读/debug 例外也要锁定。
- 后端推导和校验分界：UI 选择什么，后端 derive/resolve 什么，缺失/不可达/权限不足如何返回 field error。
- explicit failure 与 unknown 的区别：明确不可达是否阻断，未知可达性是否 warning 并允许提交。
- 创建预览/detail/progress 中的 resolved resource 展示义务。
- mock/provider fixture 义务：候选列表、空列表、权限错误、wrong parent、invalid rule、unknown state、auto-create resolved result。

涉及此类语义时，通常至少需要三个 issue 消费同一 carrier：provider/mock 或 adapter issue 提供候选和校验状态，service/API issue 消费并校验，frontend issue 消费并渲染。缺任一 issue 或 verification 映射，任务规划 blocked。

不合格信号：

- Txxx 标题或范围是“实现前端 UX / 完善 UI / 支持创建页”，但没有 `frontend_user_task` 和 `action_route_component`。
- Txxx 修改 `.tsx/.jsx`、`pages/`、`components/`、`routes/`、`app/`，但没有 `form_state_matrix`、`mode_negative_assertions`、`fixture_needs`、`browser_verification`。
- Txxx 把更新页、容量页、详情页、进度页、创建页塞进一个大任务，导致用户动作闭包无法逐个验收。
- Txxx 只写“build pass / UI compiles / no old mode labels”，却声明 create/update/delete flow 完成。
- Txxx 只验证 service fixture 或 API client payload，却声明真实前端请求完成。
- Txxx 写了某个用户 action 的需求，但没有复制 action -> route -> router -> landing component 链路。
- Txxx 把 “VPC/Subnet/SG/IAM/InstanceType 通过 selector/default/auto-create，不做 raw text 主路径” 压缩成 “ASG must use provider selectors”。
- Txxx 的 mock acceptance / repo-specific acceptance runtime 只说 “populate provider selectors”，没有列出 selector 对象、response shape、fixture 状态、错误分支和 drift guard。
- Txxx 的 `Files To Change` 指向的页面与 Action-To-Route-To-Component 的 landing component 不一致。
- Txxx 只测 payload builder，却没有验证 action 落点页面的 mode-specific render/negative old-mode leakage。
- Txxx 没有说明隐藏字段是否还参与校验。
- Txxx 没有说明 click submit 成功后跳转哪里、失败在哪里展示。
- Txxx 的 `action_route_component` 只包含 create submit，却标题声称包含 detail/resize/progress/events。
- Txxx 的 `Files To Change` 没有包含 action dropdown source component，例如详情页菜单组件，却声称修改对应 action route。
- Txxx 的 `Files To Change` 没有通过 allowlist feasibility：执行语义要求的层不存在于文件范围中，导致 worker 只能用绕路实现或临场扩 scope。
- Txxx 把详情页配置 tab 和详情页 action dropdown 混成一个 “detail page” 描述，没有分别列 source/landing/verification。
- Txxx 的 verification log 中 browser flow 是 `not_run/deferred`，但 task 仍被写成 passed。

### Derived Configuration 拆分规则

如果存在“前端不传字段，后端从已有资源推导配置”：

- 后端字段来源、缺失字段错误、自动创建/补选逻辑必须先成为独立任务。
- 前端隐藏字段或提交空 payload 必须后置，且引用 locked Derived Configuration contract。
- 真实/拟真源对象 fixture 和缺字段测试必须独立成验证任务。
- 不得把“UI 简化”和“后端推导兜底”放进同一个原子任务。

### Runtime Lifecycle 拆分规则

如果需求涉及云资源、异步任务、创建后操作、observability 或运行时自动调节能力，创建、更新、删除、指标和自动调节必须拆成可独立验证的任务，不能被一个“支持新部署模式”任务吞掉。

拆分要求：

- create、update deployment config、delete、failure/retry、metrics/logs、auto-adjust controller/load verification 分别成任务或明确 N/A。
- 删除任务必须包含资源 ownership/tag、清理调用、幂等、部分失败状态和残留资源表达。
- 修改部署配置任务必须拆开后端 API/task 与前端 mode-specific 页面；不得默认复用旧 mode 页面。
- Metrics 任务必须覆盖 runtime 暴露/采集配置/API 查询/UI 展示中本任务负责的一层，并引用 Observability contract。
- 自动调节任务必须至少拆为配置/控制器实现和压力触发验证；只做配置写入不能关闭自动调节验收。
- 每个创建后任务的 Verification 必须说明它不能由 create smoke 替代。

### Step 2.5: 决策一致性与回流门禁

拆分任务前必须检查：

- Decision Registry 中每个 active locked 决策都有稳定 `Decision key`。
- Decision Consistency Matrix 中不存在同一 Decision key 的冲突 active locked 结论。
- 如果某个 DEC/C/VER/T 已被 supersede，Backflow Invalidation Matrix 已列出失效范围。
- 没有 active Atomic Issue 或待生成任务引用 superseded DEC/C/VER。
- 任何新增任务边界决策都写入 `task-planning-decisions.md`，并同步 Decision Registry。

如果发现冲突或 supersession 缺失，先更新 Decision Registry / Backflow Invalidation Matrix，再重新生成覆盖表和 Task DAG。

### Step 3: 写任务索引

`tasks.md` 必须是 sealed 任务索引、依赖顺序和初始状态，不承载完整任务上下文，也不承载执行日志或最终 passed 状态：

```markdown
| Task | Issue | Sources | Layer | Files/modules | Verification | Initial status |
|---|---|---|---|---|---|---|
| T001 | `atomic-issues/T001.md` | REQ-001,C-001 | backend-service | `...` | `mvn ...` | pending |
```

任务规划完成并 pass-stage 后，`tasks.md` 是 sealed planning artifact。执行阶段不得把 verification result、Atomic Execution Local Review、passed/done/completed 状态写入 `tasks.md`；这些必须写入 `task-verification-log.yaml` / `execution-state.yaml`，task-local semantic review 写入 `task-semantic-review.yaml`，mock acceptance / repo-specific acceptance runtime row-level evidence 写入 `mock-acceptance-execution.yaml`，并由 `workflowctl.py pass-task Txxx` 写入 `workflow-state.yaml.task_receipts`。

如果必须兼容 checklist 格式，也必须在每行包含 issue 链接：

```markdown
- [ ] T001 [REQ-001,C-001] `atomic-issues/T001.md` - short title.
```

### Step 3.5: 写 Atomic Issues

对 `tasks.md` 中每个任务创建 `atomic-issues/Txxx.md`。

必须从 `ai-dev-methodology/templates/atomic-issue.md` 复制结构，不得自由省略章节。

在写 issue 前必须先建立覆盖表；缺任一表不得进入 `atomic-execution-sdd`：

```markdown
### Frontend Action Route Coverage

| Action ID | Source component | Final route/API | Router definition | Landing component/file | Owning issue | Render proof | Side-effect proof | Negative inherited-mode proof | Status |
|---|---|---|---|---|---|---|---|---|---|

### Semantic Consumption Matrix - Atomic Task Planning

| Upstream object | Required by task planning? | How consumed | Derived object | Copied semantics | Semantic carriers assigned | Dropped semantics | Drop reason / decision | Verification / gate | Status |
|---|---:|---|---|---|---|---|---|---|---|

### Module-to-Issue Map

| Module | Responsibility | Provided contracts | Consumed contracts | Atomic Issues | Boundary validation |
|---|---|---|---|---|---|

### Contract Closure Coverage

| Contract | Provider module | Provider issue | Consumer module(s) | Consumer issue(s) | Composition verification | Excerpt copied into issues? |
|---|---|---|---|---|---|---:|

### Contract Materialization Coverage

| Contract | Provider facts copied? | Consumer facts copied? | Preconditions copied? | Obligations copied? | Forbidden interpretations copied? | Atomic Issue section(s) | Status |
|---|---:|---:|---:|---:|---:|---|---|

### Requirement Composition Coverage

| REQ/SCN | Module composition path | Provided contracts proving it | Verification | Atomic Issue(s) carrying proof |
|---|---|---|---|---|
```

并必须建立 `Task DAG`；缺失或无法拓扑排序时不得进入执行：

```markdown
### Task DAG

#### DAG Nodes

| Task | Primary module | Layer | Provides contracts | Consumes contracts | Files owned | Verification gate | Status |
|---|---|---|---|---|---|---|---|

#### DAG Edges

| From task | To task | Dependency type | Reason | Can parallel? | Failure propagation if skipped |
|---|---|---|---|---:|---|

#### Topological Execution Order

| Order | Task | Why now | Blocked by | Unlocks |
|---:|---|---|---|---|

#### Parallel Groups

| Group | Tasks | Disjoint files? | Disjoint contracts? | Shared verification? | Risk |
|---|---|---:|---:|---:|---|
```

这些表不是汇报材料，而是任务生成算法：

- Frontend Action Route Coverage 决定每个用户 action 的真实落点文件、owner issue 和验证 issue；涉及前端 action 时缺失该表不得进入执行。
- Module-to-Issue Map 决定每个 issue 的 primary module。
- Semantic Consumption Matrix 决定每个 REQ/SCN/PDEC/DEC/C/MIG/VER 是否被 issue 消费或阻塞。
- `Semantic carriers assigned` 决定每个密集语义载荷进入哪些 Txxx packet；没有 carrier 分配的 dense requirement 不得生成 issue。
- Contract Closure Coverage 决定 provider issue、consumer issue 和验证 issue。
- Contract Materialization Coverage 决定每条契约的 provider facts、consumer facts、preconditions、obligations、forbidden interpretations 是否已经进入 Atomic Issue 正文。
- Requirement Composition Coverage 决定哪些验证必须作为组合级 proof 进入 issue。
- Backend API Flow DAG 决定哪些多接口用户场景必须生成 composition acceptance issue。
- `existing-object-action-consumer-graph.md` 决定旧 object/action consumer assumption 是否需要被新变体继承、替换或 locked N/A。
- `variant-impact-matrix.md` 中每个 `Must new variant satisfy?=yes` 行必须生成 provider task、consumer task 或 proof-only row；不能只进入 Source Context。
- `progress-change-producer-chain-matrix.md` 决定 progress/change producer task、readback verification 和 frontend progress consumer 的 DAG 边。它必须进入 owner packet 的 `provided_contract_obligations`、`consumed_contract_snapshots` 或 `backend_behavior_verification`。
- `external-side-effect-contract-matrix.md` 决定外部副作用 owner task、no-cloud/playground 替代边界、最低 production proof 和 failure/readback proof。它必须进入 owner packet 的 `external_side_effects`，不能只写在 contract excerpt。
- `runtime-materialization-parity.md` 决定 runtime mode change classification、产品能力 baseline、runtime artifact/config/plugin/secret/bootstrap/entrypoint/readback 映射和 resource-exists-only 负向断言。它必须进入 owner packet 的 runtime materialization 执行段，不能只写在 semantic carrier 或 contract excerpt。
- `runtime-test-topology-matrix.md` 决定 proof owner 文件、fixture/support 文件、freshness/build step 和验证命令。每个 `Must be in task-dag files?=yes` 或 `Must be in packet files_to_change?=yes` 的 proof file 必须自动进入对应 Txxx 的 allowlist；否则 task planning fail，不得留到执行期 recovery。
- Proof Owner Allowlist Matrix 决定 Verification Matrix 的 proof 文件是否已进入 task allowlist。缺失 proof file 是 task-planning gap，不是执行期补文件。
- Semantic Load Split Matrix 决定任务是否过载：一个 Txxx 同时包含多个 primary module、provider side effect owner、state/event/progress producer、readback consumer owner、跨模块 verification loop 时，默认拆分；只有同一 primary module、同一 semantic type、同一 operation/surface、同一短验证闭环全部成立时才允许合并。
- Task DAG 决定执行顺序、并行边界和错误不传播证明。
- 如果某个模块、契约或 REQ/SCN 无法映射到 issue，必须回流到设计/契约/验证阶段，不能生成“补一个任务看看”的实现 issue。
- 如果某个 required upstream object 在 Semantic Consumption Matrix 中没有 `Derived object=Txxx` 或 locked N/A，必须回流，不能进入执行。
- 如果某个用户 action 没有 owner issue、landing component、render proof 或 negative inherited-mode proof，必须回流到 frontend-contract-design / verification-matrix，不能进入执行。
- `frontend-route-component-matrix.md` 中每个 `UI-ACT-*` 必须被复制到 owner packet 的 `action_route_component`。owner packet 的 `files_to_change` 和 `task-dag.yaml.files` 必须包含该 action 的 source component、click handler/route builder、router definition、landing component/file。
- `frontend-mode-field-display-matrix.md` 中每个 surface 的 `Must show`、`Must hide`、`Assertion` 必须复制到 owner packet 的 `mode_field_display_matrix`。详情页配置 tab、操作下拉、update-config、resize、progress、events 不得只写成 “detail mode-specific rendering”。
- `frontend-form-state-matrix.md` 中每个 form/step 的 `Active fields`、`Inactive/hidden fields`、`Validation trigger`、`Submit participation` 必须复制到 owner packet 的 `form_state_matrix`。只在 Source Context 写“mode-specific form validation”不算消费。
- `frontend-mode-leakage-negative-matrix.md` 中每个 surface/action 的 `Forbidden DOM/text`、`Forbidden payload fields`、`Forbidden route/API`、`Assertion method` 必须复制到 owner packet 的 `mode_negative_assertions` 和 `browser_verification.negative_assertions`。只在 prohibited changes 或 semantic carrier 泛写“no K8s leakage”不算消费。
- `frontend-browser-verification-matrix.md` 中每个 `Action ID` 必须有 row-level browser/click/network/DOM/screenshot-or-trace proof。build/lint/typecheck/payload helper 不算 action-flow proof。
- 前端矩阵消费是 section-scoped：`workflowctl.py` 和 `validate_artifacts.py` 只认 owner packet 的专用字段，不做 full-packet text match。`Source Context`、`semantic_carriers`、source excerpt、implementation steps 或 verification summary 里出现同样文字，只能证明来源存在，不能证明该矩阵行已经进入执行契约。
- 如果浏览器 proof 因环境原因后置，必须指向具体 `mock-frontend-action-matrix.yaml` row 或 `mock-acceptance-cases.yaml` case id；没有 case id 的 “deferred to Txxx” 不允许让当前 frontend issue passed。

Task DAG 生成规则：

- provider issue 必须先于 consumer issue。
- schema/migration/cloud resource issue 必须先于依赖它的 service/API/UI issue。
- external side-effect provider issue 必须先于 service/readback/UI consumer issue；no-cloud/playground proof issue 不能替代 provider side-effect issue。
- progress/change producer issue 必须先于 frontend progress/change consumer issue；runtime side effect issue 若触发 change producer，必须通过 DAG 边连接到 producer issue，而不能只连接 endpoint/detail consumer。
- runtime proof owner issue 必须包含 proof file 和 required freshness/build step；跨模块测试依赖本地 SNAPSHOT 时，freshness step 必须成为 verification command 或 prerequisite command。
- verification gate 必须先于依赖它宣布完成的场景。
- 并行组必须同时满足文件不重叠、契约不依赖、共享验证不会互相污染。
- 任一 edge 的 Failure propagation 不能为“未知”；否则任务顺序未证明。

Atomic Issue 写作规则：

- 摘录必要上下文，不要只引用 ID。
- 将上游 PRD/AIP/考古/迁移/契约/验证中本任务必需的语义复制进 issue；全局文档只能作为 source of truth 链接，不承担执行语义。
- 先写 `atomic-issue-packets.yaml.semantic_carriers`，再写其他 packet 字段；把每个 carrier 复制到实际执行章节后再编译 Markdown。
- reviewer 必须能从单个 Txxx issue 看到 carrier 的完整执行含义，而不是需要回读 spec 才知道 “selectors” 包含哪些资源、状态和错误。
- 从 Module Contract Graph 生成 issue，而不是从自然语言任务列表生成 issue。
- 每个 issue 必须声明 primary module、consumed contracts、provided contracts。
- consumed contracts 是本 issue 可以假设成立的外部承诺；provided contracts 是本 issue 必须为其他模块实现或维护的承诺。
- 只包含完成当前任务需要的最小闭包，避免把完整 plan 粘进去。
- 每个 issue 的文件集合必须尽量单层、单模块。
- 跨模块一致性通过 Contract Excerpts 和 Verification 表达，不靠实现者记住全局设计。
- 如果写不出自包含 issue，说明任务边界不对或上游契约不完整，必须回到 `plan.md` / contracts / verification matrix。
- 每个 issue 写完后用 0/1/2 rubric 逐项评分；任何维度为 0 阻塞执行，任何维度为 1 必须补齐到 2，或有用户/明确 owner 本轮显式接受的风险记录。

### Local Audit Gate: Contract Materialization Audit

覆盖表和候选 Atomic Issue packet 写出后，主 agent 必须本地二次审计每个 issue 是否物化契约，而不是引用 ID。候选 packet 在本审计通过前不能被视为任务，也不能被下游执行阶段读取。

输出：

```markdown
### Contract Materialization Local Audit Report

| Issue | Auditor verdict | Missing copied context | Contract/materialization gap | Verification gap | Required rewrite | Blocks execution |
|---|---|---|---|---|---|---:|
```

阻塞条件：

- `atomic-task-decomposition.md` 缺失，或缺少 Contract Granularity Admission Matrix、Contract Edge Decomposition Matrix、Owner Legitimacy Matrix、Provider Consumer Task Decision Matrix、Task Merge Split Decision Matrix 任一矩阵。
- 任一 decomposed edge row 没有 provider obligation、consumer decision、merge/split decision 或 verification proof。
- 任一 `Contract Granularity Admission Matrix` 行为 `blocked-backflow`、`unknown`、`TODO`，或 missing detail 被留给 worker 判断。
- 任一 `Contract Executable Obligation Matrix` active row、`ESE-*`、`PCP-*`、`RMM-*` 等专用 row 没有进入 `atomic-planning-context-pack.md`、`atomic-task-decomposition.md`、`task-dag.yaml` 和 `atomic-issue-packets.yaml` 的具体 owner 映射。
- 只用粗 `C-xxx` 代替 `C-xxx-OBL-yyy` / 专用 row ID，导致 autoscaling policy create、HPA prune、runtime parity、ownership cleanup/protect、failure consistency 这类 obligation 无法定位到唯一 owner。
- consumed/provided contract 只有 ID、标题或一句总结。
- `semantic_carriers` 缺失、泛化、没有复制到 packet 执行章节，或 carrier 没有覆盖上游 dense semantics。
- execution precondition 只有任务号，没有已成立事实。
- provided obligation 没有 downstream consumer 或 observable output。
- forbidden interpretation、preconditions failure handling 缺失。
- frontend action route、mock drift、runtime lifecycle 或 composition verification 未复制进相关 issue。

### Step 3.6: Atomic Issue Rubric Gate

对每个 `atomic-issues/Txxx.md` 写入本地审计结果，或在独立 planning audit artifact 中汇总；不得把执行期审计结果写入 sealed `tasks.md`：

| 维度 | 必须达到 2 分的判定 |
|---|---|
| Goal | 说明本任务产出、价值和对应 source |
| Module Contract Closure | primary module、consumed contracts、provided contracts、内部不变量明确 |
| Scope | In scope / Out of scope 都具体，阻止扩张 |
| Source Context | 复制必要语义，包含行为、边界、错误或状态 |
| Locked Decisions | 复制具体决策和本任务影响，不只列 ID |
| Contract Excerpts | Trigger/Normal/Failure/Consistency/Timing/Verification 完整 |
| Code References | 具体文件/类/方法/页面/测试以及要遵循什么 |
| Files To Change | 可定位路径；新文件有包路径、命名规则和原因 |
| Implementation Steps | 文件级顺序步骤，不要求 worker 重新拆方案 |
| Verification | 命令/步骤、expected result、proves、失败含义齐全 |
| Prohibited Changes | 任务特定的禁止事项，不只是通用三条 |
| Done Criteria | 可检查，和 verification/source 对齐 |

任何 0 分阻塞 `atomic-execution-sdd`。任何 1 分必须修到 2 分；若因环境限制不能修，必须在 planning artifact 的 Not Run/Risk 表记录风险，并由用户或明确 owner 在本轮显式接受。

### Local Audit Gate: Atomic Issue Independent Rubric Audit

Step 3.6 完成后、进入结构校验或执行前，主 agent 必须按模块/issue group 做本地二次复核 Atomic Issues，并输出 pass/block/risk/backflow-candidate。

输出：

```markdown
### Atomic Issue Local Audit Report

| Issue | Auditor score/verdict | Worker would need new decision? | Missing self-contained context | Verification expected-result gap | Required rewrite | Blocks execution |
|---|---|---|---|---|---|---:|
```

阻塞条件：

- 任一 required rubric 维度 0 分。
- 1 分风险未被明确批准或未修成 2 分。
- issue 不能独立派发。
- verification 无 expected result、proves 或 failure meaning。
- issue 的 Files To Change 与 Action Route Coverage / Module-to-Issue Map 冲突。

### Step 4: 依赖与并行

标记 `[P]` 只在满足以下条件时使用：

- 文件集合不重叠。
- 没有前后置数据依赖。
- 失败不会影响另一个任务输入。

### Step 5: 验证命令

在 `tasks.md` 和每个 Atomic Issue 中预先写入：

- 编译命令
- 单测命令
- lint/typecheck
- 前端构建/浏览器验证
- Helm/Terraform render/plan
- 集成/E2E/手动验证

未能预定义验证的任务不能进入实现，除非明确标记风险并获得用户确认。

验证命令必须来自 `verification-matrix` 或显式回写到其中；不能在 tasks 中凭空新增一套不一致的验证口径。

Atomic Issue 的 Verification 必须写 expected result。对 API route、UI、DB、Terraform、cloud-runtime 等验证，必须写明“什么结果证明行为成立”，不能只写命令。

## 输出

更新或创建 `specs/changes/<change-id>/tasks.md`：

- Sources
- Atomic Planning Context Pack 链接和摘要
- Execution Rules
- Pre-Implementation Check
- Task List
- Parallel Work
- Verification Commands
- Verification Log 空表只允许出现在 `task-verification-log.yaml` / `execution-state.yaml` 模板中，不得作为 execution log 写入 sealed `tasks.md`
- Not Run 空表，包含 Source、Severity、Owner/approval、Blocks done
- Decision Gaps 空表
- Task DAG
- Backflow Invalidation Matrix 链接或摘要，如存在回流/失效
- Current Sync 判断
- Handoff Notes

并创建：

- `specs/changes/<change-id>/atomic-planning-context-pack.md`
- `specs/changes/<change-id>/atomic-task-decomposition.md`
- `specs/changes/<change-id>/atomic-issue-packets.yaml`
- `specs/changes/<change-id>/atomic-issues/Txxx.md`

如任务数量很多，可以增加 `atomic-issues/README.md` 作为索引，但 `tasks.md` 仍必须链接每个 issue。

### Step 6: 结构校验

每完成一批语义闭环 packet 并编译对应 Markdown 后，运行：

```bash
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/atomic_issue_compile.py specs/changes/<change-id> --check
```

```bash
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py validate pre-execution specs/changes/<change-id>
```

再运行：

```bash
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/validate_artifacts.py specs/changes/<change-id>
```

上述 planning 校验通过后，进入 pre-execution 前必须完成同步只读 subagent quality review，并写入：

```text
specs/changes/<change-id>/atomic-issue-quality-review.yaml
```

启动 reviewer 的 prompt 必须显式携带方法论 Atomic Boundary 原文五条定义，并说明 `primary_closure/action-flow/stateful operation/provided contract/verification loop` 只是拆分辅助证据；不得只写“check atomicity”。等待 reviewer 时单次超时时间必须至少 30 分钟；30 分钟内未返回不得改用 `main-local` pass。reviewer 输出的每个 Txxx row 必须说明五条定义是否成立，证据必须引用具体 artifact path 和 section。

review 通过后重新运行：

```bash
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/validate_artifacts.py --stage task-planning specs/changes/<change-id>
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py validate task-planning specs/changes/<change-id>
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py validate pre-execution specs/changes/<change-id>
```

任一校验失败不得进入 `atomic-execution-sdd`，也不得执行任何已局部通过的 Txxx。若怀疑校验脚本误报，只有用户或明确 owner 在本轮显式批准后才能记录为 risk-accepted；agent 不得自判误报并继续。误报批准不能绕过 `workflowctl.py validate pre-execution`，也不能允许在 gate 失败时修改 `specs/changes/<change-id>` 之外的文件。

`workflowctl.py`、`validate_artifacts.py` 和 `atomic_issue_compile.py` 必须从 `/Users/keqing/.codex/skills/...` 的绝对路径运行。目标仓库没有这些脚本、脚本输出很长、validator 严格、修复成本高，均不是降级理由。工具绝对路径不可用时，本阶段只能 `blocked` 并报告 skill runtime 工具缺失；不得用 checklist 自审、关键词自审或人工口头确认替代。

没有上述三类校验成功结果，且没有 `workflowctl.py begin-execution` 生成的 `execution_receipt` 时，不得写出或口头宣称 `pre-execution complete`、`ready for execution`、`准备开始 T001`、`进入 T001`、`可以开始改代码`。`tasks.md`、`atomic-issues/Txxx.md`、局部 packet 或编译同步都不是执行许可。

校验失败期间只允许修改 `specs/changes/<change-id>` 下的 artifact。不得新建或修改业务代码、mock 代码、SQL、前端文件或测试文件；如果已经出现非 specs 改动，必须先把当前阶段标为 `blocked`，记录 backflow，再回到最早缺失阶段修 artifact。

校验通过不代表语义合格；还必须完成 Step 3.6 的 rubric gate。脚本和 rubric 任一不通过，都不得进入执行。

结构校验还必须人工或脚本等价检查 `atomic-planning-context-pack.md`：

- 每个 required upstream object 都在 Context Pack 中有 executable semantics。
- 每个生成的 Txxx 都能追溯到 Context Pack 的 source/decision/contract/verification 行。
- 每个 Txxx 都有 `atomic-issue-packets.yaml` packet，且 `atomic-issues/Txxx.md` 与 packet 编译结果一致。
- 任一 Atomic Issue 中出现的新语义，如果不在 Context Pack 或 canonical artifact 中，必须回流补 Context Pack 和源 artifact。

### Local Audit Gate: Execution Readiness Audit

结构校验、rubric、coverage、Task DAG 全部完成后，主 agent 必须做最终 execution readiness 本地审计。

输出：

```markdown
### Execution Readiness Local Audit Report

| Gate | Auditor finding | Evidence | Required backflow | Blocks atomic-execution-sdd |
|---|---|---|---|---:|
```

阻塞条件：

- `validate_artifacts.py` 失败且无用户或明确 owner 的本轮显式 risk-accepted 记录；该记录仍不能绕过 `workflowctl.py validate pre-execution`。
- Task DAG 不可拓扑排序，或 verification gate 后置但依赖任务已标 completed。
- Blocks done Not Run 被标完成。
- Backflow Invalidation Matrix 中有 active issue 引用 superseded DEC/C/VER。
- 任一本地审计报告的 blocker 未关闭。

## 退出检查

- [ ] 所有 REQ/SCN/SC 有任务覆盖，或明确 N/A。
- [ ] 每个任务有 source reference。
- [ ] 主 agent 已重新读取 canonical artifacts 并生成 `atomic-planning-context-pack.md`；任务生成不依赖聊天历史或压缩摘要。
- [ ] Context Pack 的 Source Rehydration Ledger 覆盖所有 required canonical artifacts，未读项均有 locked N/A 或 blocker。
- [ ] Context Pack 的 Upstream Semantic Index 覆盖所有 REQ/SCN/PDEC/DEC/C/MIG/VER，且 copied semantics 不是 ID/标题/一句摘要。
- [ ] 已生成 `atomic-task-decomposition.md`，并包含 Contract Granularity Admission Matrix、Contract Edge Decomposition Matrix、Owner Legitimacy Matrix、Provider Consumer Task Decision Matrix 和 Task Merge Split Decision Matrix。
- [ ] `Contract Executable Obligation Matrix` 中每个 active `Sub-obligation ID` 均已映射到 decomposed edge row、provider/consumer decision、merge/split decision、`task-dag.yaml` task 和 owner packet；只写粗 `C-xxx` 不算通过。
- [ ] Owner Legitimacy Matrix 中每个 provider guarantee row 的 proposed provider task primary module 与 canonical owner module 一致；API/DTO/request carrier/proof/fixture 行只使用 carrier_order_edge、verification_prerequisite_edge 或 proof_only_edge，不进入 semantic `provides`。
- [ ] Task Merge Split Decision Matrix 的每个 merge row 都先通过 Owner Legitimacy Matrix；没有用合并来修复 owner 不一致，也没有让同一个 provider obligation 同时归属多个 Txxx。
- [ ] 若存在 `existing-object-action-consumer-graph.md`、`variant-impact-matrix.md` 或 `progress-change-producer-chain-matrix.md`，已被 `atomic-planning-context-pack.md` 消费，并映射到 decomposed edge、Txxx、verification 和 task DAG edge。
- [ ] 若存在 `external-side-effect-contract-matrix.md`，已被 `atomic-planning-context-pack.md` 消费，并映射到 owner packet 的 `external_side_effects`、provider task、readback/consumer proof 和 task DAG edge。
- [ ] 若存在 `runtime-materialization-parity.md`，已被 `atomic-planning-context-pack.md` 消费，并映射到 owner packet 的 runtime materialization 执行段、provider/consumer task、readback proof 和 task DAG edge。
- [ ] 若存在 `runtime-test-topology-matrix.md`，每个 proof owner 文件已进入 owner Txxx 的 packet `files_to_change` 和 `task-dag.yaml.files`，freshness/build step 已进入 verification command 或 prerequisite。
- [ ] `atomic-task-decomposition.md` 中每个 Txxx 都能追溯到 decomposed contract edge / semantic type / operation-surface / provider-consumer decision / merge-split decision，且无 blocked-backflow、unknown、TODO 或待确认行。
- [ ] `atomic-task-decomposition.md` 包含 Proof Owner Allowlist Matrix 和 Semantic Load Split Matrix；没有 split-required 但无 backflow/拆分的行，也没有 “same module/page/related work” 这类弱合并理由。
- [ ] 每个 Txxx 都能追溯到 Context Pack 中的 source、decision、contract 和 verification 行。
- [ ] 已生成 `atomic-issue-packets.yaml`；每个 Txxx 的 packet 都包含 sources、decisions、contract excerpts、execution preconditions、consumed snapshots、provided obligations、invariants、verification 和 failure backflow。
- [ ] 已运行 `atomic_issue_compile.py specs/changes/<change-id>`；`atomic-issues/Txxx.md` 由 packet 编译生成，未手工绕过。
- [ ] 已运行 `atomic_issue_compile.py specs/changes/<change-id> --check`，确认 packet 与 Markdown 同步。
- [ ] 已完成同步只读 reviewer 的 `atomic-issue-quality-review.yaml`；每个 Txxx 都有 review row，且无 validator-driven wording、Source Context self-requirement、错 owner proof、brief 关键词压缩或非原子 blocker。
- [ ] Source Intake Ledger 覆盖所有输入，没有 behavior-affecting unread/blocked source。
- [ ] Semantic Consumption Matrix 覆盖所有 REQ/SCN/PDEC/DEC/C/MIG/VER；required 对象都有 Txxx、locked N/A 或 blocker。
- [ ] 没有为了通过 validator 静默收窄 task source；任何 dropped source/object 都有 locked N/A/drop decision、原因和替代 owner。
- [ ] Verification Feasibility Gate 已进入任务规划；required verification 的环境/fixture/setup owner 已复制到 tasks/issue。
- [ ] 涉及多仓/版本时 Version Branch Alignment Matrix 已通过。
- [ ] Artifact Rubric Scorecard 无 0 分；1 分已修复到 2 分，或有用户/明确 owner 本轮显式接受的风险记录。
- [ ] 已完成适用的本地审计报告：Planning Input、Task Decomposition、Contract Materialization、Atomic Issue Rubric、Execution Readiness；无阻塞项。
- [ ] 每个任务引用相关 locked decision，或明确 N/A。
- [ ] Decision Consistency Matrix 没有 active conflict。
- [ ] 没有 active task/issue 引用 superseded DEC/C/VER；如发生回流，Backflow Invalidation Matrix 已更新。
- [ ] 每个任务绑定一个 primary module，或明确为纯 verification issue。
- [ ] 每个任务列出 consumed contracts 和 provided contracts。
- [ ] Contract Materialization Coverage 覆盖每条 locked contract，且没有 `copied?=no`、`Status=blocked`、unknown 或待确认行。
- [ ] 每个非纯文档 Atomic Issue 已物化契约：Execution Preconditions、Consumed Contract Snapshot、Provided Contract Obligation、Invariant Carryover、Preconditions Failure Handling 都存在且有事实内容。
- [ ] 没有 Atomic Issue 把 consumed/provided contract 写成 ID、标题、链接或一句总结；provider guarantee、consumer assumption、字段/状态/错误/时序、下游 observable output 已复制到 issue 本体。
- [ ] 每个 Atomic Issue 写明前提不成立时的停止和回流路径；不得让 worker 在执行阶段临时补猜、修上游或重定契约。
- [ ] 没有任务在实现阶段重新定义模块边界或跨模块契约。
- [ ] 每个任务有具体 repo/file/module path。
- [ ] 每个任务有 `atomic-issues/Txxx.md`。
- [ ] 每个 Atomic Issue 摘录了必要 source/decision/contract 语义，而不是只引用 ID。
- [ ] 每个 Atomic Issue 不读完整 `proposal/spec/plan` 也能独立执行。
- [ ] 每个 Atomic Issue 有明确 In scope / Out of scope。
- [ ] 每个 Atomic Issue 有 Existing Code References。
- [ ] 每个 Atomic Issue 的 Verification 有命令/步骤、expected result 和 proves。
- [ ] 每个后端行为 issue 都有 `backend_behavior_verification`，且不是 compile-only；每个 claimed contract/edge/state/error 至少有一条行为断言。
- [ ] 触碰 3 个以上后端细层的 issue 填写了 `backend_layer_boundary`，或已拆分；不得把 API/domain/persistence/runtime 混成一个默认原子任务。
- [ ] 后端 issue 没有用 browser/DOM/render proof 关闭自身完成；前端 proof 已由 frontend/mock acceptance owner 承担。
- [ ] 每个 Atomic Issue 有 Prohibited Changes。
- [ ] 没有任务包含未决决策。
- [ ] 每个任务有短闭环验证。
- [ ] 跨模块契约有对应实现任务和验证任务。
- [ ] 前端调用的 API 有独立 route contract verification 任务。
- [ ] 前端用户 action 有 Frontend Action Route Coverage，且每个 action 的 source component、route builder、router definition、landing component/file 和 owning issue 已锁定。
- [ ] 前端 UI issue 的 Files To Change 与 Frontend Action Route Coverage 的 landing component 一致；不存在“需求语义写 update page，但 issue 指向错误页面”的情况。
- [ ] 前端 mutation action 有独立 action-flow verification 或同任务 DOM/browser proof。
- [ ] 每个 mode-specific action 有 route/component render proof 和旧 mode 泄漏负向验证；payload builder/service fixture 未被用来替代页面落点验证。
- [ ] 前端 UI/form issue 的完成标准没有被 build/source inspection/service fixture 过早关闭。
- [ ] Wizard/form/mode-switch issue 复制了 active/inactive fields、validation scope、submit participation 和 success/failure feedback。
- [ ] 缺少 action-flow proof 的 UI issue 标记为 blocked / implemented-pending-action-flow，而不是 completed。
- [ ] 带 `:action` 或复杂 Controller 拼接的 API 有最终路径 404 防回归任务。
- [ ] Derived Configuration 任务已拆成字段来源、错误语义、UI payload、真实/拟真验证，不存在混合任务。
- [ ] Runtime Lifecycle 任务已拆成 create/update/delete/failure-retry/observability/auto-adjust 等独立闭环；创建 smoke 没有替代删除、指标或自动调节验证。
- [ ] 支持运行时自动调节能力时，已有独立压力触发验证任务或明确 Not Run risk。
- [ ] `Task DAG` 已列出 DAG Nodes、DAG Edges、Topological Execution Order、Parallel Groups，且 provider/consumer/verification 顺序成立。
- [ ] Verification Matrix 已覆盖所有任务验证。
- [ ] Not Run 表包含 Source、Severity、Owner/approval、Blocks done；P0/P1 或 `Blocks done=yes` 项阻塞 done，不得标为完成。
- [ ] `tasks.md` 可作为索引，`atomic-issues/Txxx.md` 可作为 `atomic-execution-sdd` 的任务主输入。
- [ ] 已满足 artifact-completeness-spec Stage 9 的 tasks index、Atomic Issue body、coverage map、source/decision/contract excerpts、verification expected result artifact 要求。
- [ ] `validate_artifacts.py` 通过；若存在误报批准，批准人必须是用户或明确 owner，且 `workflowctl.py validate pre-execution` 仍已通过。
