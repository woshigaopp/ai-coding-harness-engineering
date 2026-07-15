---
name: atomic-execution-sdd
description: SDD 对齐版原子执行。Use when implementing accepted AutoMQ specs/changes tasks by executing self-contained atomic-issues/Txxx.md indexed from sealed tasks.md, using proposal/spec/plan/contracts only to verify source of truth, performing per-task verification across backend/frontend/Terraform/Helm/cloud/observability, and recording execution only through workflowctl begin-execution/admit-task/validate-task-diff/pass-task receipts plus task-verification-log.yaml, task-semantic-review.yaml, and mock-acceptance-execution.yaml when applicable.
---

# Atomic Execution SDD

## 定位

这是 `atomic-execution` 的 SDD 对齐版。

职责只限于：**按 `tasks.md` 索引中的 Atomic Issue 执行并验证**。

理论前提：如果 `tasks.md` 中的所有 Atomic Issues 都是真正原子、自包含、模块内契约闭包完备的任务，那么按顺序执行它们后，大需求应自然完成。本阶段只验证这个前提是否成立并执行；不能把不完整 Atomic Issue 当作提示词自行补全。

实现阶段不得再做产品或架构决策。

执行或评审本阶段时，必须按 `ai-dev-methodology/references/artifact-completeness-spec.md` 的 “Stage 10: Atomic Execution” 检查正交维度、Required Artifacts、Completeness Criteria 和 Exit Gate。

执行前必须运行结构化 pre-execution gate 和 artifact gate。校验失败时先回到 `atomic-task-planning` 或最早缺失阶段修 artifact，不得靠执行阶段补语义。

```bash
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py validate pre-execution specs/changes/<change-id>
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/validate_artifacts.py specs/changes/<change-id>
```

这两个命令是进入实现前的 admission control，不是事后审计。任一失败时，不得读取 `atomic-issues/Txxx.md` 开始改代码，不得把 `tasks.md` 里的任务标为 Done，不得用手写 Markdown-only issue 继续执行。

这两个命令必须从 `/Users/keqing/.codex/skills/ai-dev-methodology/scripts/` 绝对路径运行。目标仓库没有 `workflowctl.py` / `validate_artifacts.py` 不是降级理由；脚本不可用、输出过长、规则严格或修复成本高时，只能 blocked/backflow，不能用 checklist 自审或主观判断替代。

两个 gate 都通过后，必须立即执行：

```bash
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py begin-execution specs/changes/<change-id>
```

`begin-execution` 会写入 `workflow-state.yaml.execution_receipt`，封存 pre-execution artifact hash、全量 sealed artifact hash、stage receipt hash 和当前 git state。没有这个 receipt，任何 `specs/changes/<change-id>` 之外的业务文件 diff 都是非法执行。

receipt hash 只封存 workflow artifact 和任务输出语义。`.DS_Store`、gitignored build/cache 文件、`target/`、`node_modules/`、`dist/`、`coverage/` 等系统噪音不会进入 sealed artifact hash，也不能被当作阶段产物、验证证据或任务 diff。

执行前 admission 还有一个文件系统约束：在两个命令都通过之前，git worktree 中不得存在 `specs/changes/<change-id>` 之外的新增、修改或暂存文件。若存在，说明已经过早进入实现，必须停止本阶段、回流修 artifact；不得继续在代码层扩大改动。

特别阻塞条件：

- 缺少 `workflow-state.yaml`、`semantic-objects.yaml`、`contracts.yaml`、`verification.yaml`、`task-dag.yaml`、`backflow.yaml` 或 `atomic-issue-packets.yaml`。
- `atomic-issues/Txxx.md` 不是由 `atomic_issue_compile.py` 从 `atomic-issue-packets.yaml` 编译生成，或 `--check` 不同步。
- `tasks.md` 只有自然语言摘要、没有结构化 DAG / packet / sidecar 对齐。
- `semantic_carriers` 没有从 `REQ/DEC/C/task-dag` 追踪到对应 Txxx packet。
- 任一 Atomic Issue 只有标题和一句描述，或缺 Execution Preconditions / Consumed Contract Snapshot / Provided Contract Obligation / Verification expected result。
- `workflow-state.yaml.stage_status` 使用 `completed` / `done`，或 `execution` 不是 `not_started` 但缺少 `execution_receipt`。
- `tasks.md` 出现 `Atomic Execution Log`、`Verification Result`、`Fresh command`、`passed/done/completed` 终态任务状态；执行日志只能写入 `task-verification-log.yaml` / `execution-state.yaml`，task-local semantic review 写入 `task-semantic-review.yaml`，mock/playground row evidence 写入 `mock-acceptance-execution.yaml`，task 通过只能由 `workflowctl.py pass-task` 签发。

当用户要求“继续推进”“直到做完”“中间不要中断”时，`validate_artifacts.py` 返回 `BLOCKED` 的默认动作是自动 backflow：更新 `Backflow Invalidation Matrix`，修复缺失 artifact / Atomic Issue / verification，再重跑校验。只有产品决策、权限/凭证、真实 runtime/cloud evidence 不可取得、或 PRD/AIP 冲突这类人类阻塞才停下来询问。

执行阶段只消费已经闭包的 Atomic Issues。若发现 source 未读、决策冲突、契约变化、Task DAG 错误、P0/P1 Not Run 或 superseded 引用，必须停止并回流；不能把这些问题当成实现细节处理。

