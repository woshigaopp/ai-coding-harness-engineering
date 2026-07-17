---
name: automq-ai-dev-workflow-contextpack
description: AutoMQ 大需求与大改动的 context-pack 工作流总入口。Use when Codex must turn product requirements or AIP input into gate-locked specs/changes artifacts, module contracts, verification, self-contained Atomic Issues, implementation, mock/product acceptance, and launch convergence; also use when continuing or repairing an active contextpack workflow and when stage validators repeatedly reveal late construction defects.
---

# AutoMQ AI Dev Workflow Contextpack

## Objective

把大需求转成按模块、契约闭包、自包含、可短验证的 Atomic Issues，并在实现后完成 mock/product acceptance 与上线收敛评审。

本入口只保留编排和不可违背的边界。详细规则位于 [workflow-rule-reference.md](references/workflow-rule-reference.md)，阶段构造协议位于 `${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/references/stage-construction-protocol.md`，机器规则位于 `${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/stage-construction-contracts.yaml`。

不要把完整规则全文同时装入每个阶段上下文。先运行 `prepare-stage`，只消费生成的 stage execution pack；遇到具体 gate、触发器或回流时再读取详细 reference 对应章节。

## Non-Negotiable Model

大需求 workflow 必须同时满足：

1. 决策面先于决策锁定。
2. 模块契约先于 checklist task。
3. 生产实现契约与验收 adapter 契约分离。
4. 每个阶段只消费已 `passed` 且 receipt 未过期的上游。
5. 每个阶段先 preflight、再逐 obligation 闭合、最后做全局 gate。
6. Atomic Issue 是上游事实的派生产物，不是 source of truth。
7. 实现只能消费已签收的 Atomic Issue；发现新决策必须回流。
8. Atomic execution 完成不等于需求完成，仍需 acceptance 和 launch convergence。

## First Action: Workflow Identity

新 workflow 的第一个 canonical artifact 必须是：

```text
specs/changes/<change-id>/workflow-workdir.md
```

使用 `${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/workflow-workdir.md`。它必须早于 `purpose.md`、`source-intake-ledger.md`、`proposal.md`、`spec.md`、`plan.md`、`tasks.md` 和任何阶段 artifact。

恢复 session、上下文压缩后继续、cwd 不确定或用户说“继续”时：

1. 先找并读取 active change 的 `workflow-workdir.md`。
2. 运行 `workflowctl.py verify-resume specs/changes/<change-id>`，确定性对比 worktree、change dir、change-id、branch 和 base commit。
3. 命令只追加 hash-chained `resume_verified` workflow event，不修改 receipt-bearing `workflow-workdir.md`。
4. 不一致时切回登记 worktree 或报告 blocked；不得创建新 change/worktree。

Base branch 为 `origin/*` 时，source-intake 前必须 fetch 并固定 Remote OID、fetch 时间和命令；“最新分支”不能只消费本地缓存 ref。

详细恢复与隔离规则读取 [workflow-rule-reference.md](references/workflow-rule-reference.md) 的 `Workflow Workdir Identity Gate`、`Session Resume Identity Gate` 和 `Repo Isolation Gate`。

## Stage Construction Protocol

Stage Construction Protocol 是本实验版的默认构造方式。新 change 使用：

从 `${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/workflow-state-contextpack.yaml` 创建 `workflow-state.yaml`，不要使用标准 workflow 的 schema v1 模板。

```yaml
schema_version: 2
workflow:
  skill: automq-ai-dev-workflow-contextpack
  profile: full
  stage_construction_protocol: stage-construction-v1
  runtime:
    version: <copied from workflow-state-contextpack.yaml>
    manifest_sha256: <copied from workflow-state-contextpack.yaml>
```

`profile` 只能是 `full`、`execution-only`、`repair`、`migration`。已有 accepted/sealed tasks 只执行时使用 `execution-only`；它不因启用 contextpack 而重新强制生成 AIP。旧 workflow 不得通过手改 marker 静默升级；运行 `workflowctl.py migrate-workflow-runtime <change-dir> --profile <profile>`，接受旧 receipt 被显式失效后再重签。

### 1. Prepare Before Writing

