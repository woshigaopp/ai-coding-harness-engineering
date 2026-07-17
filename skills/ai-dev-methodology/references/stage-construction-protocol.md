# Stage Construction Protocol

## 目录

- [目标](#目标)
- [单一事实源](#单一事实源)
- [命令协议](#命令协议)
- [Obligation 闭合模型](#obligation-闭合模型)
- [校验分层](#校验分层)
- [兼容与回流](#兼容与回流)
- [诊断要求](#诊断要求)

## 目标

Stage Construction Protocol 把已知规则从阶段末 gate 左移到阶段开始和构造过程。它不削弱 `workflowctl.py validate/pass-stage`，而是在最终 gate 前增加两个确定性边界：

1. `prepare-stage`：根据已签收上游、机器可读规则和当前需求信号生成本阶段适用 obligation。
2. `validate-obligation`：每完成一个语义对象就检查其闭合字段并写入行级 validation receipt。

阶段末 `validate-stage-construction` 只接受全部 obligation 已关闭、行级 receipt 未过期、stage contract 和上游输入未漂移的 ledger。最终 `validate <stage>`、`validate_artifacts.py`、只读 reviewer 和 `pass-stage` 继续负责全局一致性、语义审查和 receipt。

## 单一事实源

机器规则位于：

```text
${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/stage-construction-contracts.yaml
```

运行时身份由 `templates/workflow-runtime-manifest.yaml` 固定。它记录 runtime version、profile policy、artifact schema compatibility 以及 `workflowctl.py`、`validate_artifacts.py`、compiler、machine contract 的 SHA-256。active change 必须把 runtime version 与 manifest hash 固定到 `workflow-state.yaml`；安装规则变化后只能显式执行 `migrate-workflow-runtime`，不得让历史 workflow 静默接受新规则。

每条规则必须有：

- 稳定 `rule_id`。
- `earliest_stage`，表示最晚何时应被识别。
- `phase`：`preflight`、`incremental` 或 `final`。
- `rationale`，解释为什么存在。
- `repair_stage`，禁止 validator 只给出模糊修复建议。
- `allow_not_applicable`。
- `required_closure`。

`SKILL.md`、阶段执行包和 validator 引用该文件，不再分别维护另一套字段要求。新增已知规则时先修改 machine contract 和 smoke test，再修改自然语言导航。

## 命令协议

进入任一 canonical stage artifact 前运行：

```bash
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py prepare-stage <stage> specs/changes/<change-id>
```

命令执行：

1. 校验 `workflow-workdir.md` 和已签收上游 receipt。
2. 校验当前阶段要求的 context pack 或 `plan.md` rehydration section，再读取 machine contract。
3. 扫描上游 canonical artifacts 中的 applicability signal。
4. 生成 `stage-construction/<stage>-obligations.yaml`。
5. 生成 `stage-construction/<stage>-execution-pack.md`。
6. 若 machine contract、上游 receipt 或 trigger evidence 变化，将旧 row 标为 `pending-rewrite`，不得静默复用旧 validation。

context pack 不是长度门禁。每个 pack 必须包含：当前 source artifact path + SHA-256、全部上游 receipt hash、消费的语义对象 ID、`Copied Semantic Excerpt` 及其 SHA-256、`Downstream Coverage Targets`，以及值为 `none` 的 `Unresolved Required Rows`。重复 filler、只写阶段摘要、缺 hash 或存在 unresolved required row 都在 `prepare-stage` 前失败。

若当前阶段已经 `passed` 且 receipt、ledger、execution pack、contract、trigger 和 canonical artifact hash 全部新鲜，`prepare-stage` 必须是字节级 no-op。任一项过期时必须拒绝修改任何 stage-construction/workflow 文件，先创建并应用 backflow，把阶段移出 `passed` 后再重建。

完成单个 obligation 后，在 ledger 中填充 closure 并运行：

```bash
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py validate-obligation <stage> <obligation-id> specs/changes/<change-id>
```

该命令通过后写入 row-level validation receipt。`file.md#Section` 只固定该 section；typed obligation 进一步只固定包含自身 `object_id` 的结构化行。closure 或该对象的语义内容变化会使 receipt stale，无关 section/row 和 presentation-only Markdown 变化不会扩大失效范围。canonical reference 缺 section 时直接失败，不能退化成整文件 hash。

阶段末运行：

```bash
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py validate-stage-construction <stage> specs/changes/<change-id>
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py validate <stage> specs/changes/<change-id>
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py pass-stage <stage> specs/changes/<change-id>
```

`pass-stage` 会再次执行 stage-construction 校验。没有 ledger、存在 open/pending-rewrite row、row receipt 过期、contract hash 过期或 input fingerprint 过期时不得签收。

passed/N/A 阶段需要修复时，先记录并应用真实 backflow，再运行 `workflowctl.py reopen-stage <stage> <change-dir> --backflow-id <BF-ID> --reason <reason>`。该命令将当前及传递下游阶段置为 `pending-rewrite`、删除对应 receipt；只有 task-planning 或更早阶段失效并传递到 execution 时才清除 execution/task receipt，单独重做 acceptance 保留 execution。不得手改阶段状态。

## Obligation 闭合模型

每个 obligation 使用以下闭合链：

```text
trigger/source
-> canonical artifact
-> semantic object / decision
-> production owner / consumer
-> contract
-> verification
-> negative assertion
-> downstream consumer
```

machine contract 的 `required_closure` 与 `defaults.closure_fields_available_by_stage` 共同决定当前规则需要链路中的哪些字段。规则可以描述完整生命周期，但 PRD/AIP/design 不得被要求填写尚未存在的 `C-xxx` 或 `VER-xxx`；这些字段只在 contract/verification/task/acceptance 等拥有它们的阶段成为必填。字段必须填具体路径、ID、断言或 downstream artifact，不能填写 `covered`、`handled`、`mode-aware`、`see plan` 等摘要词。

ledger 中的 `rule_id`、title、phase、earliest/repair stage、N/A 权限、required closure、trigger 和 digest 都是 machine contract 的派生元数据，不是人工输入。validator 必须逐字段按当前 contract 重算；修改 ledger 元数据不能降低义务，只能导致失败并要求重新运行 `prepare-stage`。人工只允许填写 `closure`，状态和 validation receipt 由命令推进。

带 `decompose_by` 的规则必须按 canonical artifact 中的 typed object ID 展开，每个 resource、operation、UI action、side effect、contract obligation 各有独立 obligation ID。到 machine contract 指定的 `typed_required_from_stage` 后仍找不到对象 ID 时，禁止退回单条 coarse obligation。closure 引用的 semantic/decision/contract/verification ID 必须真实存在于其 canonical artifacts，正则形状正确但不存在的伪 ID 无效。

允许 `not_applicable` 的规则必须同时填写：

- `reason`：为什么当前需求不触达该义务。
- `product_semantics`：用户/API/UI 实际看到什么。
- `verification`：如何证明它是产品级 N/A，而不是内部异常或漏实现。

不允许 N/A 的规则只能关闭为 `closed`；证据不足时保持 `blocked`，回流到 `repair_stage`。

整个 stage 的 N/A 与单条 obligation N/A 不同。整个 stage 只能通过 `mark-stage-na` 写入带 canonical hash 的 `stage_na_receipts`，并受 profile 的 `whole_stage_na_allowed` 控制。`source-intake`、`prd`、`readiness` 等 profile 必需阶段不能靠手改 `stage_status` 跳过。

## 校验分层

| 层 | 发现内容 | 失败动作 |
|---|---|---|
| Preflight | 上游 receipt、context 输入、适用规则、必须先决策或调研的 blocker | 不创建当前阶段 canonical artifact |
| Incremental | 单个 obligation 的 owner、语义、decision、contract、negative assertion、verification 和 projection | 停留在当前 obligation，不扩展下一组对象 |
| Final deterministic | obligation coverage、hash freshness、跨对象结构一致性 | 修复 ledger/canonical artifact 后重跑 |
| Readonly review | 漏 surface、错误 owner、错误模块边界、证据不足或真实语义冲突 | 主 agent 裁决并回流；不得让 reviewer 修改 artifact |
| Stage receipt | 全量 validator、rubric、reviewer 和 artifact hash | 只有 `pass-stage` 可以写 `passed` |

最终 gate 如果发现缺字段、缺 owner、缺 verification、非法状态、已知 trigger 未投影等机械问题，必须用 `record-late-defect` 写入 `workflow-defects.yaml`。相同 failure signature 递增 recurrence count，不得复制新行；每行必须声明 should-have-caught stage、repair action 和 machine-rule/test promotion target。当前产品 workflow 修 artifact 后用 `repair-late-defect` 固定 change-local artifact hashes，并实际执行 validator commands、固定 exit code/time/output digest，状态变成 `locally-repaired`；不得在产品 workflow 中修改全局 skill/runtime。promotion 留给独立 methodology maintenance/retrospective。最终 gate 应主要发现跨对象一致性和新的语义问题。

## 兼容与回流

新 contextpack change 必须从 `templates/workflow-state-contextpack.yaml` 创建 `workflow-state.yaml`，并以 schema v2 启用：

```yaml
schema_version: 2
workflow:
  profile: full
  stage_construction_protocol: stage-construction-v1
  runtime:
    version: <copied from workflow-state-contextpack.yaml>
    manifest_sha256: <manifest SHA-256>
```

共享的 `templates/workflow-state.yaml` 保持标准 workflow 的 schema v1，不携带本协议 marker。标准 schema v1 不会因正文提到 context pack 而启用本协议；历史 contextpack schema v1 对当前 validator 返回单一 migration-required 结果，不能直接运行 `prepare-stage`。

旧 active change 的 schema v1 不被自动强制迁移。需要启用时运行 `workflowctl.py migrate-workflow-runtime <change-dir> --profile <profile>`；命令会升级 schema、固定 runtime，并把旧 `passed` 改为 `pending-rewrite`、清除旧 stage/N/A/execution/task receipts。不得手工伪造 runtime pin、ledger 或 receipt。

以下变化会让 ledger stale：

- stage contract hash 改变。
- 当前 stage 消费的上游 receipt hash 改变。
- trigger scan 的 path、matched pattern 或 excerpt 改变；即使 obligation 集合未变化，也必须重新确认输入。
- obligation closure 改变。
- closure 引用的 canonical artifact 内容改变。

`external-capability-research.md` 是 AIP-owned synthesis，不进入 source-intake receipt；修改其 schema 或叙述只能失效 AIP 及其下游。source-intake receipt 只封存原始 source ledger 和不可变 identity。

发生上游语义回流时，先按既有 Backflow Invalidation Matrix 失效 DEC/C/VER/T，再重新运行对应阶段 `prepare-stage`。stage-construction ledger 不是新的 source of truth；它只记录 canonical artifacts 如何满足 machine contract。

## 诊断要求

每条错误必须包含：

```text
rule_id
earliest_stage
detected_stage
trigger evidence
missing or stale closure
rationale
repair_stage
forbidden shortcut
```

示例：

```text
RULE SC-MANAGED-RESOURCE-001 [earliest=prd detected=task-planning]
trigger=spec.md:auto-create
missing=contracts, negative_assertions
rationale=selector/readback cannot close provider resource lifecycle
repair_stage=contract
forbidden_shortcut=do not add "managed resource" wording to a task packet
```

诊断的目的不是帮助绕过 parser，而是把缺口送回最早拥有该语义的阶段。