候选 issue、部分通过的 packet、手写 Markdown、或只有 `atomic_issue_compile.py --check` 同步的产物都不是执行输入。pre-execution 是整个 change 的 admission gate，不允许“先执行已闭合的几个 Txxx”。

## 输入优先级

Primary input:

```text
specs/changes/<change-id>/atomic-issues/Txxx.md
```

`tasks.md` 只作为封存的任务索引、顺序和初始状态表。单个任务执行时，Atomic Issue 是唯一可执行任务说明。执行状态不得手写回 `tasks.md`；必须由 `workflow-state.yaml.task_receipts` 派生。

Supporting context:

- `source-intake-ledger.md`
- `proposal.md`
- `spec.md`
- `plan.md`
- `Semantic Consumption Matrix`
- Decision Registry
- Decision Consistency Matrix
- Task DAG
- Backflow Invalidation Matrix，如存在回流/失效记录
- Verification Matrix
- Verification Feasibility Gate
- Version Branch Alignment Matrix，如涉及多仓/版本
- Artifact Rubric Scorecard
- archaeology / contract / migration references linked from plan

Supporting context 只能用于核对 source of truth，不能用于补齐 Atomic Issue 缺失的必要语义。如果必须读完整 `plan.md` 才知道如何实现当前任务，则该 Atomic Issue 不合格，必须先回到 `atomic-task-planning` 修任务。

如果没有 `tasks.md` 或 `atomic-issues/Txxx.md`，先使用 `atomic-task-planning`，不得直接实现。

如果有 `tasks.md` 和 `atomic-issues/Txxx.md`，但没有结构化 sidecar 或 `atomic-issue-packets.yaml`，仍视为没有合格 Atomic Issues。必须先使用 `atomic-task-planning` 重建 packet、sidecar 和编译产物，不得执行已有 Markdown。

## 执行前检查

第一步固定执行：

```bash
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py validate pre-execution specs/changes/<change-id>
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/validate_artifacts.py specs/changes/<change-id>
```

只有两者都通过，才允许继续下面的人工检查和代码修改。

随后必须执行：

```bash
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py begin-execution specs/changes/<change-id>
```

`begin-execution` 成功前禁止读取 Txxx 开始实现，禁止创建业务代码文件。

读取 `tasks.md`，确认：