读取上游 receipt、`workflow-workdir.md` 和对应 context pack 后，在创建或修改当前阶段 canonical artifact 前运行：

```bash
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py prepare-stage <stage> specs/changes/<change-id>
```

该命令生成：

```text
stage-construction/<stage>-obligations.yaml
stage-construction/<stage>-execution-pack.md
```

execution pack 只包含当前阶段适用规则、触发证据、闭合字段、repair stage 和执行顺序。它是当前阶段的 primary construction guide。

`prepare-stage` 失败时不得写当前阶段 canonical artifact。先修 workdir、上游 receipt、未决人类决策、缺失 context pack 或 machine contract。

已通过或 N/A 阶段因 artifact/receipt 漂移需要重做时，先记录并应用真实 backflow，再显式重开阶段：

```bash
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py reopen-stage <stage> specs/changes/<change-id> --backflow-id <BF-ID> --reason <concrete-reason>
```

该命令传递失效下游 receipt；重开 task-planning 或更早阶段而使 execution 成为下游时，才清除 execution/task receipt。单独重做 mock/product acceptance 保留已签收的 execution。不得手改 `passed`/`not_applicable` 为 `pending-rewrite`。

### 2. Close One Obligation At A Time

按 execution pack 顺序，一次只处理一个 obligation。先在 canonical artifact 中闭合：

```text
source/trigger
-> semantic object / decision
-> production owner / consumer
-> contract
-> verification
-> negative assertion
-> downstream projection
```

再把具体 artifact 路径、ID、断言和 consumer 写入 ledger 的 `closure`，运行：

```bash
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py preflight-stage-closures <stage> specs/changes/<change-id>
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py validate-obligation <stage> <obligation-id> specs/changes/<change-id>
```

`preflight-stage-closures` 只读地扫描全部 closure 草稿并一次返回所有 construction errors；open row 会在内存中按待关闭状态检查，PRD/AIP 还会同时执行全局兼容校验。它不写 receipt，不能替代逐条 `validate-obligation`。

canonical artifact 必须引用到最窄稳定 section，例如 `spec.md#用户可见状态`。typed obligation 的 receipt 只固定该 section 中包含自身 `object_id` 的结构化行；禁止用整个 dense Markdown 文件的 hash 让无关 row 一起 stale。

确实不适用且规则允许 N/A 时运行：

```bash
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py validate-obligation <stage> <obligation-id> specs/changes/<change-id> --not-applicable
```

N/A 必须同时写明产品语义、原因和验证，不能用“本需求不涉及”关闭。

如果当前阶段产生新的 surface、mode、mutation、runtime、mock 或 user action signal，立即重跑 `prepare-stage`，让新 obligation 显式进入队列；不要等到阶段末 validator 才补。

### 3. Close The Stage

全部 obligation 有 fresh row receipt 后运行：

```bash
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py validate-stage-construction <stage> specs/changes/<change-id>
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py validate <stage> specs/changes/<change-id>
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py pass-stage <stage> specs/changes/<change-id>
```

`pass-stage` 重新执行 stage-construction 和全量 artifact validator，并把 ledger、execution pack 与 canonical artifacts 一起封存。只有 `pass-stage` 可以写 `stage_status.<stage>=passed`。

整个阶段不适用时只能运行 `workflowctl.py mark-stage-na` 并提供 decision ID、reason、product semantics 和 verification。原始 `not_applicable` 状态、缺 `stage_na_receipts`、profile 禁止跳过的阶段都不能被下游消费。

进入下一阶段前重新读取 `workflow-state.yaml` 和 `workflow-workdir.md`，确认 receipt、hash、cwd、branch 和 change dir 均未漂移。

### Late Detection Discipline

最终 gate 仍可能发现新的跨对象矛盾或 reviewer 发现的新 surface，这是合法语义发现。以下问题不应反复留到阶段末：

- 缺字段、非法状态或缺 artifact。
- 已知 signal 没有 owner obligation。
- 缺 provider/consumer、negative assertion 或 verification。
- 已知 dense semantic carrier 没有 projection。
- 只有 ID、关键词或“见 plan”的摘要式闭合。

这类失败必须作为 `late_detection_defect` 运行 `workflowctl.py record-late-defect` 写入 `workflow-defects.yaml`，把稳定 `failure_signature` 前移到 machine contract、preflight 或 incremental validator，并记录 machine-rule/test promotion target。不得只在当前 artifact 中补关键词。

`open` defect 会阻断后续 gate。产品需求 workflow 先修当前 change 的 artifact 和 validator evidence，再运行：

```bash
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py repair-late-defect \
  specs/changes/<change-id> <LD-ID> --repair-stage <should-have-caught-stage> \
  --artifact-path <repaired-artifact> --validator-command '<command-to-run-and-receipt>'
```

命令会实际执行每条 validator command（单条最多 600 秒），并固定 exit code、运行时间和 output digest；任一命令失败/超时或 repaired artifacts 不包含 defect 的 `affected_artifact` 时不解除阻塞。`locally-repaired` 允许当前需求继续，但不代表全局规则已晋升。产品 workflow 禁止直接修改 `${CODEX_HOME}/skills` 或发布 runtime；machine rule、regression test 和新 runtime 必须在独立 methodology maintenance/retrospective 中完成。只有用户明确进入 methodology maintenance 时，才迁移并晋升：

```bash
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py migrate-workflow-runtime specs/changes/<change-id> \
  --profile <profile> --from-stage <should-have-caught-stage>
```

迁移后必须显式晋升：

```bash
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py promote-late-defect specs/changes/<change-id> <LD-ID> \
  --target-path templates/stage-construction-contracts.yaml \
  --target-path scripts/validate_skill_suite.py \
  --test-id <stable-rule-or-test-id>
```

晋升只证明缺陷已进入可重复的机器规则/测试，不替代当前 change 的 artifact 修复。完成后从 `should_have_caught_stage` 重新 `prepare-stage`、验证并签收；不得通过删除 defect ledger 解锁。active workflow 不因另一个产品需求发现 defect 而自动迁移。

## Stage Transition

适用的 canonical stage：

```text
source-intake
prd
aip
readiness
design
archaeology
migration
frontend-contract
contract
verification
task-planning
mock-acceptance
product-acceptance
```

每个阶段统一执行 deterministic construction；只有 machine `review_policy` 标记 `required=true` 的关键 gate 才执行只读 review：

```text
rehydrate upstream
-> prepare-stage
-> close/validate obligations depth-first
-> deterministic stage validation
-> [review_required] freeze review packet
-> [review_required] readonly multi-perspective review
-> main-agent disposition/repair
-> rerun gates
-> pass-stage receipt
```

候选 artifact、空表、局部 compiler success、无 open question、人工口头确认都不能替代 receipt。

阶段路由：

| Stage | Owner skill | Critical output |
|---|---|---|
| source-intake | source ledger templates | source trace、授权、workflow mode |
| prd | `product-requirement-design` | proposal/spec/PDEC/decision surfaces |
| aip | `aip-template` + `aip-readiness-review` | AIP/ADEC/mechanism model |
| readiness | `requirement-readiness-review` | executable readiness verdict |
| design | `new-feature-design` | domain/module semantics |
| archaeology | `code-archaeology-sdd` | old facts/invariants/patterns |
| migration | `migration-diff-analysis` | delete/keep/modify/add |
| frontend-contract | `frontend-contract-design` | route/action/form/state/API contracts |
| contract | `cross-module-contract-sdd` | provided/consumed executable obligations |
| verification | `verification-matrix` | REQ/SCN/DEC/C/MIG proof and feasibility |
| task-planning | `atomic-task-planning` | DAG、packets、compiled Atomic Issues |
| execution | `atomic-execution-sdd` | code、task receipts、verification log |
| mock-acceptance | `mock-acceptance-gate` | backend/frontend matrices and runtime evidence |
| product-acceptance | `product-acceptance-review` | browser/runtime semantic review |
| launch convergence | launch-readiness template | production-standard PR/diff review |
| retrospective | `convergence-retrospective` | N1/N2 and workflow improvements |

读取 [workflow-rule-reference.md](references/workflow-rule-reference.md) 的 `阶段地图`、`前置输入` 和 `工作流` 获取每个阶段的完整 artifact 与特殊触发器。

## Context Rehydration

以下 context pack 是下游 admission input：