- [ ] `workflowctl.py validate pre-execution` 已通过；失败时已回流到 `atomic-task-planning`，没有继续执行。
- [ ] `validate_artifacts.py` 已通过。若存在误报批准，批准人必须是用户或明确 owner，且 `workflowctl.py validate pre-execution` 仍已通过；agent 自判误报不算通过。
- [ ] 运行 pre-execution gate 前没有 `specs/changes/<change-id>` 之外的 git 改动；如果有，已回流而不是继续实现。
- [ ] `atomic-issue-packets.yaml` 存在，每个 Txxx 有 packet，且 `atomic_issue_compile.py specs/changes/<change-id> --check` 通过。
- [ ] `workflow-state.yaml`、`semantic-objects.yaml`、`contracts.yaml`、`verification.yaml`、`task-dag.yaml`、`backflow.yaml` 存在并参与校验。
- [ ] `source-intake-ledger.md` 存在，且没有 behavior-affecting `unread` / `blocked` source。
- [ ] `Semantic Consumption Matrix` 存在，当前 task 消费的所有 upstream object 都已复制必要语义到 Atomic Issue；没有 required upstream object 处于 `blocked` 或无理由 dropped。
- [ ] Verification Feasibility Gate 中当前 task 的 required verification 可运行，或已记录阻塞 Not Run。
- [ ] Artifact Rubric Scorecard 对当前 Atomic Issue 无 0 分。
- [ ] Decision Consistency Matrix 没有 active conflict。
- [ ] `Task DAG` 存在，并包含 DAG Nodes、DAG Edges、Topological Execution Order、Parallel Groups。
- [ ] 当前要执行的 task 在 Task DAG 中没有未完成 provider/verification predecessor。
- [ ] 如存在 Backflow Invalidation Matrix，没有 active issue 引用 superseded DEC/C/VER/T；当前 task 未处于 `blocked` / `pending-rewrite` / `pending-rerun`。
- [ ] 所有 blocking open questions 已解决。
- [ ] 每个任务链接到 `atomic-issues/Txxx.md`。
- [ ] 每个 Atomic Issue 有 Goal、Scope、Source Context、Locked Decisions、Contract Excerpts、Existing Code References、Files To Change、Implementation Steps、Verification、Prohibited Changes、Done Criteria。
- [ ] 每个非纯文档 Atomic Issue 有 Execution Preconditions、Consumed Contract Snapshot、Provided Contract Obligation、Invariant Carryover、Preconditions Failure Handling。
- [ ] Atomic Issue 摘录了必要 source/decision/contract 语义，而不是只写 ID。
- [ ] Atomic Issue 中出现的每个 REQ/SCN/PDEC/DEC/C/MIG/VER ID 都有对应语义摘录；不得要求 worker 回读 PRD/plan。
- [ ] Consumed Contract Snapshot 写的是可执行事实，不是 contract ID 或一句总结。
- [ ] Provided Contract Obligation 写明 downstream consumer、observable output/state 和 verification proving it。
- [ ] Execution Preconditions 写明前置任务完成后已经成立的事实和证据，不只是 task ID。
- [ ] Preconditions Failure Handling 写明发现前提不成立时必须停止并回流，不能临场补猜。
- [ ] Atomic Issue 有具体 repo/file/module path。
- [ ] Atomic Issue 的验证有命令/步骤、expected result、proves，并能追溯到 Verification Matrix。
- [ ] 后端行为 issue 有 `Backend Behavior Verification Matrix` 或等价 packet 行；compile/build/checkstyle 只能作为 supporting proof，不能关闭 API/service/domain/persistence/runtime/provider 行为。
- [ ] 后端 issue 没有用 browser/DOM/render proof 作为自身完成证据；这类 proof 必须属于 frontend/mock acceptance issue。
- [ ] 触碰 3 个以上后端细层的 issue 有 `Backend Layer Boundary`，说明为何不能拆、禁止哪些跨层临场决策、验证边界在哪里。
- [ ] 需求级完成依赖的 Module Composition Verification 已进入当前 Atomic Issue 或独立验证 issue；不能只依赖模块内部单测。
- [ ] 涉及前端用户 action 时，当前 Atomic Issue 已复制 Action-To-Route-To-Component 事实：visible action/i18n key、source component、route builder、final route/API、router definition、landing component/file、mode branch、forbidden inherited UI/API。
- [ ] 涉及 mode-specific 前端 action 时，当前 Atomic Issue 的 Files To Change 包含真实 landing component/file，且 Verification 包含 route/component render proof 和旧 mode 泄漏负向验证。
- [ ] 涉及 `UI-ACT-*` 时，当前 Atomic Issue 的 `action_route_component` 已逐行复制所有 owner action；不能只实现 create submit 后声明 detail/resize/progress/events 完成。
- [ ] 涉及前端字段展示时，`frontend-mode-field-display-matrix.md` 的 owner 行已逐行复制到当前 Atomic Issue 的 `mode_field_display_matrix`；详情 tab、配置区、操作下拉、update-config、resize、progress、events 不能只在 Source Context 或 semantic_carriers 中出现。
- [ ] 涉及前端表单时，`frontend-form-state-matrix.md` 的 active fields、inactive/hidden fields、validation trigger、submit participation 已逐行复制到 `form_state_matrix`；隐藏字段是否参与校验不能由执行者临场推断。
- [ ] 涉及 mode 泄漏负向验证时，`frontend-mode-leakage-negative-matrix.md` 的 forbidden DOM/text、payload fields、route/API 和 assertion method 已进入 `mode_negative_assertions` 与 `browser_verification.negative_assertions`。
- [ ] 涉及浏览器验收时，`frontend-browser-verification-matrix.md` 的每个 Action ID 已进入 `browser_verification` 的 steps/network/DOM/screenshot-or-trace；Source Context、semantic_carriers 或 generic verification summary 不算消费成功。
- [ ] 涉及前端详情页操作下拉、行操作、tab action、update-config、resize、progress、events 时，Files To Change 包含真实 source component、handler/router 和 landing component/file。
- [ ] 前端 task 的 `browser_verification` 是必跑完成证据；build/lint/typecheck 只能作为 supporting proof。若浏览器 proof 因环境后置，必须有具体 mock frontend case id，且当前 UI issue 不能 pass。
- [ ] Atomic Issue 不要求执行者选择方案。
- [ ] Atomic Issue 可以直接作为 GitHub issue 独立派发。
- [ ] Atomic Issue 的正文是中文，代码/API/命令等标识除外。
- [ ] Atomic Issue 绑定一个 primary module，或明确为纯 verification issue。
- [ ] Atomic Issue 声明 consumed contracts，并且执行时可以假设这些契约成立。
- [ ] Atomic Issue 声明 provided contracts，并且本任务只实现/维护这些契约，不重新定义契约。
- [ ] Files To Change 中不存在不可定位的 “new helper under ...” 开放范围；若需要新文件，issue 已锁定包路径、命名规则和职责。
- [ ] Files To Change 通过 allowlist feasibility：API/VO/DTO、持久化/DO/mapper/migration、domain/service/entity、runtime/task/executor、frontend action source/handler/router/landing 等语义要求，都能在本 issue 的文件范围中找到对应真实落点。
- [ ] Implementation Steps 不包含“按需”“视情况”“选择合适方式”等实现阶段决策词，除非同时给出决策规则。
- [ ] 没有未锁定契约。
- [ ] 涉及云资源、部署模式或派生配置的任务，已有参考实现字段矩阵、Derived Configuration contract、representative fixture/runtime smoke。
- [ ] 涉及创建后操作、删除、observability 或运行时自动调节能力的任务，已有 Runtime Lifecycle contract、runtime-lifecycle/auto-adjust-load 验证和 expected result。
- [ ] `tasks.md` 的 Not Run 表没有 P0/P1 或 `Blocks done=yes` 的未批准阻塞项；存在时不得标需求完成。
- [ ] `tasks.md` 没有 execution log、Fresh command/result、Atomic Execution Local Review、passed/done/completed 终态任务状态。
- [ ] `workflow-state.yaml.execution_receipt` 只由 `workflowctl.py begin-execution` 生成；不存在倒签或手写 execution 状态。
- [ ] mock/backend、mock/frontend、packaged playground 或 event-state owner task 的 row-level 执行结果写入 mutable `mock-acceptance-execution.yaml`；sealed mock matrix/case 文件不承载 execution passed 状态。

不满足则先回流更新 `atomic-issue-packets.yaml`、`atomic-issues/Txxx.md`、`tasks.md`、`spec.md` 或 `plan.md`，重新 pass affected stage 和 `begin-execution`，不要写代码。

## 原子任务粒度

每个任务必须满足：

1. 零决策。
2. 单细层变更。
3. 上下文自包含。
4. 验证闭环短。
5. 错误不传播。

### 单细层示例

| Layer | 示例 |
|---|---|
| backend-data | DB migration、entity、repository |
| backend-domain | manager/service/domain logic |
| backend-api | controller、VO、permission、OpenAPI |
| backend-async-task | task steps、retry、state transition |
| frontend-api-client | API client、types、query hooks |
| frontend-page | page、tabs、forms、table |
| frontend-i18n | i18n keys and messages |
| terraform-provider | schema、CRUD、diff |
| deployment-helm | chart values/templates |
| cloud-resource | provider-managed compute group/IAM/RBAC/lifecycle scripts |
| observability | metrics/events/logs/alerts |
| test | unit/integration/e2e |
| docs | user docs/runbook |

跨细层任务必须拆分。

后端细层也必须拆分：backend-api、backend-domain、backend-data、backend-runtime、backend-observability 不能因为都在 Java 里就合并。若 Atomic Issue 已被批准为跨 3 层以上 exception，执行者只能按 `Backend Layer Boundary` 中锁定的 split decision 做机械实现；发现还需要选择字段名、错误码、事件名、事务边界或兼容策略时，必须回流，不得临场决定。

如果后端 Atomic Issue 没有 `Backend Behavior Verification Matrix`，或矩阵行没有具体 assertion，执行阶段必须停止并回流到 `atomic-task-planning`。不得通过“先实现，再补测试”来绕过该缺口。

## 执行循环

对每个任务：

1. 读取 sealed `tasks.md` 和 `task-dag.yaml` 只确认顺序，不手改状态。
2. 执行 `workflowctl.py admit-task Txxx specs/changes/<change-id>`。失败则回流，不得改代码。
3. 读取当前 `atomic-issues/Txxx.md`。
4. 只读取 Atomic Issue 中列出的代码文件和必要支持上下文，不扩大 scope。
5. 修改代码。
6. 运行该任务短闭环验证。
7. 把 fresh command/result 写入 `task-verification-log.yaml` 或 `execution-state.yaml`，不要写 `tasks.md`。mock/playground owner task 的逐行执行证据必须写入 `mock-acceptance-execution.yaml`，不要改 sealed `mock-backend-matrix.yaml`、`mock-frontend-action-matrix.yaml`、`mock-event-state-matrix.yaml` 或 `mock-acceptance-cases.yaml` 去标 passed。
8. 执行 `workflowctl.py validate-task-diff Txxx specs/changes/<change-id>`。失败表示 scope expansion，必须 backflow/reseal/re-admit。`admit-task` 会记录当时已有 changed path hash 作为本任务 diff baseline；前序已通过但未提交的任务 diff 不会污染当前任务，但当前任务修改任何 baseline 中的非 allowlist 文件仍会因 hash 变化而失败。
9. 执行 task-local semantic review，把结果写入 `task-semantic-review.yaml`。review 必须对照当前 `Txxx.md` 和当前 diff，检查 provided obligations、negative assertions、verification proof、diff scope 和测试断言是否真的满足 issue。先运行 `workflowctl.py review-hashes Txxx specs/changes/<change-id>` 取得当前 allowlist changed path hash 并写入 review；review 后如果继续改代码，必须重跑 review。
10. 执行 `workflowctl.py pass-task Txxx specs/changes/<change-id>`。成功后 task 才算 passed。`pass-task` 会拒绝缺失、阻塞、过期或未覆盖契约/验证的 semantic review。
11. 继续下一个任务。

如果执行中发现 Atomic Issue 缺少必要信息：

```text
Stop -> classify as atomic-issue-not-self-contained -> update Backflow Invalidation Matrix -> update Atomic Issue/source artifacts -> rerun affected verification -> continue
```

不得靠临场阅读完整全局文档自行补齐后继续实现。允许读取全局文档只为确认 source of truth；如果全局文档里的内容是执行必需语义，必须先复制回当前 Atomic Issue。

执行已经 `in_progress` 时，必须先判断回流类型；不得把所有问题都压成局部修补，也不得默认 clean worktree 重开。

**Local-reseal backflow** 适用于任务边界基本成立、只需修少量 DEC/C/VER/T 或 planning artifact 的情况。固定顺序：

1. 在 `backflow.yaml` 记录 `BF-xxx`、earliest missing stage、最小 invalidated DEC/C/VER/T，以及执行开始后被修改的 `invalidates.artifacts`。
2. 运行 `python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py backflow specs/changes/<change-id> BF-xxx`，让工具传播受影响对象。
3. 只修受影响的 contract / verification / task-planning artifact，不扩大到无关任务；修复后的 active DEC/C 必须重新达到 locked 状态，direct impacted T 必须离开 blocked/pending-rewrite，VER/T 必须回到可执行状态或明确 pending-rerun，`BF-xxx.status` 必须改为 `resolved` 或 `closed`。
4. 运行 `atomic_issue_compile.py` 和 `atomic_issue_compile.py --check`，再运行 task-planning/pre-execution 相关 validator。
5. 运行 `python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py reseal-execution-backflow specs/changes/<change-id> BF-xxx --reason "<reason>"`。
6. 从最早受影响任务重新 `admit-task`；受影响任务原有 receipt 已失效，必须重新实现/验证/review/pass。已有业务 diff 只有在属于本次 reseal invalidated 任务且落在该任务 allowlist 内时，才能进入新的 admission baseline；其他 diff 仍必须阻塞。