| Boundary | Required artifact |
|---|---|
| PRD/AIP -> design/archaeology | `design-context-pack.md` 或 `plan.md#Design Context Rehydration` |
| archaeology/design -> frontend/contract | `contract-context-pack.md` 或 `plan.md#Contract Context Rehydration` |
| contract/verification -> task planning | `atomic-planning-context-pack.md` |
| implementation -> acceptance | `acceptance-context-pack.md` 或 `mock-acceptance.md#Acceptance Context Rehydration` |

Context pack 必须从磁盘 canonical artifacts 重新生成，包含 source ledger、语义摘录、locked decisions、禁止重新解释、boundary-specific facts 和 downstream coverage。聊天记忆不能补 canonical 缺口。

`external-capability-research.md` 是 PRD normalized 之后、AIP/design 之前构造并由 AIP receipt 封存的工程研究归纳，不属于 source-intake receipt。source-intake 只登记它消费的原始 URL、代码、SDK 和用户输入；研究归纳的 schema 或叙述修复不得回退 source-intake。

已 `passed` 的 plan-bearing 上游必须从 `stage-snapshots/<stage>-plan.md` 恢复接受时语义；`plan.md` 只是当前阶段继续扩展的工作副本，不能用它覆盖或重新解释 snapshot。上游 backflow 后由 `pass-stage` 替换 snapshot，再重新生成下游 context pack。

AIP narrative materialization 只消费 AIP 当时拥有的 ADEC/DEC、MECH/FACT/CONSTRAINT 和 Current Architecture evidence。readiness、design、archaeology、migration、frontend、verification、task-planning 后续新增的阶段决策属于各自 owner stage，不得因共享 `plan.md` 增长而反向制造 AIP backflow；只有它们证明 AIP 原有方案本身缺失或错误时，才按真实语义缺口回流 AIP。

缺失或不完整时先回流上游；不得写下游 candidate artifact。

## Human Decisions

默认权限：

- PRD `PDEC` 逐条由人确认，除非用户明确授权指定范围内按 AI 推荐锁定。
- AIP/AIP readiness `ADEC` 默认逐条由人确认，除非用户明确授权工程决策。
- “继续推进”“直到做完”不等于决策授权。
- 用户声明参与决策后，所有阶段决策都必须逐条询问，直到用户明确退出或放宽。

默认一次只发一条 Human Decision Prompt。用户明确要求集中查看多个决策时，允许用 `decision-bundles/HDB-xxx.yaml` 固定完整 prompt、逐项推荐/备选/影响、batch eligibility、用户对 `all-listed` 的明确响应和 receipt hash；只有合法 bundle 才能一次锁定多项，模糊的“都同意”仍无效。生成交互文本前只在当前 session 首次读取 `${CODEX_HOME:-$HOME/.codex}/skills/verbatim-script-style/SKILL.md`，后续使用 execution pack 中的 prompt schema，不重复装载全文。用户回答后先更新阶段 decision document、Decision Registry、Semantic Consumption Matrix 和必要 backflow。

完整字段和交互状态读取 [workflow-rule-reference.md](references/workflow-rule-reference.md) 的 `Human Decision Participation Gate` 和 `决策文档纪律`。

## Subagent Boundary

Subagent 只能作为同步阻塞的只读 reviewer：

- 只读 frozen packet，输出 evidence-based findings。
- 不生成、修改、补齐或格式修复 canonical artifact。
- 不运行 validator、不签 receipt、不决定 passed/done。
- gate failure repair、schema/parser/receipt 修复由主 agent本地完成。
- required reviewers 必须全部 final 后主 agent 才能裁决和继续。

没有真实 spawn/wait/final output/close evidence 时，`reviewer_type: readonly-subagent` 无效。等待和 lifecycle 的完整硬规则读取 [workflow-rule-reference.md](references/workflow-rule-reference.md) 的 `Subagent Usage Hard Gate` 和 `Controlled Multi-Perspective Review Discipline`。

## Contract And Atomic Issue Boundary

实现 issue 的唯一合格模型：

```text
在一个 primary module 内，假设 consumed contracts 已成立，
实现或保持 provided contracts，且不重新定义模块边界或跨模块语义。
```