只有 workflow 工具本身无法 reseal、git 状态无法隔离、或用户明确要求恢复到干净分支时，才允许创建 clean recovery worktree。不得把 clean worktree 当作普通 backflow 路径。

**Task-regeneration backflow** 适用于任务拆分错误、canonical owner 错误、contract edge/operation 粒度错误、Atomic Issue 不自包含、需要新增/删除/合并/拆分 Txxx，或 Task DAG 拓扑需要重建的情况。此时必须回到 `atomic-task-planning` 或更早阶段重新生成受影响 Atomic Issues；如果影响面跨多个核心 contract、多个 primary module 或 DAG 拓扑，允许重新生成整批 task-planning artifacts。执行要求：

1. 在 `backflow.yaml` 记录 `BF-xxx`、失效 DEC/C/VER/T、失效 task-planning artifacts 和 supersession。
2. 运行 `workflowctl.py backflow` 计算 direct/downstream task 和 verification 影响。
3. 重建受影响的 `task-dag.yaml`、`atomic-issue-packets.yaml`、`atomic-issues/`、`atomic-task-decomposition.md`、`atomic-issue-quality-review.yaml` 和必要上游 artifact。
4. 重跑 `atomic_issue_compile.py`、`atomic_issue_compile.py --check`、`validate_artifacts.py --stage task-planning/pre-execution`、`workflowctl.py validate task-planning/pre-execution` 和 Atomic Issue quality review。
5. 若仍在同一 `execution=in_progress` change-dir 内恢复，修复完成后按 local reseal 规则运行 `reseal-execution-backflow` 并从最早受影响任务重新 `admit-task`；若工具无法合法 reseal 或用户要求干净恢复，才使用 clean recovery worktree。

如果执行中发现契约没有被物化，例如 consumed contract 只有 ID、provided contract 没有 downstream consumer、执行前提只有前置任务名、或没有写前提失败处理：

```text
Stop -> classify as contract-materialization-gap -> update Backflow Invalidation Matrix -> return to atomic-task-planning -> materialize contract snapshot/obligation/preconditions -> rerun affected planning/verification gates -> continue only after issue is sealed
```

禁止在执行阶段通过“再读 plan/contract 后自己理解”绕过该缺口。这样会把 N2 契约重新变成 N1 临场推理。

如果执行中发现前端 action 的真实落点不清楚，或 Atomic Issue 写的文件与代码中的 action route 不一致：

```text
Stop -> classify as frontend-action-route-materialization-gap -> update Backflow Invalidation Matrix -> return to code-archaeology-sdd/frontend-contract-design/atomic-task-planning -> add Frontend Action Route Trace/Coverage -> update affected Atomic Issue -> rerun verification planning -> continue only after issue is sealed
```

不得在执行阶段自行选择“看起来像 update page 的文件”继续实现。必须先把 visible action、route builder、router definition、landing component 和验证证明写回 Atomic Issue。

如果执行中发现前端矩阵行只出现在 `Source Context`、`semantic_carriers`、source excerpt、implementation steps 或 verification summary，而没有进入对应专用执行字段：

```text
Stop -> classify as frontend-matrix-consumption-gap -> update Backflow Invalidation Matrix -> return to frontend-contract-design / atomic-task-planning -> copy the exact matrix rows into action_route_component / mode_field_display_matrix / form_state_matrix / mode_negative_assertions / browser_verification -> rerun compile/check/pre-execution -> continue only after issue is sealed
```

不得用“我已经读过矩阵”继续实现。矩阵行没有进入 owner packet 的执行 section，就等价于没有被当前 Atomic Issue 消费。

如果执行中发现 issue 的文件范围不可行，例如实现 API 返回必须改 VO/controller、持久化兼容必须改 DO/mapper/migration、事件机制必须改 event/progress producer、前端操作必须改真实下拉 source/handler/router/landing，但 `files_to_change` 没有包含这些文件：

```text
Stop -> classify as allowlist-feasibility-gap -> update Backflow Invalidation Matrix -> return to code-archaeology-sdd / frontend-contract-design / atomic-task-planning -> add required files or split task -> rerun compiler/check/pre-execution -> re-admit task
```

不得用 properties JSON、private adapter、相邻页面、hidden helper 或“顺手改未列文件”绕过。`workflowctl.py admit-task` 会封存 file allowlist；`validate-task-diff` 只允许当前任务修改 allowlist 内文件，以及 execution-mutable artifacts：`workflow-state.yaml`、`execution-state.yaml`、`task-verification-log.yaml`、`task-semantic-review.yaml`、`mock-acceptance-execution.yaml`、`task-receipts/*`。

如果 `pass-task` 因关键词误判，把普通后端/API/domain/adapter/event task 当成 frontend 或 mock acceptance owner，要求执行不属于当前 issue 的 backend matrix、frontend action matrix 或 packaged playground rows：

```text
Stop -> classify as task-owner-classifier-gap -> update workflow tool or owner metadata -> keep task text truthful -> rerun compiler/check/pre-execution -> re-admit task
```

不得通过删除真实语义词、替换 `runtime/provider/frontend/mock/no-cloud/fixture` 文案、伪造 matrix row、或手写 receipt 来绕过 validator。真实修复是让 `task-dag.yaml` 的 `layer`、packet 的 `mock_acceptance_target` / `acceptance_target`、以及 matrix owner 明确。普通后端任务可以提到下游 UI、外部适配器、fixture 或 no-cloud 语义，但这些词不能让它承担全量 mock acceptance。

mock acceptance 必须按 owner 分层关闭：

- `mock-backend` owner 只关闭 backend matrix rows。
- `mock-frontend` owner 只关闭 frontend action rows。
- `packaged-playground` owner 只关闭 packaged representative cases。
- 普通 backend task 的完成证据是后端行为测试、verification log 和 `validate-task-diff`。
- 普通 frontend UI task 的完成证据仍是它自己拥有的 browser/DOM/click/network/action row，不得用 build/lint/typecheck 替代。

如果执行中遇到前端验证环境重、playground 暂时不可用、或只跑了 build/lint/typecheck：

```text
Stop -> classify as frontend-action-flow-verification-gap -> keep current task not passed -> update task-verification-log.yaml with Not Run -> backflow to mock-frontend-action-matrix / mock-acceptance-cases or rerun browser proof -> pass-task only after row-level UI-ACT browser evidence passes
```

不得用 “deferred to T005/mock acceptance” 关闭当前前端 UI issue，除非当前 issue 的 Done Criteria 本来就是 `implemented-pending-action-flow` 且 Task DAG 明确后续 verification issue 承担同一个 `UI-ACT-*` 的 browser/network/DOM proof。在这种情况下当前 task 也不能通过 `pass-task` 标成 passed，只能保持未完成或由专门 verification issue 通过。

## No Subagent Execution Discipline

执行阶段默认不使用 subagent 做实现。主 agent 必须按 Task DAG 拓扑顺序执行 sealed Atomic Issues，并在每个非纯文档、非 trivial task 完成后做 diff、verification log 和 task-local semantic review 审计。

规则：

- 不把实现工作分派给 worker subagent。
- 单个任务执行时只消费对应 `atomic-issues/Txxx.md`，不得重新读取全局文档补语义，不得改其他 issue 的文件。
- 如果 issue 缺 source 语义、文件落点、consumed/provided contract、前提、验证 expected result 或 action route，必须返回 `blocked-pending-backflow`，不得自行猜测实现。
- 如果 issue 文件范围不支持其语义，必须返回 `blocked-pending-allowlist-feasibility-backflow`，不得用未列文件或绕路实现补齐。
- 标记 task done 前，主 agent 必须做 admission review：diff 只在 admitted file allowlist 内，provided obligations 被满足，未改变 consumed contracts，验证结果 fresh，`task-semantic-review.yaml` 无 blocking findings，且 `workflowctl.py validate-task-diff Txxx` 与 `workflowctl.py pass-task Txxx` 均通过。
- 非并行或高耦合任务仍按 DAG 串行执行；并行只作为 Task DAG 的文档属性，不触发 subagent。
- 发现新决策、契约缺口、action route 缺口或验证缺口时，必须 stop/backflow，不能临场选择。

### Required Readonly Reviewer Gate

只允许一个受控例外：`pass-task` 前必须使用只读 reviewer subagent 做 task-local semantic review。

这是一个同步阻塞 review，不是并行执行 lane。主 agent 启动 readonly reviewer 后，必须等待 reviewer 返回 final findings，单次等待超时必须设置为至少 30 分钟；30 分钟内未返回时不得 fallback 到 `main-local` pass，只能继续等待或保持当前 task blocked。完成复核、必要修复、重跑验证和 `task-semantic-review.yaml` 落盘之后，才能继续当前 `pass-task` 或进入下一个 Txxx。等待 reviewer 期间禁止：

- `admit-task` 任何后续任务。
- 修改任何业务代码或 execution-mutable artifact。
- 读取并执行下一个 `atomic-issues/Txxx.md`。
- 把 reviewer 仍在运行时的部分输出当成通过证据。

这个 reviewer subagent 不是 worker，不能改代码、不能生成或修改 canonical artifact、不能运行 `pass-task`、不能决定 task done，也不能提出新的产品/架构方案。它只读取：

- 当前 `atomic-issues/Txxx.md`
- 当前 task admitted file allowlist 内的 diff
- `task-verification-log.yaml` / `execution-state.yaml`
- `mock-acceptance-execution.yaml`（仅当当前 task 是 mock/playground owner）
- 必要时读取当前 task issue 列出的相关代码文件

reviewer 输出只能是 findings：

| Finding type | Allowed meaning |
|---|---|
| `contract-deviation` | 代码/测试与 `Provided Contract Obligation`、契约摘录或行为细节不一致 |
| `verification-insufficient` | 验证没有证明 issue 要求，例如 helper test 替代真实 route/API/controller/browser proof |
| `behavior-bug` | 当前实现存在可直接导致任务语义失败的 bug，例如不可达分支、断言与测试名相反、入口 validation 漏测 |
| `diff-scope-risk` | diff 与 admitted allowlist、模块边界或禁止事项不一致 |
| `no-findings` | 未发现阻塞问题 |

主 agent 必须复核 reviewer findings。真问题立即修复并重跑验证/review；误报必须在 `task-semantic-review.yaml` 记录 `disposition=not_a_bug` 和理由；需要改上游 artifact 的问题必须按 backflow 处理。reviewer 的输出不得直接进入 `proposal/spec/plan/tasks/atomic-issues`，只能作为 execution review evidence。