每个 Atomic Issue 必须包含 execution preconditions、consumed snapshot、provided obligation、invariant carryover、forbidden re-decisions、files、ordered steps、verification expected result 和 failure backflow。

`atomic-issues/Txxx.md` 必须由 `atomic_issue_compile.py` 从 `atomic-issue-packets.yaml` 编译。`--check` 只证明同步，不证明可执行。

任务拆分与 dense semantic carrier 完整规则读取 [workflow-rule-reference.md](references/workflow-rule-reference.md) 的 `Contract-Closed Issue Last`、`Contract Materialization Gate` 和 `Dense Semantic Carrier Gate`。

## Execution Admission

修改 `specs/changes/<change-id>` 外文件前必须依次成功：

```bash
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/atomic_issue_compile.py specs/changes/<change-id> --check
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py validate pre-execution specs/changes/<change-id>
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/validate_artifacts.py specs/changes/<change-id>
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py begin-execution specs/changes/<change-id>
```

每个任务：

```text
admit-task
-> implement within allowlist
-> short verification
-> validate-task-diff
-> readonly task semantic review
-> write verification/review logs
-> pass-task
```

发现新决策、契约缺口、allowlist 不足或验证不能证明 obligation 时，按最早缺失阶段 backflow/reseal；不得扩大 scope 或把执行日志写回 sealed `tasks.md`。

完整 pre-execution 与 execution 规则读取 [workflow-rule-reference.md](references/workflow-rule-reference.md) 的 `Pre-Execution Hard Gate` 和 `Step 6: 实现纪律`。

## Acceptance And Launch

进入 `mock-acceptance` 不使用不存在的 `execution=passed` transition。admission 要求 fresh canonical execution receipt，且所有 Atomic Issue 都有 canonical `pass-task` receipt；mock acceptance stage receipt 必须在 upstream map 中 pin 该 execution receipt hash。execution backflow/reseal 会显式失效已有 mock/product acceptance receipt。

Mock acceptance 必须分层：

1. Backend Mock Matrix 穷举后端组合。
2. Frontend Action Matrix 穷举真实 action/payload/DOM/negative assertions。
3. Packaged/runtime cases 只做代表性集成、wiring 和 freshness。

生产代码必须调用生产 adapter；no-cloud adapter 只替代物理外部依赖。automqbox/CMP 仅 Connect domain 使用 `cmp-playground`，非 Connect 功能不得读取或生成 playground-specific artifact。

Acceptance 通过后，基于集成 PR 或等价 diff 运行 Post-Atomic Launch Convergence Gate。以生产上线标准而非 Atomic Issue 逐字内容分类 `implementation_gap`、`acceptance_gap`、`launch_decision_required`、`atomic_task_gap`、`methodology_gap` 和 `allowed_implementation_variance`。

完整边界读取 [workflow-rule-reference.md](references/workflow-rule-reference.md) 的 `Mock As First-Class Delivery`、`Packaged Acceptance Runtime Boundary`、`Step 4.6` 和 `Post-Atomic Launch Convergence Gate`。

## Canonical Artifacts

所有 reviewable state 落在：

```text
specs/changes/<change-id>/
```

持久 workflow 文档默认使用中文；代码标识、API、命令、枚举和日志原文保留原文。

Machine runtime：

```text
${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/stage-construction-contracts.yaml
${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/workflow-state-contextpack.yaml
${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py
${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/validate_artifacts.py
${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/validate_skill_suite.py
```

绝对路径 runtime 不存在或不可执行时只能 blocked，不能降级成口头 checklist。

## Startup Output

首次完成身份恢复、原子边界判断和 source intake preflight 后输出：

```markdown
## Workflow Decision

| 项 | 结论 |
|---|---|
| 是否原子任务 | yes/no + 理由 |
| 路径 | new-feature / major-change / execution-only |
| change-id | YYYY-MM-DD-area-topic |
| required artifacts | proposal/spec/plan/tasks/current |
| blocking questions | none 或单条下一 Human Decision Prompt |
| next stage | stage name |
| stage construction | prepared / blocked + ledger path |
```

需要人类决策时只输出一条 Human Decision Prompt，不用批量表格关闭多条决策。