只有在 subagent 工具不可用、上层系统禁用 subagent、当前会话没有用户显式授权启动 subagent、用户明确禁止 subagent，或当前 task 是纯文档/trivial 且无业务 diff 时，才允许 fallback 到 `main-local` review。fallback 时主 agent 仍必须完成同样的 task-local semantic review，并在 `task-semantic-review.yaml` 写明 `subagent_fallback_reason` 和 `subagent_fallback_scope`。没有 fallback reason 的 `main-local` review 不能通过 `workflowctl.py pass-task`。

无论来源是 `readonly-subagent` 还是带明确 fallback 的 `main-local`，最终都必须落盘到 `task-semantic-review.yaml`，并通过 `workflowctl.py pass-task` 校验。

每个非纯文档、非 trivial task 完成后，必须执行一次本地审计：

```markdown
### Atomic Execution Task-Local Semantic Review

| Task | Reviewer type | Verdict | Issue alignment | Contract alignment | Verification alignment | Diff scope alignment | Blocking findings | Required backflow | Blocks task done |
|---|---|---|---|---|---|---|---|---|---:|
```

`task-semantic-review.yaml` 推荐结构：

```yaml
reviews:
  - task: Txxx
    reviewer_type: readonly-subagent # fallback only: main-local
    subagent_fallback_reason: "" # required when reviewer_type=main-local
    subagent_fallback_scope: ""  # required when reviewer_type=main-local
    reviewed_at: "YYYY-MM-DDTHH:MM:SSZ"
    verdict: pass # pass | no-findings
    checked_sections:
      - Provided Contract Obligation
      - 行为细节 / Invariant Carryover
      - negative assertions / 禁止事项
      - Verification expected result
      - admitted file allowlist and current diff
    issue_alignment: pass
    contract_alignment: pass
    verification_alignment: pass
    diff_scope_alignment: pass
    changed_path_hashes:
      repo/path.java: "<sha256>"
    blocking_findings: []
    non_blocking_findings: []
    dispositions: []
```

阻塞条件：

- diff 超出 Atomic Issue 的 Files To Change / scope。
- 实现改变了 consumed/provided contract 或模块边界。
- 实现与 `Txxx.md` 明确语义相反，例如任务要求 canonical capacity 不携带 workerSpec，代码或测试仍把 workerSpec 放进 capacity。
- 测试名、断言和任务语义互相矛盾。
- 存在明显不可达分支、入口 validation 漏测、或 helper-only proof 导致任务要求没有被证明。
- 前端 action 落点、mode 分支或 forbidden inherited UI/API 与 Atomic Issue 不一致。
- 前端 task 只有 build/lint/typecheck/payload helper 证据，没有逐 `UI-ACT-*` 的 browser/click/network/DOM/screenshot-or-trace 证据。
- 前端/browser proof 写成 Not Run/deferred；这只能留下阻塞记录，不能通过 `pass-task` 标成 passed。
- mock/playground/runtime 改动没有对应 verification。
- `task-verification-log.yaml` / `execution-state.yaml` 没有 fresh command/result，或 Not Run 阻塞项被当作 done。
- `task-semantic-review.yaml` 缺当前 task 记录、verdict 非 pass/no-findings、blocking_findings 非空、或 changed_path_hashes 与当前 diff 不一致。

获取 `changed_path_hashes` 的命令：

```bash
python3 /Users/keqing/.codex/skills/ai-dev-methodology/scripts/workflowctl.py review-hashes Txxx specs/changes/<change-id>
```

## 遇到新决策

如果执行中出现未锁定决策：

```text
Stop -> record decision gap -> update Decision Registry + Backflow Invalidation Matrix -> update proposal/spec/plan/tasks -> ask user/reviewer -> continue only after locked
```

输出格式：

```markdown
## Decision Gap

| Field | Value |
|---|---|
| Task | Txxx |
| Source | REQ/SCN/C/MIG |
| Gap |  |
| Options |  |
| Recommended decision |  |
| Files blocked |  |
```

不得在代码里临场选择。Decision Gap 必须同步回写到：

如果执行中发现需要改变 consumed/provided contract，或发现当前 issue 没有声明相关契约：

```text
Stop -> classify as contract-gap or atomic-issue-not-contract-closed -> update Backflow Invalidation Matrix -> update Module Contract Graph / contracts / issue -> rerun Task DAG and affected verification -> continue only after locked
```

- Decision Registry，状态为 `open`。
- `task-verification-log.yaml` / `execution-state.yaml` 的 Decision Gaps 或 Handoff Notes。
- 当前 `atomic-issues/Txxx.md` 的 Decision Gap / Blocked section。
- 必要时更新 `spec.md` / `plan.md` 后再继续。

任何回流都必须同时处理：

- Backflow Trigger：记录发现位置、类别、最早缺失阶段和必须回流的阶段。
- Invalidation Matrix：列出失效的 DEC/C/T/VER、Atomic Issues 和需要重跑的验证。
- Supersession Record：记录旧对象和新对象，确认语义是否已复制。
- Task 状态：受影响 task 标为 `blocked` / `pending-rewrite` / `pending-rerun`，不得继续当作 done。

## 验证命令库

按任务类型选择，命令以 repo 实际脚本为准。

| 类型 | 验证 |
|---|---|
| Java backend | compileJava / test / checkstyle |
| frontend | typecheck / lint / build / targeted tests |
| UI behavior | Playwright or browser verification when applicable |
| OpenAPI | schema generation/diff and API tests |
| DB migration | migration test / rollback test |
| Terraform | fmt / validate / plan or provider tests |
| Helm/K8s | helm template / lint / kube schema validation |
| Cloud resource | dry-run/plan, IAM policy check, lifecycle hook smoke test |
| Observability | metric/event/log unit tests or runtime smoke |
| Runtime lifecycle | create/update/delete/scale/retry API + task + runtime state consistency |
| Runtime auto-adjustment | CPU/memory/lag/等价压力触发运行时自动调节，观察 desired/actual/status/event |
| Docs | link/render check when available |

如果计划验证无法运行，必须写入 `task-verification-log.yaml` / `execution-state.yaml` 的 Not Run，并确保 `pass-task` 不会通过 blocking Not Run。

执行纪律：

- Java backend 行为变更必须至少运行能命中真实生产路径的 unit/integration/API/runtime 测试，并在 `task-verification-log.yaml` 记录 assertion/behavior_id。`compile`、`package -DskipTests`、checkstyle 只能证明可构建，不能证明 source/contract 语义成立。
- 如果后端任务声称 typed error、warning、兼容旧 payload、状态持久化、事件/progress、provider cleanup、autoscaling decision 等行为，验证必须分别断言这些行为；不能只用一个 service happy path 关闭所有 contract。
- 不能用创建成功替代删除、更新部署配置、指标链路或自动调节验证。
- 自动调节任务没有压力触发证据时，必须写 Not Run risk，不能标 Done。
- Metrics 显示为 0 时，必须按契约确认是真实 0 还是空序列/query error/采集未配置；无法确认则记录为 verification failure 或 Not Run。
- 删除任务必须验证云资源清理、残留资源表达或幂等重试；只看到 API 返回成功不能标 Done。

## Verification Log 回写

完成前必须更新 `task-verification-log.yaml` 或 `execution-state.yaml`，不得更新 sealed `tasks.md`：

```markdown
## Verification Log

| Date | Check | Command / Source | Result | Notes |
|---|---|---|---|---|
| YYYY-MM-DD |  |  | pass/fail |  |

## Not Run

| Check | Source | Severity | Reason | Risk | Owner/approval | Blocks done |
|---|---|---|---|---|---|---|

## Decision Gaps

| Task | Gap | Status | Resolution |
|---|---|---|---|
```

不能只在聊天里说“测试通过”。

Not Run 规则：

- `Severity=P0/P1`、核心 REQ/SCN、关键跨模块契约、组合验证、runtime lifecycle 或 `Blocks done=yes` 的项目阻塞完成声明。
- 这些项目只能进入 `blocked` 或 `risk-accepted-by-user` 状态；没有用户/owner 明确接受时不得标 Done。
- 低风险 Not Run 也必须写清 expected proof 缺失后哪些语义仍未证明。
- 前端 UI issue 的 browser/DOM/click/network/screenshot-or-trace proof 是完成证据；写成 Not Run/deferred 时 `pass-task` 必须失败，除非当前 issue 明确不是完成 issue，而是后续专门 verification issue 的前置实现包，并保持未 passed。

## 完成前自检

- [ ] 每个完成任务都有 `workflow-state.yaml.task_receipts.Txxx.status=passed`。
- [ ] 每个 REQ/SCN 有完成任务或 N/A。
- [ ] 每个 contract 有实现和验证。
- [ ] 每个 migration plan 项有执行或 N/A。
- [ ] `task-verification-log.yaml` / `execution-state.yaml` 有 fresh command/result。
- [ ] mock/playground owner task 的每个 owned backend/frontend/event/package row 都有 `mock-acceptance-execution.yaml` 终态行级证据。
- [ ] Not Run 记录完整。
- [ ] Not Run 中没有未接受的 P0/P1 或 `Blocks done=yes` 阻塞项被当作 done。
- [ ] 如果发生回流，Backflow Invalidation Matrix 已更新，受影响 task 不处于错误 done 状态。
- [ ] Task DAG 中当前 task 的后继只在 predecessor 完成并验证后继续。
- [ ] 当前完成的 Atomic Issue 仍是 sealed execution packet：物化前提、consumed snapshot、provided obligation、不变量和前提失败处理均已保持最新；如执行中发现缺失，已按 contract-materialization-gap 回流。
- [ ] 涉及前端 action 的任务已按 Atomic Issue 中的真实 route/component 链路实现；若执行中发现链路缺失或文件不一致，已按 frontend-action-route-materialization-gap 回流。
- [ ] 适用任务已完成 Atomic Execution Local Review；无 `Blocks task done=yes` 项。
- [ ] 判断是否需要更新 `specs/current/`。
- [ ] 没有 out-of-scope diff。
- [ ] 已满足 artifact-completeness-spec Stage 10 的 issue completeness check、scoped file reads、short-loop verification、verification log、decision gap、not run risk artifact 要求。

## 输出

最终回复只总结：

- 完成了哪些 tasks。
- 执行了哪些 Atomic Issues。
- 修改了哪些 repo/files。
- 运行了哪些验证。
- 未运行检查和残余风险。
- 是否更新了 `task-verification-log.yaml` / `execution-state.yaml`、适用的 `mock-acceptance-execution.yaml`，以及是否生成了 `task-semantic-review.yaml` 和 `pass-task` receipts。
