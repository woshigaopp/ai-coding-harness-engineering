# Complete Workflow Rule Reference

本文件保存 contextpack workflow 的完整细则。主 `SKILL.md` 负责低上下文编排；执行到具体 gate 时按主入口的读取路由加载本文件对应章节。

## 目录

- [定位](#定位)
- [Gate-Locked Delivery](#gate-locked-delivery)
- [Module Contract First](#module-contract-first)
- [Mock As First-Class Delivery](#mock-as-first-class-delivery)
- [Context Pack Experiment](#context-pack-experiment)
- [Contract-Closed Issue Last](#contract-closed-issue-last)
- [阶段地图](#阶段地图)
- [前置输入](#前置输入)
- [工作流](#工作流)
- [Pre-Execution Hard Gate](#pre-execution-hard-gate)
- [实现纪律](#step-6-实现纪律)

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

在“决策前置”之前，workflow 必须先完成“决策面发现”。用户只给 purpose、目标或高层需求时，AI 不能稳定自行想到所有需要决策的点。因此在 PRD/readiness 阶段必须生成 `specs/changes/<change-id>/decision-surface-discovery.md`，使用 `ai-dev-methodology/templates/decision-surface-discovery.md`，覆盖 mode consumer、capability、frontend action、post-create consumer、persistent mutation、operation mutability、managed resource ownership、runtime lifecycle、runtime mode materialization parity、mock acceptance / repo-specific acceptance runtime、observability、permission 和 compatibility。决策面发现不能只消费 experience-shaped triggers；对大需求、高风险 surface、purpose-only 输入或会改变 API/状态/资源/runtime/mock/用户可见语义的需求，还必须运行模板中的 `Generative Surface Stress Tests`，通过 consumer enumeration、mutation chain、invariant breakage、lifecycle completeness 和 reverse acceptance 从当前需求生成 candidate surface。不适用的 stress test type 必须用 `locked-n/a` 说明原因，不能省略。每条 candidate surface 必须有 path trace、broken/uncertain assumption、provider owner、consumer owner、mock/acceptance owner 或 locked N/A、negative assertion 和 verification，并进入 `Surface Obligation Projection Matrix`。只有 stress test 结论、没有 path trace / provider owner / negative assertion / verification 的，不算关闭；缺少 code scope 时必须标 `blocked-needs-code-scope`，不得用猜测的 class/API/path 补齐。每个 surface 必须有 owner stage、locked decision/contract/verification、owner Atomic Issue 或 locked N/A；缺失时不得进入 pre-execution。若命中 runtime mode materialization parity，按需读取 `${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/references/experience/runtime-mode-materialization-parity.md`。若需要理解生成型决策面发现的理论背景，读取 `${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/references/generative-decision-surface-discovery.md`。

## Gate-Locked Delivery

本 workflow 的优先级是：先锁定阶段质量，再推进下一阶段。`继续推进` 只能表示在 gate 允许的范围内自动修复和重跑；不能表示先写候选文档、薄任务或代码来制造进度。

候选 artifact、未锁定文档、空表、部分 packet、局部通过的 compiler check 都不是下游输入。只有状态为 `passed`，且对应 artifact、rubric、validator 全部通过并存在有效 `stage_receipts.<stage>` 的产物，才能被下一阶段消费。

### Workflow Workdir Identity Gate

启动本 skill 后的第一个 canonical artifact 必须是：

```text
specs/changes/<change-id>/workflow-workdir.md
```

它必须在写 `purpose.md`、`source-intake-ledger.md`、`proposal.md`、`spec.md`、`plan.md`、`tasks.md` 或任何阶段 artifact 之前创建。使用 `${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/workflow-workdir.md`，记录：

- target repo、worktree 绝对路径、`specs/changes/<change-id>` 绝对路径和 change-id。
- 当前 branch、base branch、base commit、git top-level。
- 创建时间和命令证据：`pwd`、`git branch --show-current`、`git rev-parse HEAD`、`git rev-parse --show-toplevel`、`git worktree list`。

`workflow-workdir.md` 是恢复身份锚点，不是普通说明文档。上下文压缩恢复、新 session、当前 cwd 不确定或工具摘要提到不同 worktree 时，运行 `workflowctl.py verify-resume <change-dir>` 对比 `Worktree path`、`Change dir absolute path`、`Change id`、`Branch name` 和 `Base commit`。命令把结果写为 hash-chained `resume_verified` event，不修改 identity artifact；同一 session 内没有 cwd/branch/change 漂移证据的普通“继续”不重复装载规则全文。

硬规则：

- 如果当前 cwd 没有 `specs/`，这表示恢复位置错误，不表示可以重新创建 `specs/changes/<change-id>`。
- 如果当前 cwd / branch / change dir 与 `workflow-workdir.md` 不一致，必须停止、报告 expected/actual，或切回该文件记录的 worktree；不得新建 branch、worktree、change-id、`purpose.md` 或 Atomic Issues。
- 如果找不到 `workflow-workdir.md`，但聊天记录、`workflow-state.yaml`、`source-intake-ledger.md` 或用户提供路径能指向已有 active change，必须先恢复并补写该文件；不得因为缺这个文件就重开。
- 新建 worktree/change-id 只允许在确认没有 active change，或用户明确说“重新开始/废弃旧执行/从头新建”之后。
- 所有阶段 receipt 必须封存不可变的 `workflow-workdir.md`。修改 worktree/change/branch/base 等身份字段会使 receipt stale；恢复审计只进入 `workflow-events.yaml`。
- Base branch 为 `origin/*` 时，必须在 source/current-code construction 前记录 `fetched-remote`、Remote OID、fetch 时间和 `git fetch` 命令，且 Remote OID 等于 Base commit。

### Subagent Usage Hard Gate

本 workflow 中的 `subagent`、`worker`、`explorer`、`agent` 和任何 `spawn_agent` 创建的执行体都统一视为 subagent；名称不同不改变权限。Atomic Issue 文档里出现的 `worker` 只是“未来拿到该 issue 的实现执行者”这个抽象角色，不表示当前 workflow 可以启动 subagent/worker 来生成、修复或补齐阶段 artifact。

subagent 唯一合法用途是只读 reviewer：阅读主 agent 已经冻结的 review packet，输出 evidence-based findings。subagent 不得生成、修改、补齐、重写、格式修复、签收任何 canonical artifact，不得运行 gate/validator 或替主 agent 判定 artifact valid / ready / passed；也不得负责 PRD、AIP、readiness、archaeology、design、migration、frontend-contract、contract、verification、atomic-task-planning、mock-acceptance、product-acceptance 或 retrospective 的阶段产物。

`reviewer_type: readonly-subagent` 只是 artifact schema 字段，不是 subagent review 证据。任何 `multi-perspective-reviews/<stage>.yaml`、`atomic-issue-quality-review.yaml` 或 `task-semantic-review.yaml` 只有在同时记录真实 `spawn_agent`、`wait_agent` final status、reviewer final output digest/source 和 `close_agent`/复用证据后，才算完成只读 subagent review。主 agent 自己补写 reviewer row、把旧记录的 reviewer_type 改成 readonly-subagent、或写“按 schema 记录 readonly-subagent”都不算 review，当前 gate 必须保持 blocked。

禁止把以下工作交给 subagent / worker / explorer：

- gate failure repair、validator error triage、schema/parser 修复、receipt hash 修复。
- 缺失 artifact 的创建或补齐，例如 `multi-perspective-reviews/<stage>.yaml`、`verification-feasibility.md`、decision review、contract matrix、verification matrix、context pack、Atomic Issue packet。
- 修改 `specs/changes/<change-id>` 下任何 canonical artifact，哪怕只改表头、字段名、状态词、枚举值或格式。
- 生成 PRD/AIP/contract/verification/task/acceptance 正文、YAML sidecar、rubric scorecard 或 backflow artifact。
- 代替主 agent 做阶段推进、receipt 签收、ready/done 判断、artifact 修复计划或实现计划。

当 `workflowctl.py validate/pass-stage`、`validate_artifacts.py`、`atomic_issue_compile.py`、mock validator、browser smoke 或 acceptance 暴露缺口时，主 agent 必须本地读取 validator 输出、相关 artifact 和脚本规则，亲自修复 canonical artifact，再重跑 gate。只有当前阶段 artifact 已经成为 frozen review candidate，且任务是 Controlled Multi-Perspective Review / Atomic Issue quality review / task-local semantic review 时，才允许启动只读 reviewer。

若主 agent 已经把 artifact repair 交给 worker/explorer/subagent，必须立即停止该 delegation；关闭该 subagent 或忽略其改写产物，由主 agent 回到最早失败 gate 重新本地修复。不得把该 subagent 的输出作为 canonical artifact、review finding 或通过依据。

当用户要求“workflow 继续推进”“直到所有步骤做完”“中间不要中断”时，含义是自动完成从需求到实现、验证、mock acceptance、适用的仓库专属验收 runtime 和产品验收入口的闭环；每一步仍必须经过对应 gate。遇到 gate failure 时，必须回流修到 gate 通过，而不是把 failure 记录成待办后继续。

执行规则：

- 任一 gate、脚本、rubric、本地审计、browser smoke 或 acceptance 返回 `blocked` / `fail` / P0/P1 时，默认动作是回流到最早缺失阶段，修 artifact / 代码 / mock / 验证 / 环境后继续重跑。
- 在 `workflowctl.py validate pre-execution` 和 `validate_artifacts.py` 同时通过之前，禁止修改 `specs/changes/<change-id>` 之外的文件。发现已经有非 specs 代码改动时，必须停止执行、记录 backflow，并先修 artifact；不得继续扩大实现。
- `workflowctl.py` / `validate_artifacts.py` / `atomic_issue_compile.py` 失败、不可运行、输出过长、规则严格、或 agent 觉得修复成本高，都只能导致 `blocked` / backflow；不得降级成 checklist 自审、关键词自审、人工口头确认或“先执行已闭合 Txxx”。
- 没有 `workflowctl.py validate pre-execution`、`validate_artifacts.py` 和 `workflowctl.py begin-execution` 的成功证据时，不得说 `pre-execution complete`、`ready for execution`、`准备开始 T001`、`进入 T001`、`可以开始改代码` 或等价表达。
- 只有真实人类阻塞才停下来：产品决策未授权、凭证/权限缺失、真实云/runtime evidence 客观不可取得、PRD/AIP 互相冲突且无可锁定选择、或用户明确要求暂停。
- `blocked` 不是 `done`，也不是“跳过继续”。它表示当前阶段必须进入 backflow loop，并在 `Backflow Invalidation Matrix`、对应 stage decision doc、`tasks.md` / acceptance artifact 中记录失效对象和重跑结果。
- `completed` / `done` 不是合法阶段状态。`workflow-state.yaml.stage_status` 只能使用 `not_started`、`in_progress`、`blocked`、`passed`、`not_applicable`、`pending-rewrite`、`pending-rerun`。`passed` 不是人工状态，只能由 `workflowctl.py pass-stage <stage> specs/changes/<change-id>` 在对应 artifact、rubric 和 validator 通过后写入，并同时写入 `stage_receipts.<stage>`。
- 手工把 `stage_status.<stage>` 改成 `passed` 或 `not_applicable` 属于门禁违规；`passed` 必须有可重算 hash 的 `stage_receipts`，`not_applicable` 必须有 profile 允许且可重算 hash 的 `stage_na_receipts`。凭证缺失、伪造或过期时，下游必须回流。
- `decision-surface-discovery.md` 中的 `routed-to-*` / `stage-owned` 只允许存在于 owner stage 尚未签收之前。对应 owner stage 正在签收或已经 `passed` 时，该 surface 必须关闭为 locked decision、locked N/A、blocked backflow、C/VER 或 Txxx owner；否则当前 owner stage 不能签收，后续阶段不得消费该 artifact。
- 对 automqbox/CMP Connect 功能，完成状态必须包含可访问的 packaged playground 或明确等价环境、端口/PID/branch/bundle/package freshness、mock/product acceptance evidence、以及交付前 first-line QA 结果。automqbox 非 Connect 功能只使用通用 mock/product acceptance，不感知 `cmp-playground`。

### Stage Boundary Receipt Gate

生命周期分为四类，禁止混用命令：receipt stages 为 source-intake、prd、aip、readiness、archaeology、design、migration、frontend-contract、contract、verification、task-planning、mock-acceptance、product-acceptance，使用 `validate` + `pass-stage`；execution lifecycle 使用 `begin-execution` / `admit-task` / `pass-task`，不存在 `execution=passed` 命令，mock acceptance admission 由 fresh execution receipt + 全部 canonical pass-task receipts 证明，并在 mock receipt 中 pin execution receipt hash；launch convergence 只使用 `validate-launch-readiness`；retrospective 使用 retrospective artifact 与 `workflow-defects.yaml` promotion，不支持 `pass-stage`。

阶段转换协议：

1. 完成当前阶段 artifact 后，运行：

```bash
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py validate <stage> specs/changes/<change-id>
python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py pass-stage <stage> specs/changes/<change-id>
```

2. `validate <stage>` 通过只表示结构校验通过，不表示阶段通过；只有 `pass-stage <stage>` 写入有效 `workflow-state.yaml.stage_receipts.<stage>` 后，当前阶段才可被下游消费。
3. 在创建、修改或消费下一阶段 artifact 前，必须重新读取 `workflow-state.yaml`，确认当前阶段 `stage_status.<stage> == passed`、`stage_receipts.<stage>` 存在、receipt 命令匹配当前 stage，且没有 artifact hash stale。
4. 同时必须重新读取 `workflow-workdir.md`，确认当前 cwd/change dir/branch 仍与记录一致；不一致时先恢复目录身份，不得继续写 artifact。
5. 如果当前阶段或任一已签收上游阶段覆盖的 artifact 后续被修改，必须先重跑受影响阶段的 `pass-stage`，并从最早失效阶段继续；不得继续写更下游 artifact。
6. 若 `pass-stage` 因全量 `validate_artifacts.py --stage <stage>` 发现其它 artifact 缺口，必须按最早缺失阶段回流；不得把 `validate <stage>` 成功当成可进入下一阶段的理由。

禁止替代表达：

- “已补齐”“本地审计通过”“结构审计通过”“没有 open/blocker”“validator 大体通过”“可以进入下一阶段”“先生成下游候选再回头补签”都不能替代 `pass-stage` receipt。
- 缺少当前阶段 receipt 时，不得开始写下一阶段 artifact；已经写出的下游 artifact 只能视为候选，必须在上游 receipt 补齐并确认 hash 未失效后重新校验。
- 不得为了获得 receipt 而只做 parser 规避或弱化语义。凡是为通过 validator 改动关键词、表头、ID、状态词或 owner 表述，必须确认改动是 semantic-preserving；若可能改变产品/工程语义，回流到对应阶段决策。

### Human Decision Participation Gate

本 gate 定义人类决策参与方式。它不是普通 open question 记录，而是阶段推进门禁：只要当前阶段存在需要人确认的决策，阶段就不能签收，后续阶段也不能消费该阶段 artifact。

默认决策权限：

- PRD 阶段产生的 `PDEC` 默认必须停下来让人确认。只有用户明确说“同意 AI 推荐决策”“授权 AI 按推荐方案锁定”“指定范围内的产品决策由 AI 按推荐方案锁定”或等价表达时，AI 才能在授权范围内把推荐方案锁定并继续。授权必须记录范围；范围外、新 surface、或改变用户可见语义的决策仍需逐条确认。
- AIP / AIP readiness 阶段产生的 `ADEC` / 工程关键决策默认也必须停下来让人确认。只有用户明确授权 AI 做工程决策，或明确同意当前推荐方案时，AI 才能锁定并继续。
- 用户说“继续推进”“中间不要中断”“直到做完”“后续应该没有卡点”不等于授权 AI 直接替人做 PRD/AIP 决策；这些话只表示可自动修复 gate failure 和继续执行已授权范围内的工作。

Human participation mode：

- 如果用户说“我参与决策”“每个决策让我确认”“不要自动决策”“后续决策都问我”“我来拍板”或等价表达，workflow 必须进入 `human-decision-participation` 模式。
- 进入该模式后，所有阶段产生的阶段决策都必须逐条停下来让人确认，不只限于 PRD 和 AIP。适用阶段包括 readiness、new-feature-design、code-archaeology-sdd、migration-diff-analysis、frontend-contract-design、cross-module-contract-sdd、verification-matrix、atomic-task-planning、mock-acceptance backflow、product-acceptance backflow 和 convergence retrospective 中会改变后续 workflow 的决策。
- 退出或放宽该模式只能由用户明确表达，例如“后续工程决策按 AI 推荐锁定”“这一阶段后续新发现的同类决策可按 AI 推荐锁定，但每条仍必须生成记录”“退出人工逐条决策”。模糊的“继续”不能退出该模式；任何授权都不能回填关闭已存在但未逐条确认、未逐条记录 prompt 和用户响应的决策。
- 当前 mode 和授权范围必须写入 `source-intake-ledger.md` 或 `plan.md#Human Decision Participation Gate`，并同步到 Decision Registry / Decision Document Index。

逐条交互规则：

- 默认一次只发一条 `Human Decision Prompt`。用户明确要求集中查看时，可以展示 decision bundle；每条仍须有独立 ID、key、推荐、备选、影响和 `batch_eligible=true`。
- 多项确认只有在 `decision-bundles/HDB-xxx.yaml` 固定完整 prompt snapshot/hash、精确 decision list、`response_scope=all-listed`、用户原文、ISO-8601 时间和 receipt hash 时有效。bundle 文件名必须等于 `bundle_id`，所有 decision ID 必须属于其 `stage`，且只进入该 stage 的 receipt；后续 AIP/design bundle 不得反向失效 PRD receipt。没有 bundle receipt 的“以上都同意”不能关闭多个决策；用户改选或不明确的项必须拆回单项。
- 用户回答后，必须先把该决策按现有决策状态模型落盘为 `locked`、`open` 或 `superseded`，更新对应 `decision-reviews/<stage>-decisions.md`、Decision Registry、Semantic Consumption Matrix 和必要的 Backflow Invalidation Matrix，再继续下一条。用户拒绝推荐方案、要求重写、暂不决策、或需要回流时，决策状态保持 `open`，具体原因写入 `User response` / `Resolution` / `Backflow action` 字段；不得发明 `rejected`、`needs-rework`、`still-open` 等新状态。
- 若用户没有明确选择，或回答改变了需求/架构/契约含义，当前阶段必须保持 `blocked` 并回流到最早受影响阶段；不得把模糊回答解释成同意推荐方案。
- 在 `human-decision-participation` 模式下，`workflowctl.py pass-stage <stage>` 前必须能在阶段决策文档中看到每条人类决策的 prompt、用户响应、最终状态、影响 artifact 和更新时间。

生成 `Human Decision Prompt` 前必须读取 `${CODEX_HOME:-$HOME/.codex}/skills/verbatim-script-style/SKILL.md`，并按其 Core Style / Logic Preference 书写：像给一个不熟悉当前项目的人解释决策背景一样，先把为什么现在要决策、关键项目语义和影响链路讲清楚，再给推荐方案。表达应是口语化、推理驱动、可直接读给人听的中文，而不是只有表格或选项编号。

每条 prompt 至少包含：

| Field | Required content |
|---|---|
| Stage / decision ID / Decision key | 当前阶段、决策编号、稳定决策 key |
| 背景说明 | 这个决策为什么在当前阶段出现，缺它会阻塞什么 |
| 关键项目语义 | 涉及的模块、状态、API、UI、runtime、mock/acceptance 边界或兼容语义；默认假设用户不熟悉项目，需要补足必要上下文 |
| 推荐方案 | AI 推荐的一个明确方案 |
| 推荐理由 | 为什么该方案更符合产品语义、现有实现、模块边界、契约闭包和验证可行性 |
| 备选方案 | 至少列出重要备选和不推荐原因；不适用时说明为什么没有合理备选 |
| 影响范围 | 会影响哪些 artifact、DEC/C/VER/T、Atomic Issue、验证或 acceptance |
| 需要用户回答 | 明确请求用户选择、授权按推荐锁定、要求重写，或标记暂不决策 |

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

进入 `cross-module-contract-sdd`、`verification-matrix` 或 `atomic-task-planning` 前，必须在 `decision-surface-discovery.md#Surface Obligation Projection Matrix` 证明每个高风险 surface 已经展开。高风险 surface 至少包括：跨 mode、跨模块、外部副作用、持久化 mutation、operation mutability、runtime lifecycle、user-visible event / progress / change、mock/no-cloud/repo-specific acceptance runtime、权限/资源 ownership、创建后 consumer、兼容迁移和安全/网络/凭证语义。纯文案、局部无状态展示、单文件内部重命名或不会改变 API/状态/资源/验证边界的小改动，可以 locked N/A 或轻量记录，但必须说明为什么不是高风险 surface。

每行必须同时具备：

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
| `baseline/default` 且它暗示 permission、runtime capability、provider identity、generated resource、security policy、ownership behavior、compatibility fallback 或外部系统默认行为 | 拆成具体 baseline/default kind，例如 deploy trust/profile、runtime permission policy、connector-specific permission、provider default context、compatibility default；每类必须有 decision、owner、verification 或 open blocker。普通 UI 初始值、纯展示默认文案或无状态本地默认值不触发重型展开，除非它会被持久化、提交到 API、影响资源/权限/runtime 或改变用户可见错误语义。 |
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
- Operation mutability decision 会改变用户可见语义，未授权 AI 决策时必须按 `Human Decision Participation Gate` 逐条生成 `Human Decision Prompt`；模糊的“按 create 页面做一版”“沿用已有字段”不能关闭该决策。
- frontend action-flow 只能消费已锁定的 mutability decision；不得用“active branch payload 正确”替代“该字段允许在该 operation 修改”的产品/工程决策。

## Module Contract First

大需求不是先拆 checklist task，而是先建模为模块和模块契约图。

必须先回答：

- 有哪些模块。
- 每个模块拥有的数据、状态、资源和生命周期是什么。
- 每个模块对外提供哪些契约。
- 每个模块依赖其他模块提供哪些契约。
- 每条跨模块契约的触发、正常路径、失败路径、一致性、时序和验证是什么。
- 每条跨模块契约是否需要本地 mock acceptance / repo-specific acceptance runtime 表达；mock 对外契约是否与真实 provider/API 同构。
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
| Backend Mock Matrix | 快速覆盖 controller/service/mock-handler/mock-service/API/state 组合 | `mock-backend-matrix.yaml` | 后端组合多且适合快速跑，先挡住 contract drift、fallback、状态机和 fixture 图错误 |
| Frontend Action Matrix | 快速覆盖真实 route/component/API-client/DOM/payload/user action 组合 | `mock-frontend-action-matrix.yaml` | 前端排列组合多，必须在打包前验证 action、payload、DOM、负向泄漏和 selector 状态 |
| Packaged / Repo-Specific Representative Cases | 代表性证明打包产物、静态资源、真实浏览器路由、handler wiring、freshness 和 handoff QA | `mock-acceptance-cases.yaml` + `mock-acceptance.md` | 最慢、最接近交付，只证明集成代表样本，不承担全组合穷举 |

`mock-acceptance-cases.yaml` 的 packaged case 必须通过 `backend_matrix_refs` 和
`frontend_action_refs` 追溯到前两层矩阵。后端或前端矩阵未通过时，不得启动、刷新或交付任何 packaged/runtime/browser 入口来声明验收完成；尤其不得用 packaged browser check 替代矩阵。

这三层 case system 必须在 task-planning / pre-execution 前生成 planned rows。也就是说，mock acceptance 不是 T005 实现完以后临时想测什么，而是实现前已经锁定的测试系统：

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
| `implementation_gap` | PR / diff 没有达到生产上线标准。 | 记录 execution backflow；在原 owner task 范围内 reseal/re-admit，超出原任务边界则回到 task planning 生成/重签 owner issue；修代码、补测试、重跑 acceptance 和 launch review。 |
| `atomic_task_gap` | PR 可以成立，或暴露了当前 Atomic Issues 未能清楚描述的上线级实现闭环。 | 不需要改代码时记录为复盘输入；需要改代码时必须按 implementation gap 的 execution backflow/task regeneration 路径处理。 |
| `launch_decision_required` | 最终上线评审发现实现方无法自行决定的上线时决策，例如接受风险、调整上线范围、选择保守行为。 | 在本 gate 内与人交互确认，记录 human launch decision、owner、影响和结论；不回流到 PRD/AIP/contract/Atomic Issues。 |
| `acceptance_gap` | 实现可能成立，但缺少足够上线证据。 | 补 mock/product/packaged/browser/provider evidence。 |
| `methodology_gap` | 缺口来自 workflow/skill/rubric 没有防住可重复问题。 | 记录为后续 skill/validator 改进输入；不阻塞当前 PR，除非同时构成 launch-blocking implementation/acceptance/decision finding。 |
| `allowed_implementation_variance` | PR 与 Atomic Issue 的具体方案不同，但不破坏需求语义和上线闭环。 | 记录差异，不能当作 implementation gap。 |

硬规则：

- Atomic Issues 是实现计划和对照材料，不是生产上线标准本身。
- 发现 PR 与 Atomic Issue 不一致时，必须先判断差异是否破坏需求语义或上线闭环；如果不破坏，归为 `atomic_task_gap` 或 `allowed_implementation_variance`。
- 评审输出写入 `specs/changes/<change-id>/launch-readiness-review.md`，记录 review input、production standard sources、findings、classification、owner、resolution action、human launch decision、evidence 和关闭状态；模板使用 `ai-dev-methodology/templates/launch-readiness-review.md`。
- 该 gate 是最终 post-PR convergence gate，只能在集成 PR 创建/更新或等价 diff artifact 发布后启动；Review Input 的 `Head` 必须记录当前本地 Git HEAD commit SHA。GitHub PR 由 `gh pr view` 核对 `headRefOid`；等价 review artifact 必须是存在的文件、正文声明当前 Head，且 `Diff source` 同时记录当前 Head 和 artifact SHA-256。无法证明 review source 已刷新到该 commit 时保持 blocked；运行 `workflowctl.py validate-launch-readiness specs/changes/<change-id>` 校验。
- 所有 launch-blocking findings 关闭前，不得宣布 workflow 完成；修复后必须重新执行受影响验证和本 gate。
- 若仓库流程要求 PR，Atomic execution 和 acceptance 完成后必须创建或更新集成 PR，再用该 PR 作为 launch convergence review 对象；若没有 PR 流程，必须有等价 diff/review artifact。
- 当前 `workflowctl.py pass-stage` 不支持该 gate，不得伪造 stage receipt，也不得把它提前建模成普通前置阶段。
- 该 gate 完成即 workflow 完成。纯上线风险决策用 `launch_decision_required` 在本 gate 收口；任何代码、测试、生产契约或验收证据修改都必须回流到最早 owner stage/task，刷新 task output digest、execution receipt、受影响 acceptance receipt 后再运行本 gate。不得在 receipt 之外直接修代码。

## Boundary And Composition Gates

模块契约图本身也必须被验证。不能只“列出模块”和“列出契约”，必须证明模块划分合理、模块组合后覆盖需求。

## Controlled Multi-Perspective Review Discipline

AutoMQ 大需求 workflow 允许在关键 gate 使用 subagent，但只能作为同步阻塞的只读 reviewer。subagent 不是第二个主 agent，不参与并行设计、并行实现、artifact 生成或阶段签收；它只阅读 frozen review packet，输出结构化 findings。主 agent 保留唯一裁决权：合并 findings，决定 accepted / rejected / deferred / backflow，更新 canonical artifacts，重新跑 gate，并在涉及人类决策时按 Human Decision Participation Gate 逐条询问用户。

硬规则：

- 不把 PRD/AIP/草案、Atomic Issue、verification、acceptance 或代码实现分派给 subagent 生成或修改。
- 不允许 subagent 修改文件、签发 receipt、锁定 DEC/C/VER/T、决定 ready/done/accepted，或把 finding 直接写成 canonical decision。
- 需要 review 时，主 agent 必须先生成当前阶段 canonical artifacts、context pack、decision-surface-discovery / stress tests / projection matrix（如适用），再构造 frozen review packet；不得让 reviewer 自由读取聊天历史并从零设计需求。
- reviewer 返回后，主 agent 必须同步等待全部 required reviewer final findings，再处理当前 gate；等待期间不得签收阶段、不得进入下一阶段、不得 admit 后续 Txxx、不得用部分输出通过 gate。使用 30–60 秒 `wait_agent` 轮询并保持用户可见状态更新，累计等待窗口至少 30 分钟；窗口内未返回时不得中断 reviewer、缩小 review scope、改用 main-local、自行补 reviewer 结果、刷新 gate 或继续下游，只能继续轮询。
- 等待 reviewer 期间，frozen review packet 和 reviewer 要审的 canonical artifacts 必须保持冻结。主 agent 不得修改 `multi-perspective-reviews/<stage>.yaml`、`atomic-issue-quality-review.yaml`、`task-semantic-review.yaml` 的 reviewer/finding/disposition 占位结构，不得修改本轮 reviewer 输入覆盖的 PRD/AIP/plan/contracts/verification/tasks/acceptance artifact；只能做不改变 reviewer 输入和结论的只读观察或等待状态记录。
- 只有 reviewer 已经超过 30 分钟仍无 final status，主 agent 才能选择继续等待、关闭后以相同 frozen packet 和同等 review scope 重启 reviewer，或把当前 review gate 标为 `blocked` 并记录具体原因。超时不是降低 gate 标准、缩小审查范围、要求“只审最关键 artifact”、跳过 finding、伪造 reviewer evidence 或进入下一阶段的理由。
- review artifact 必须记录 `subagent_execution`：agent id、agent type、spawn_agent evidence、wait_agent completion/final status、final message digest/source、close_agent evidence 或明确 reused-live reason。缺任一项时，`reviewer_type=readonly-subagent` 不生效，不能通过 gate。当前本地 validator 只能验证字段、packet/final digest 和 hash 链完整性，不能独立证明 orchestrator 事件真实性；不得把 schema 通过描述成“已由机器证明真实 spawn/wait”。真实性仍以当前会话的 orchestrator event 为准，未来接入平台签名 receipt 后再升级为机器可验证信任根。
- reviewer finding 必须包含 evidence path / violated rule / missing decision or contract / why current artifact is insufficient / suggested backflow stage / human_decision_required。只有感觉判断、重写方案、无证据建议或“整体看起来可以”的输出不能作为 gate 依据。
- 主 agent 可以驳回 reviewer finding，但必须在 `multi-perspective-reviews/<stage>.yaml`、`atomic-issue-quality-review.yaml` 或 `task-semantic-review.yaml` 中记录 rejected reason 和反证据；不能静默忽略 blocker。
- 不允许用 main-local fallback、主线程自审、deterministic command、rubric 自查或用户口头确认替代只读 reviewer。工具策略、用户授权、环境限制或 subagent 不可用时，当前 review gate 必须保持 `blocked`，记录阻塞原因，并等待真实只读 reviewer 可用后重跑；不得签收阶段、不得继续下游。
- 不允许“没有实际启动 subagent，但 review artifact 里按 schema 写 readonly-subagent”。这属于伪造 review 证据，等同 main-local fallback。
- 需要并行探索时，仍优先用 deterministic command、`rg`、脚本、测试、浏览器自动化和 validator。subagent 只用于人类研发评审式的多视角审证据，不用于替代确定性检查。
- Gate failure repair / validator error triage 期间不得启动 subagent。`workflowctl.py validate/pass-stage`、`validate_artifacts.py`、`atomic_issue_compile.py` 或 mock validator 失败后，主 agent 必须本地读取 validator 输出、相关 artifact 和脚本规则，修复 canonical artifact，再重跑 gate。只有当当前阶段 artifact 已修到 frozen candidate，且需要执行 Controlled Multi-Perspective Review / Atomic Issue quality review / task-local semantic review 时，才允许启动只读 reviewer。
- 不得因为 gate failure 内容复杂、错误很多、需要定位 validator 规则、或需要补 contract/PRD/AIP/task artifact，就启动 explorer/worker/subagent 分担修复。缺 review artifact 时，先由主 agent修复阶段产物和 frozen packet，再启动 reviewer；不能让 reviewer 帮忙生成或修 artifact。

Subagent lifecycle hygiene：

- 启动任何 reviewer 前，主 agent 必须先关闭已完成、已裁决、或不再需要的 subagent；不得让完成的 reviewer 长时间占用 agent slot。
- 每轮 review 结束后，主 agent 写入 findings/disposition 并关闭对应 subagent；再进入下一阶段或下一批 review。
- 若启动 reviewer 时提示 subagent 池满，先关闭已完成/不再需要的 agents 后重试一次。若仍无法启动，当前 review gate 必须 `blocked`，阻塞原因记录为 `subagent pool exhausted after cleanup` 或等价具体原因；不得改用 main-local fallback。
- subagent 池满不是降低 gate 标准、跳过 review、改用 worker 修 artifact、或继续下游阶段的理由。

reviewer 的输入必须是阶段 frozen packet，而不是开放问题。每次启动必须显式给出：

| Input | Required content |
|---|---|
| Stage under review | 当前阶段和 gate 名称，例如 PRD readiness、AIP mechanism design、cross-module contract、atomic task planning |
| Review objective | 本 reviewer 只负责的视角，例如 product semantics、architecture/owner、verification/acceptance |
| Frozen artifacts | 允许阅读的 canonical artifact 路径、context pack、sidecar、相关矩阵和 validator 输出 |
| Locked upstream facts | 已锁定 PDEC/ADEC/DEC/C/VER/T 摘要，以及禁止重新解释的内容 |
| Reviewable scope | 本轮允许质疑的 surface、owner、contract、proof、task boundary |
| Non-reviewable scope | 不允许重写的产品方向、已锁定决策、无关模块、未授权代码实现 |
| Finding schema | `finding_id`、`severity`、`violated_rule`、`evidence_paths`、`missing_decision_or_contract`、`suggested_backflow_stage`、`human_decision_required` |
| Blocking criteria | 哪些 finding 阻塞当前 gate，哪些只是 non-blocking risk |

Decision surface discovery 和 Generative Surface Stress Tests 是 review 的前置输入，不是被 subagent 替代的工作。主 agent 必须先用 experience-shaped triggers 和 consumer enumeration / mutation chain / invariant breakage / lifecycle completeness / reverse acceptance 生成 candidate surfaces、Surface Obligation Projection Matrix 和 downstream DEC/C/VER/T 映射；reviewer 只审这些 surface 是否漏、是否 owner 错投、是否抽象关闭、是否缺 negative assertion 或 verification。

阶段级 multi-perspective review 配置：

是否需要 review、初审/修复轮最少人数和上限以 `workflow-state-machine.yaml#review_policy` 为唯一机器事实源。`source-intake` 不单独启动 subagent review，其 source/current-state 证据由 PRD/readiness reviewer 消费。`initial` 使用完整视角；`semantic-repair`、`projection-repair`、`format-repair` 只复审受影响视角，最少 1 人，不因 frozen hash 的机械变化自动召回全部 reviewer。修复轮必须在 `repair_context` 固定 immutable `previous_review_ref`、触发 finding/validator failures、实际变更 artifacts 和缩窄视角理由；缺任一项按 initial review 处理，不能只改 `review_kind` 绕过初审人数。

| Gate | Default reviewer count | Required reviewer perspectives | Frozen input focus | Blocking output |
|---|---:|---|---|---|
| Decision Surface Discovery 后 | 3 | Product semantics、Architecture/owner、Verification/acceptance | `decision-surface-discovery.md`、Generative Surface Stress Tests、Surface Obligation Projection Matrix、Decision Registry、Semantic Consumption Matrix | 漏 surface、stress test 未实际运行、provider/consumer/mock owner 缺失、negative assertion 或 verification 缺失 |
| PRD / requirement readiness | 2 | Product semantics、Legacy/current behavior | source-intake、code-scope/current product understanding、PRD draft、PDEC、acceptance scenarios | 用户场景/对象/状态/错误/权限/兼容未决，PDEC 未逐条锁定 |
| AIP / mechanism design | 3 | Architecture/owner、Runtime/external mechanism、Verification | AIP/propose、engineering propose intake、external research、mechanism-design-model、ADEC | 方案只有方向没有机制，MECH/OPSEQ/EXTAPI/RMM/RLM/FCM/MIM 未闭合 |
| Code archaeology / migration diff | 2-3 | Legacy invariant、Architecture boundary、Compatibility | code-scope-discovery、archaeology artifact、migration diff、旧代码 anchors | 旧字段/状态机/consumer/readback/default/compat invariant 未进入 DEC/C/VER/T |
| Cross-module contract | 3 | Provider-consumer owner、State/lifecycle/event、Verification | module graph、contracts、surface obligation projection、semantic consumption matrix | frontend 关闭 backend、mock 关闭 production、DB readback 关闭 provider write、contract ID-only |
| Atomic task planning 前 | 2 | Atomic boundary、Semantic carrier/projection | task-planning 输入、Task DAG、owner slice、semantic carriers、atomic-issue-packets draft | owner slice 错、task 边界策略错、carrier/projection 缺失、task DAG 回流错误 |
| 每个 task pass 前 | 1 | Task-local semantic reviewer | 当前 Txxx、当前 diff、验证日志、validate-task-diff 输出 | diff 偏离 Txxx、verification 不证明 obligation、allowlist 越界、需要新决策 |
| Mock/product acceptance 前 | 2-3 | Product acceptance、Mock/runtime proof、Frontend interaction | acceptance-context-pack、mock execution、browser/runtime evidence、verification log | smoke 替代语义验收、fixture identity 漂移、生产 adapter 未证明、mode 泄漏 |

人数按风险上限控制：普通中等需求阶段级 review 2 个 reviewer，高风险大需求 3-4 个 reviewer，跨 runtime / 跨云资源 / 跨前后端 / 有 mock acceptance 的特别复杂需求最多 5 个 reviewer；任务级 review 固定 1 个 reviewer。人数不能靠凑数提高可信度，每个 reviewer 必须有互斥视角和独立 blocking criteria。

阶段级 review findings 写入 `multi-perspective-reviews/<stage>.yaml`，例如 `multi-perspective-reviews/prd.yaml`、`multi-perspective-reviews/contract.yaml`。`atomic-task-planning` 的阶段级 review 只审输入面、owner/projection 方案、Task DAG 和 packet draft；编译后的每个 Txxx 是否 validator-driven、过宽、owner 错投或压缩语义，必须用专用 `atomic-issue-quality-review.yaml` 审查。task pass 前的语义审查继续写入 `task-semantic-review.yaml`。

`atomic-execution-sdd` 的只读 reviewer 仍是内置同步阻塞 gate：当前 Txxx 完成实现、验证和 `validate-task-diff` 后，必须启动一个只读 reviewer 对照当前 Atomic Issue、当前 diff 和验证日志找 `contract-deviation`、`verification-insufficient`、`behavior-bug`、`diff-scope-risk`。该 reviewer 不能改代码、不能生成/修改 artifact、不能签发 receipt、不能决定 done。主 agent 必须复核 findings，修复或 backflow，并把最终 review 结果写入 `task-semantic-review.yaml`；`workflowctl.py pass-task` 会拒绝缺失、阻塞、过期、或 reviewer_type 不是 `readonly-subagent` / `read-only-subagent` 的 review 记录。

默认 review / audit lane：

| Stage | Review / audit lane | Focus | Blocking output |
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

## Context Pack Experiment

本实验版把“跨阶段上下文恢复”作为主线机制，但只放在信息密度高、最容易因压缩丢语义的边界。Context pack 不是二次 PRD，不追求全文搬运；它是下一阶段输入索引 + 必要语义摘录 + 禁止重新解释的约束。

通用规则：

- 进入下游阶段前，主 agent 必须重新读取上游 canonical artifacts，生成或更新对应 context pack / context section。
- context pack 必须只摘录下游阶段执行所需语义：source IDs、locked decisions、module/contract facts、action route、verification expected result、Not Run / blocker、禁止事项。
- 如果语义只存在于聊天上下文、压缩摘要或记忆中，而没有落盘 source，必须回流补 artifact；不得写入下游产物。
- context pack 必须可被 validator/rubric 审计；不能只有 ID、标题或一句摘要。
- 对普通小阶段，优先在当前 artifact 内写 `Context Rehydration` 章节；只有关键边界才使用独立文件。

关键边界：

| Boundary | Required context artifact | Purpose | Blocks next stage when missing |
|---|---|---|---|
| PRD/AIP -> design/archaeology | `design-context-pack.md` 或 `plan.md#Design Context Rehydration` | 把 PRD/AIP 决策、当前产品/代码理解、scope/non-goals 转成设计和考古输入 | yes |
| archaeology/design -> frontend/cross-module contract | `contract-context-pack.md` 或 `plan.md#Contract Context Rehydration` | 把旧代码事实、字段矩阵、mode 差异、action route、模块边界转成契约输入 | yes |
| contracts/verification -> atomic task planning | `atomic-planning-context-pack.md` | 把 REQ/SCN/DEC/C/VER/MIG、模块契约、action route、mock/runtime、verification expected result 转成 Atomic Issue 输入 | yes |
| implementation -> mock/product acceptance | `acceptance-context-pack.md` 或 `mock-acceptance.md#Acceptance Context Rehydration` | 把实际 diff、运行产物、API/route、mock 边界、freshness、REQ/SCN/VER 验收范围转成验收输入 | yes |

每个 context pack 至少包含：

| Section | Required content |
|---|---|
| Source Rehydration Ledger | 读取了哪些 canonical artifacts、路径、更新时间、是否参与下游阶段 |
| Semantic Index | 下游必须消费的 REQ/SCN/PDEC/DEC/C/MIG/VER 语义摘录 |
| Decision And Constraint Pack | locked decisions、禁止解释、N/A 和 Not Run 风险 |
| Boundary-Specific Pack | 本边界需要的 module/action/contract/mock/runtime/verification facts |
| Downstream Coverage Map | 每条语义进入哪个下游 artifact/section/issue/verification |

缺少 context pack 时，不得生成下游 canonical artifact；context pack 自身不完整时，必须回流到上游 artifact，而不是在下游凭记忆补。

### Context Pack Stage Binding

Context pack 不是入口 skill 的可选建议。下游阶段必须把对应 context pack 当作输入门禁：

| Context pack | Consuming stages | Block condition |
|---|---|---|
| `design-context-pack.md` 或 `plan.md#Design Context Rehydration` | `new-feature-design`, `code-archaeology-sdd` | 缺失、未读取 PRD/AIP/source/decision、语义只有 ID 或摘要 |
| `contract-context-pack.md` 或 `plan.md#Contract Context Rehydration` | `frontend-contract-design`, `cross-module-contract-sdd` | 缺失、未包含模块边界/旧代码事实/字段矩阵/mode/action route/contract candidates |
| `atomic-planning-context-pack.md` | `atomic-task-planning` | 缺失、未覆盖 REQ/SCN/PDEC/DEC/C/MIG/VER、verification expected result、task constraints |
| `acceptance-context-pack.md` 或 `mock-acceptance.md#Acceptance Context Rehydration` | `mock-acceptance-gate`, `product-acceptance-review` | 缺失、未覆盖实际 diff、task verification、runtime freshness、mock/real boundary、Not Run |

如果 consuming stage 的 skill 没有显式声明该 context pack，仍以本入口规则为准：主 agent 必须先生成 context pack，并通过 deterministic validator / rubric / Controlled Multi-Perspective Review 审计完整性，再运行该阶段。Controlled Multi-Perspective Review 必须由只读 reviewer 执行，不能 main-local fallback。

### Session Resume Identity Gate

这个 gate 的优先级高于 Repo Isolation Gate。每次上下文压缩恢复、新 session 继续、当前目录不确定、或用户说“继续/监控/看看当前执行”时，必须先读取 `workflow-workdir.md` 判断当前执行身份；若当前 cwd 中没有该文件，再判断是否已有同一需求的 active change，而不是直接创建新 worktree。

必须先执行只读发现：

- `git worktree list`
- 优先读取已知 change 的 `specs/changes/<change-id>/workflow-workdir.md`
- 在当前 repo 和 `${CODEX_HOME:-$HOME/.codex}/worktrees/*/<repo-name>` 下查找 `specs/changes/*/workflow-workdir.md` 和 `specs/changes/*/workflow-state.yaml`
- 同步读取候选 change 的 `workflow-workdir.md`、`source-intake-ledger.md`、`proposal.md` / `spec.md`、`plan.md` 中的 Repo Isolation Gate、Workflow Mode、source title/doc id、base branch、base commit、branch name 和 worktree path

恢复判定规则：

- 如果 `workflow-workdir.md` 记录的 worktree/change-id 与当前 cwd 不一致，必须以 `workflow-workdir.md` 为准切回，或报告 mismatch blocked；不得按当前 cwd 重建。
- 如果发现候选 change 的 source/doc title、base branch、base commit、branch/worktree 证据与当前用户需求匹配，必须切回该 worktree 和 change-id，运行 `workflowctl.py verify-resume`；不得创建新的 worktree、branch 或 change-id。
- 如果当前 cwd 不是该 worktree，这只是恢复定位问题，不是重新隔离理由。必须使用已登记的 Worktree path 继续。
- 如果存在多个候选 change，选择最近 `workflow-state.yaml` / `plan.md` 修改时间且 source/doc title 匹配的 active change；无法确定时报告候选清单并停止，不得自行开新 worktree。
- 只有在确认没有 active change，或用户明确说“重新开始/废弃旧执行/从头新建”，才允许进入 Repo Isolation Gate 创建新 worktree。

恢复结果由 `workflow-events.yaml#resume_verified` 持久化，不重复写入 source/plan 等语义 artifact。如果这个 gate 没有通过，不得读取业务代码、生成新 artifact、进入任务规划或实现。

### Repo Isolation Gate

当用户要求从指定 base branch 全新开始、禁止参考本地其他分支、或目标仓库已有多个 worktree/branch 时，必须先执行 Repo Isolation Gate。未通过时不得读取目标仓库代码、生成 PRD/AIP/design/tasks 或实现。

必须落盘到 `source-intake-ledger.md` 或 `plan.md#Repo Isolation Gate`：

| Item | Required content |
|---|---|
| Target repo | 仓库名、远端 URL、目标目录 |
| Base branch | 用户指定 base branch，例如 `<user-specified-base-branch>` |
| Base commit | 创建 worktree 后的 `git rev-parse HEAD` |
| UID | 使用 `uid` / `uuidgen` / 时间戳生成的唯一后缀 |
| Worktree path | 新 worktree 绝对路径，必须包含 UID，避免和已有 worktree 冲突 |
| Branch name | 新分支名，必须包含 `codex/` 前缀和 UID，避免和已有分支冲突 |
| Forbidden sources | 本地其他分支、其他 worktree、未授权 patch、历史实现分支 |
| Allowed sources | 当前 worktree、用户提供 source、远端/官方文档、明确允许的参考 AIP/文档 |
| Audit command | `git worktree list`, `git branch --show-current`, `git rev-parse HEAD`, `pwd` 等证据 |

硬规则：

- Repo Isolation Gate 只用于没有 active change 的全新需求启动。它不能在上下文压缩恢复、已有 change 继续执行、或当前 cwd 不确定时覆盖 Session Resume Identity Gate。
- 创建 worktree 前必须检查已有 worktree/branch，分支和目录名使用 UID 防冲突。
- 不得从当前新 worktree 之外的本地同仓库目录读取、grep、diff、copy 代码。
- 不得用本地其他分支代码作为 code archaeology evidence；只能读取当前 base branch 新 worktree 中的代码。
- 允许读取用户明确指定的外部文档或远端参考，例如公开 AIP 文档；必须登记为 source，并标注它是 design reference，不是目标仓库现有实现。
- 若发现 artifact、Atomic Issue 或代码引用 forbidden source，必须创建 Backflow Invalidation Matrix，标记受影响 PRD/AIP/DEC/C/T/VER pending-rewrite，重新从隔离 worktree 读取。

### No Shortcut Interpretation

用户说“继续推进”“直到做完”“中间不要中断”“你推荐决策即可”“后续应该没有卡点”，只能解释为：

- AI 可以在被授权范围内锁定推荐的产品或工程决策。
- 可修复 gate failure 默认 backflow 修复后继续。
- 不需要在每个可自动修复问题处停下来询问用户。

这些话不代表允许跳过 PRD、AIP、readiness、code archaeology、frontend contract、cross-module contract、verification matrix、context pack、rubric、validator 或 Atomic Issue 物化门禁。任何缺失 artifact 仍必须 blocked/backflow。

### AIP Creation Hard Gate

大需求缺少 AIP 时，`aip-template` 不是可选参考，而是必须产出 workflow-owned AIP。未产出并通过 AIP readiness 前，不得进入 design、code archaeology、contract、verification、atomic task planning 或 implementation。

生成 `aip.md` 前必须读取 `${CODEX_HOME:-$HOME/.codex}/skills/aip-template/references/steering.md`。`aip.md` 必须保留 AutoMQ AIP 标准模板结构；工程完整度内容只能填入对应章节或作为子表扩展，不能用自定义 engineering outline 替换模板标题。`writing-style` 只在生成或改写 `aip.md` 正文时使用，不得用于 PRD、readiness review、plan、YAML sidecar、Atomic Issue、代码或其它阶段产物。

必须产出：

```text
specs/changes/<change-id>/aip.md
specs/changes/<change-id>/decision-reviews/aip-decisions.md
```

`aip.md` 必须包含这些模板标题，且顺序与 `aip-template` 一致：

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

模板章节内还必须覆盖这些工程完整度语义：

| Section | Required content |
|---|---|
| Background / problem | 产品背景、目标用户、为什么现在做 |
| Goals / non-goals | 工程目标、非目标、边界 |
| Selected architecture | 推荐架构、核心模块、控制流/数据流 |
| Rejected alternatives | 重要反选方案和拒绝原因 |
| Interfaces | OpenAPI / 内部 API / Terraform / DB / event / task / frontend contract 输入 |
| Data/state/task model | 数据模型、状态机、异步任务、变更记录 |
| Deployment/cloud/IAM | 云资源、K8s/ASG/EC2、权限、网络、安全组、派生配置 |
| Observability | metrics/logs/events/alerts/dashboard/runbook |
| Compatibility/rollback | 存量、升级、回滚、旧 API/字段/配置 |
| Verification strategy | 单测、集成、mock、browser、runtime/cloud evidence、Not Run |

随后必须运行 `aip-readiness-review`，生成 Engineering Propose Extraction、Current Architecture Understanding、Engineering Decision Completeness Gate 和 AIP Local Audit Report。任何 `Blocks next stage=yes` 行阻塞后续阶段。

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

### Derived Atomic Planning Invalidation Gate

Atomic Issues 是从上游 canonical artifacts 编译出来的派生产物，不是源事实。`tasks.md`、`task-dag.yaml`、`atomic-issue-packets.yaml`、`atomic-issues/Txxx.md`、`atomic-issue-quality-review.yaml` 和 `multi-perspective-reviews/task-planning.yaml` 都必须服从上游 PRD/AIP/readiness/design/archaeology/frontend-contract/contract/verification 的最新签收结果；若本 change 存在 migration 阶段 receipt，migration 也作为 optional consumed upstream 纳入 task-planning hash。

一旦 `task-planning` 之后任一已签收上游阶段被重写、重签或 receipt hash 变化，默认动作是让 `task-planning` 整体失效并重新生成任务规划产物。不得把已有 Txxx 当成资产修修补补，除非先写出 `Task Planning Impact Proof` 证明影响严格局部。

允许 local reseal 的条件必须全部满足：

- 上游变更只影响已存在的同一个 Txxx，不新增、删除、拆分、合并任何 REQ/SCN/PDEC/ADEC/DEC/C/MIG/VER/UI/ARCH/DESIGN semantic carrier。
- provider owner、consumer owner、mock/acceptance owner、primary module、files_to_change 模块边界都没有变化。
- Task DAG、predecessor/successor、parallel group、verification gate 顺序没有变化。
- verification loop、expected result、negative assertion、Not Run/fallback risk 没有变化。
- `Task Planning Impact Proof` 明确列出 changed upstream object、affected Txxx、unchanged boundary/owner/DAG/verification 的证据路径。

任一条件不满足，必须重新生成 `task-dag.yaml`、`atomic-issue-packets.yaml`、`tasks.md`、`atomic-issues/Txxx.md`、`atomic-issue-quality-review.yaml` 和 `multi-perspective-reviews/task-planning.yaml`，并重新运行 `atomic_issue_compile.py --check`、`workflowctl.py validate task-planning`、`workflowctl.py pass-stage task-planning`。只把新 DEC/C/VER ID 塞进旧 Txxx、补关键词、改 packet 表头或保留旧 DAG，都属于 violation。

`workflowctl.py pass-stage task-planning` 必须记录它消费的上游 `stage_receipts` hash。任何上游 receipt hash 变化都会使 task-planning receipt stale；下游不得继续执行旧 Atomic Issues。重新签收 task-planning 前，必须在 `atomic-planning-context-pack.md` 写入以下二者之一：

- `Task Planning Regeneration Evidence`：证明已重新生成 task-planning 派生产物，列出 regenerated artifacts、source upstream receipt hashes、compiler/review/gate evidence。
- `Task Planning Impact Proof`：证明允许 local reseal，列出 changed upstream object、affected Txxx、unchanged boundary/owner/DAG/verification 的证据路径。

没有上述证据时，`pass-stage task-planning` 必须失败，不能把旧 Txxx 重新封存。

task-planning 修复期间还必须维护 `task-planning-repair-ledger.yaml`。任何 compiler、workflowctl 或 readonly subagent review blocker 一旦被修复，都要登记为稳定 `failure_signature`，写清 `owner_invariant`、`forbidden_regression` 和可重复 `regression_checks`。每次 regenerate `task-dag.yaml`、`atomic-issue-packets.yaml`、`tasks.md` 或 `atomic-issues/Txxx.md` 后，必须先运行 ledger 中所有 active/fixed regression checks；如果已修复签名再次出现，不能继续做关键词替换或局部补字段，必须把当前阶段标为 generator invariant failure，回到 owner assignment、carrier projection 或 task split 修复后再重新生成。

如果同一类 task-planning failure 在同一 change 中第二次出现，或 readonly reviewer 指出的是生成器/owner projection/consumer-provider 分账缺口，必须同时提升为 `known_regressions`。`known_regressions` 不是所有需求的必填清单，但一旦当前需求命中，就必须写稳定签名、owner invariant、禁止回归 artifact 位置和可重复 regression check。常见需要提升的签名包括：`copied_to` 把 frontend/consumer task 误标成 provider/stateful owner、自动 fallback projection 把全局 REQ/SCN 当 dense carrier 塞进多个 task、无 owner 列的 frontend matrix 被错误过滤、consumer visibility/assumption 被写成 provider state machine implementation。

compiler 触发词只能作为风险提示，不能替代 owner 判定。`task`、`payload`、`runtime`、`readback`、`resource/provenance`、`provider` 等泛词单独出现时，不得诱导 AI 把非 owner task 改成 runtime/persistence/managed-resource owner，也不得诱导 AI 为了过 gate 写同义词。正确动作是查看 typed surface/carrier/contract owner、Task DAG 和 `files_to_change`，必要时修 compiler 规则或回流 owner projection。

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

Atomic Issue 的大小限制是可读性保护，不是语义压缩许可。执行层必须保留当前 owner slice 所需的 source、decision、contract obligation、negative assertion、files_to_change、verification 和 failure/backflow 语义。若完整承载后文件过大或难以阅读，正确动作是回流 `atomic-task-planning`，按 provider owner、operation surface、semantic type、verification loop 或 mock/production boundary 拆成多个 Txxx；不得把具体 owner、字段、状态、错误、验证压缩成 `mode-aware`、`support`、`baseline`、`stable shape`、`provider proof` 等抽象词，也不得只保留全局 artifact 引用。

只有在仍满足 single primary module、single operation surface、single semantic type family、single short verification loop，且没有多个 provider owner 或多个独立 mutation lifecycle 时，才允许适度放大该 Atomic Issue 的 size budget。放大 budget 必须在 packet 中写明原因和仍然原子的证明；如果出现多个 provider owner、多个 operation surface、多个 verification family、或 mock/acceptance 与 production side effect 混在一起，必须拆分任务，不能靠放大文件上限解决。

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

如果 context pack 无法覆盖所有 required upstream object，或无法说明每个 dense semantic carrier 会进入哪些 Txxx packet section，`atomic-task-planning` 必须 blocked 并回流补 artifact；不得用“记得需求里说过”补齐。必须由主 agent 审计 context pack 是否完整，且不能用任何并行 agent 替主 agent 生成 context pack 或最终 Atomic Issues；只读 reviewer 只能审查 frozen context pack 并输出 findings。

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

每个 carrier 必须在 `semantic-objects.yaml`、`contracts.yaml` 或 `task-dag.yaml` 中落为 `semantic_carriers`，并在 `atomic-issue-packets.yaml` 对应 Txxx 中出现。`workflowctl.py validate pre-execution` 和 `atomic_issue_compile.py --check` 失败时，不得把 `tasks.md` 标为 ready。

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

- 模板：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/*.md`
- 输入账本：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/source-intake-ledger.md`
- 代码范围发现：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/code-scope-discovery.md`
- 用户决策交互：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/user-decision-interaction.md`
- 工程 propose：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/engineering-propose-intake.md`
- 语义消费：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/semantic-consumption-matrix.md`
- 验证可行性：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/verification-feasibility.md`
- 版本分支对齐：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/version-branch-alignment.md`
- Rubric 评分：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/artifact-rubric-scorecard.md`
- 执行 DAG：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/task-dag.md`
- 回流失效：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/backflow-invalidation.md`
- Rubric：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/references/artifact-review-rubric.md`
- 正反例：`golden-atomic-issue.md` / `bad-atomic-issue.md`
- 结构化 sidecar：contextpack 使用 `${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/templates/workflow-state-contextpack.yaml`，其余为 `semantic-objects.yaml`、`contracts.yaml`、`verification.yaml`、`task-dag.yaml`、`backflow.yaml`、`atomic-issue-packets.yaml`
- 阶段级结构化校验：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py`
- 结构与语义门禁：`${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/validate_artifacts.py`

这些是 skill runtime 资源，不是目标仓库内置脚本。不得在目标 repo 内寻找 `workflowctl.py` / `validate_artifacts.py` 来判断它们是否可用；目标 repo 没有这些脚本不是降级理由。必须先用上面的绝对路径运行。只有绝对路径文件不存在或不可执行，才算 skill runtime 工具缺失；此时只能 blocked 并报告，不能用 checklist 自审替代，也不能进入实现。

进入 `atomic-execution-sdd` 前，必须使用上述资源完成模板化、rubric review、结构化 sidecar、`workflowctl.py validate pre-execution` 和 `validate_artifacts.py` 结构校验。

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
| 产品决策 | 默认必须由用户逐条确认；只有用户明确授权 AI 按推荐方案锁定时，才可不进行人工等待；但仍必须记录 prompt、授权依据、决策文档、Decision Registry、Semantic Consumption Matrix，并通过 validator gate；PRD 完成后不得残留 open product decision |
| 工程决策 | AIP 阶段默认必须由用户逐条确认，除非用户明确授权 AI；设计、考古、迁移、契约、验证等后续阶段在未进入 human participation mode 时可由 AI 在上层产品约束下自主决策；一旦用户声明参与决策，所有阶段工程决策都必须逐条确认；任何工程决策不得改变产品语义 |
| 实现决策 | 不允许；执行阶段发现新决策时暂停并回到对应阶段 |

每个阶段只要产生或修改决策，就必须同时产出独立阶段决策文档：

```text
specs/changes/<change-id>/decision-reviews/<stage>-decisions.md
```

并同步更新 `plan.md` 的 Decision Registry 和 Decision Document Index。

如果环境有 `lark-cli` 写权限，必须把阶段决策文档同步到飞书，并把 URL 回写到 Decision Document Index；如果失败，记录失败原因和后续命令。

阶段决策文档不是可选补充。它是防止“决策藏在段落里”“上下文压缩后丢失”“实现阶段重新猜”的强制 artifact。

决策文档必须逐决策展开。禁止把多个决策合并成 `PDEC-001..022`、`ADEC-001..004` 或“相关决策同上”这种摘要段。每个决策都必须独立记录问题、最终选择、反选方案、理由、产品约束对齐、影响模块、验证方式和下游 Atomic Issue 影响。

如果某个决策由人类确认，还必须记录 Human Decision Prompt、用户原始响应或摘要、确认时间、最终状态，以及是否授权后续同类决策由 AI 锁定。批量确认、默认沉默确认、或没有 prompt 记录的 “user-confirmed” 状态无效。

## 阶段地图

本 skill 只负责路由和闭环，不替代阶段 skill。每一行的 `Exit gate / receipt` 都是进入下一阶段前的强制动作。

`plan.md` 是跨阶段工作副本，不能被多个 receipt 直接封存。对会写 `plan.md` 的阶段，`pass-stage` 自动生成不可变的 `stage-snapshots/<stage>-plan.md` 并将其写入该阶段 receipt；下游只把已签收 snapshot 作为上游语义输入，同时可继续扩展 `plan.md`。修改已签收 snapshot 必须失败；上游语义变更必须先 backflow/reopen，再重签并替换 snapshot。

| 阶段 | Skill | 产物 | 目的 | Exit gate / receipt |
|---|---|---|---|---|
| 输入登记 | source intake ledger / requirement intake | `source-intake-ledger.md` | 登记用户输入、source trace、冲突、授权范围和初始决策面输入 | `validate source-intake` + `pass-stage source-intake`，确认 `stage_receipts.source-intake` |
| 产品定义 | `product-requirement-design` | `proposal.md` / `spec.md` / `decision-reviews/prd-decisions.md` / PDEC | 锁定用户视角的功能、状态、错误、权限、验收 | `validate prd` + `pass-stage prd`，确认 `stage_receipts.prd` |
| AIP 编写 | `aip-template`；`writing-style` 仅用于 `aip.md` 正文 | AIP 文档 / `decision-reviews/aip-decisions.md` | 当 AIP 缺失时，按 AutoMQ AIP 模板产出设计文档；只有生成或改写 `aip.md` 正文时应用用户写作风格 | `validate aip` + `pass-stage aip`，确认 `stage_receipts.aip` |
| AIP 门禁 | `aip-readiness-review` | blocking questions / `decision-reviews/aip-decisions.md` / DEC | 锁定工程方案、接口、兼容、观测、验证策略 | 若修改 AIP/ADEC，重跑 `pass-stage aip`；随后进入 readiness |
| 总门禁 | `requirement-readiness-review` | readiness verdict | 确认产品和 AIP 都足够进入工程阶段 | `validate readiness` + `pass-stage readiness`，确认 `stage_receipts.readiness` |
| 决策账本 | `decision-registry` | `plan.md` Decision Registry | 贯穿全流程，禁止实现阶段临时决策 | 随当前 owner 阶段一起签收；修改已签收决策账本会使对应阶段 receipt 失效 |
| 新设计 | `new-feature-design` | `spec.md` / `plan.md` / `decision-reviews/design-decisions.md` | 设计理想模块边界、领域模型、场景 | `validate design` + `pass-stage design`，确认 `stage_receipts.design` |
| 旧代码考古 | `code-archaeology-sdd` | `plan.md` archaeology / `decision-reviews/archaeology-decisions.md` | 显式化旧系统事实、隐式约束、pattern、框架语义 | `validate archaeology` + `pass-stage archaeology`，确认 `stage_receipts.archaeology` |
| 差异迁移 | `migration-diff-analysis` | `plan.md` migration / `decision-reviews/migration-decisions.md` | 比较旧/新语义，决定 delete/keep/modify/add | `validate migration` + `pass-stage migration`，确认 `stage_receipts.migration` |
| 前端契约 | `frontend-contract-design` | `spec.md` / `plan.md` / `decision-reviews/frontend-decisions.md` | UI 字段、状态、交互、i18n、权限具体化 | `validate frontend-contract` + `pass-stage frontend-contract`，确认 `stage_receipts.frontend-contract` |
| 跨模块契约 | `cross-module-contract-sdd` | `spec.md` / `plan.md` contracts / module contract graph / `decision-reviews/contract-decisions.md` | 锁定 N2 语义约束和模块 consumed/provided contract | `validate contract` + `pass-stage contract`，确认 `stage_receipts.contract` |
| 验证矩阵 | `verification-matrix` | `plan.md` / `tasks.md` / `decision-reviews/verification-decisions.md` | 将每个需求/契约/迁移映射到证明方式 | `validate verification` + `pass-stage verification`，确认 `stage_receipts.verification` |
| 原子任务 | `atomic-task-planning` | `tasks.md` + `atomic-issue-packets.yaml` + `atomic-issues/Txxx.md` + `decision-reviews/task-planning-decisions.md` | 把锁定事实转成 per-task sealed context packet，再编译成可独立派发的 Atomic Issues | 先确认所有上游 `stage_receipts` 有效，再 `validate task-planning` + `pass-stage task-planning`，确认 `stage_receipts.task-planning` |
| 原子执行 | `atomic-execution-sdd` | code + `task-verification-log.yaml` + `task-semantic-review.yaml` + `workflow-state.yaml.task_receipts` | 先 `begin-execution`，每个 task 先 `admit-task`，改完跑 `validate-task-diff`、task-local semantic review 和 `pass-task` | `validate pre-execution` + `validate_artifacts.py` + `begin-execution`；每个 Txxx 用 `pass-task` 签收 |
| 严格 Mock Acceptance | `mock-acceptance-gate` | sealed mock matrix/case artifacts + `mock-acceptance-execution.yaml` + `mock-acceptance.md` / verification log / backflow updates | 把 mock acceptance / repo-specific acceptance runtime 作为一等交付物，用真实前后端用户流程和严格外部契约 mock 验证组合逻辑 | `validate mock-acceptance` + `pass-stage mock-acceptance`，确认 `stage_receipts.mock-acceptance` |
| 产品验收 | `product-acceptance-review` | `acceptance/product-acceptance-review.md` | 部署后用真实浏览器和运行时证据发现产品语义冲突、mode 泄漏、状态不一致和验收缺口 | `validate product-acceptance` + `pass-stage product-acceptance`，确认 `stage_receipts.product-acceptance` |
| 上线收敛评审 | Post-Atomic Launch Convergence Gate | `launch-readiness-review.md` + PR/diff review findings + resolution evidence + human launch decisions | 以生产上线标准评审集成 PR 或等价 diff，区分实现缺口、原子任务缺口、最终上线决策、验收缺口和允许的实现差异 | 关闭所有 launch-blocking findings；`workflowctl.py validate-launch-readiness specs/changes/<change-id>`；当前 `workflowctl.py pass-stage` 不支持该 gate，不得伪造 stage receipt |
| 收敛复盘 | `convergence-retrospective` | retrospective actions | 区分 N2 下限和 N1 可消除缺口，反哺 current/skill | 当前 `workflowctl.py pass-stage` 不支持 retrospective；不得执行 `pass-stage retrospective`。按 `convergence-retrospective` 产物要求记录 actions，并在后续需求中由 source-intake/PRD/AIP 消费 |

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
如果 AIP 已有、接口草案/Terraform/API 设计已有，也一律先视为 Engineering Propose；必须用 `aip-readiness-review` 做 Engineering Propose Extraction、Current Architecture Understanding 和 Engineering Decision Completeness Gate，不能直接当 locked AIP。
如果两者都有但不确定是否可执行，走 `requirement-readiness-review` 做总门禁。

所有入口输入必须先进入 `Source Intake Ledger`。用户提供的 PRD、AIP、飞书链接、issue、补充设计、Terraform/API 草案、历史方案、代码路径、运行时证据，都必须登记读取状态、读取方式、下游映射和冲突。存在 behavior-affecting source 未读或 blocked 时，不得进入设计、契约、任务规划或实现。

PRD normalized 之后、AIP/design 锁定工程方案之前，如果需求涉及云资源、K8s/Helm/Terraform/IAM/network/storage/compute/runtime、第三方 API/SDK、官方协议、autoscaling/scheduling/lifecycle、metrics/logs/events 或 mock acceptance / repo-specific acceptance runtime 外部依赖，必须创建 `specs/changes/<change-id>/external-capability-research.md`。它是 AIP-owned research synthesis，由 AIP receipt 封存，不属于 source-intake receipt；source-intake 只登记其消费的原始 URL、代码、SDK 和用户输入。该文档必须登记外部能力事实、不支持/限制、约束、设计影响和 acceptance 边界。任何影响设计的外部事实必须进入 ADEC/DEC、C、VER、semantic_carrier 和 owner packet，或有 locked N/A / Not Run。没有调研消费闭环时，不得进入 AIP readiness passed、new-feature-design、cross-module-contract 或 atomic-task-planning。

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

使用本实验版时，必须在 `source-intake-ledger.md` 或 `plan.md` 明确写入：

```markdown
## Workflow Mode

| Item | Value |
|---|---|
| Workflow skill | automq-ai-dev-workflow-contextpack |
| Context pack required | yes |
```

缺少该标记时，后续 validator 无法区分普通 workflow 和 contextpack workflow；不得进入任务规划。

必须创建或更新：

```text
specs/changes/<change-id>/source-intake-ledger.md
```

并使用 `source-intake-ledger.md` 模板登记 Source Inventory、Source To Semantic Object Map 和 Source Conflict Matrix。未读输入不能作为事实使用；冲突未决不能进入 Atomic Task Planning。

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

总门禁检查：

- 产品行为是否明确。
- AIP 工程决策是否明确。
- 还有哪些 blocking open questions。
- 是否需要 `spec.md`、`plan.md`、`tasks.md`。

阻塞问题未解决前，不进入考古或实现。

产品需求从几句话或对话开始时，必须先让 `product-requirement-design` 把对话输入登记为 source，输出 Propose Extraction、待决策清单和推荐决策；用户确认或授权 AI 决策后，才能写 locked PRD。

产品需求从已有文档开始时，必须先把原文当作 Propose 标准化成新的 PRD，而不是直接接受原文完整度。标准化必须包含 source trace、gap extraction、decision extraction。

产品需求依赖外部知识时，PRD 只记录“哪些产品语义依赖外部事实”；具体外部能力事实、限制、版本/区域差异、失败语义、mock 来源和设计影响必须写入 `external-capability-research.md`，并在 AIP/design 前消费到 ADEC/DEC/C/VER。

PRD 完成前必须通过 PRD Completeness Gate：Propose extraction、Current Product/Code Understanding、用户/场景、对象模型、scope/non-goals、配置、状态、错误、权限、兼容、运行时生命周期、验收场景和产品决策锁定均完整。任一 `Blocks next stage=yes` 的 incomplete 维度阻塞 AIP、设计、考古、契约、验证和任务规划。

如果用户没有明确授权 AI 做产品决策，必须产出 `User Decision Interaction`，把每个 PDEC 的推荐方案、备选、影响、验证和用户响应落盘。无响应或模糊响应保持 `open`，阻塞 PRD 完成。

PRD 和 AIP 的决策停顿是默认规则：

- `PDEC` 发现后必须逐条发出 Human Decision Prompt，并等待用户确认、改选、授权 AI 锁定或保持 open。没有明确授权时，不得把推荐 PDEC 直接写成 locked。
- `ADEC`、接口/架构/验证/兼容性关键工程决策发现后也必须逐条发出 Human Decision Prompt，并等待用户确认、改选、授权 AI 锁定或保持 open。没有明确授权时，不得把推荐 ADEC 直接写成 locked。
- 若用户在 PRD 或 AIP 阶段一次性说“同意 AI 推荐决策”，只能作为后续授权范围记录，不能回填关闭任何尚未逐条展示、尚未逐条记录 prompt 和用户响应的决策。已生成的待确认决策仍必须一条一条关闭；后续新发现的决策按授权范围判断是否需要再次停顿，但每条 locked 决策仍必须记录其来源、推荐方案、授权依据和影响范围。

### Step 3: 初始化 Decision Registry

调用或维护 `decision-registry`：

- 产品决策登记为 `product`。
- AIP 取舍登记为 `architecture/interface/validation`。
- 后续考古、迁移、契约阶段发现的选择继续追加。
- 任何 `open` 决策都阻塞实现。
- 每个阶段产生的决策都必须同步写入对应 `decision-reviews/<stage>-decisions.md`。
- 工程阶段 AI 自主决策必须标注为 `ai-engineering`，并证明不改变产品语义。
- 人类确认的决策必须标注为 `human-confirmed`；人类明确授权 AI 锁定的决策必须标注授权原文、授权范围和适用阶段。
- 当 `human-decision-participation` 模式启用时，每个阶段新增或修改的决策都必须先进入逐条 Human Decision Prompt；未被确认或授权的决策保持 `open/blocked`，阻塞当前阶段签收。
- 每个决策必须有 `Decision key`，用于识别同一语义问题。
- 必须维护 Decision Consistency Matrix；两个 active locked 决策不能用同一 key 给出冲突结论。
- 修改 locked 决策时必须 supersede 旧决策，并触发 Backflow Invalidation Matrix。

### Step 3.2: 版本分支对齐门禁

如果需求涉及多仓库、控制面/数据面版本、Terraform/IAC、测试编排、控制面应用、kernel 镜像、部署模板或测试环境，必须先使用 `automq-version-branch-alignment` 并产出 `Version Branch Alignment Matrix`。

任何 `Aligned?=no` 且影响实现或验证的项，必须先路由到 owning repo 或作为 blocker；不得进入 atomic task planning。

### Step 3.5: Open Decision Review Doc

如果 workflow 启动后出现阻塞实现的 `open` 决策、blocking question、`needs-human-decision` 契约，不能只把它们留在 `plan.md` 或聊天里。

在 human participation mode 或 PRD/AIP 默认停顿规则下，Open Decision Review Doc 不能替代逐条交互。它只能作为决策背景和索引；真正关闭决策必须通过一条一条 Human Decision Prompt 完成。

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

逐条交互时，每次只取 `decision-review.md` 中下一条未关闭决策生成 Human Decision Prompt。用户确认后，先更新本地决策文档和 Decision Registry，再继续下一条；不得把飞书文档中的多个问题一次性视为已确认。

### Step 4: 选择路径

| 场景 | 路径 |
|---|---|
| 全新能力，旧代码只提供参考 | `code-archaeology-sdd`（只读当前系统/参考 pattern/consumer）→ `new-feature-design` → UI touched then `frontend-contract-design` → `cross-module-contract-sdd` → `verification-matrix` → `atomic-task-planning` |
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

若目标仓库定义了 repo-specific acceptance runtime，planning 可以只读当前 runtime 代码、reference、
验收 adapter、packaged 启动和 fixture graph，用于锁定真实文件路径、模块 owner、fixture 依赖和独立 runtime Atomic Issue；
这些事实必须标为 acceptance-runtime input，不能反向定义生产 API、状态、错误或资源副作用。
实现前不得启动/刷新该 runtime、不得把现有 fixture 输出当作当前需求的验收证据，也不得让业务 owner issue 依赖 mock-only 行为。
真实 frontend/API client/controller/DTO/service/manager/task/repository 必须执行，外部 adapter/API/resource 副作用必须由生产实现触发。
`mock-acceptance-gate`、product acceptance 或 runtime owner task 必须在实现后重新读取当前代码并刷新 freshness evidence；没有后置读取和验收审计时，不得宣布 no-cloud acceptance 完成。

mock acceptance / repo-specific acceptance runtime 路径还必须执行 Controlled Multi-Perspective Review lanes：contract source/drift、frontend user-flow、backend flow DAG、fresh runtime evidence。所有适用 lane 都必须由只读 reviewer 执行；不允许 main-agent fallback audit。未完成任一适用 lane 时，mock acceptance 状态必须是 blocked；不得继续刷新 repo-specific acceptance runtime 作为人工验收入口。任一 lane 输出 P0/P1 blocker 时，必须回流到对应 artifact，不能继续刷新 repo-specific acceptance runtime 做人工验收。

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

### Acceptance Context Rehydration Gate

实现和任务级验证完成后，进入 `mock-acceptance-gate` 或 `product-acceptance-review` 前，必须重新读取落盘实现状态和验收输入，生成 `specs/changes/<change-id>/acceptance-context-pack.md` 或在 `mock-acceptance.md` 中写 `Acceptance Context Rehydration` 章节。

必须重新读取或等价核对：

- `task-verification-log.yaml` / `execution-state.yaml` 的 Verification Log、Not Run、Decision Gaps，以及 `workflow-state.yaml.task_receipts` 的当前 task 状态。
- 所有已执行 Atomic Issues 的 Done Criteria、Provided Contract Obligation、Verification。
- `git diff --stat` / 关键 diff 文件清单，确认实际改动和 Atomic Issues 对齐。
- `verification-matrix.md` 中需要 mock/product acceptance 的 REQ/SCN/VER/C。
- frontend contract、cross-module contract、mock boundary、runtime lifecycle、mode semantic checks。
- packaged/runtime 产物信息：branch/commit、bundle 时间、package/image 时间、PID/port、API/browser smoke evidence；automqbox/CMP 中可包含 acceptance URL 和 freshness evidence。

Acceptance Context Pack 至少包含：

| Section | Required content |
|---|---|
| Implemented issue ledger | Txxx 状态、实际 diff scope、verification log、provided contracts |
| Acceptance semantic index | 必须验收的 REQ/SCN/DEC/C/VER/MIG 和 expected result |
| Runtime freshness pack | branch/commit、bundle/package/process/PID/port、static asset checks |
| Browser/API path pack | 需要打开的 route、action、API method/path/body、success/failure evidence |
| Mock/real boundary pack | 哪些是真实被测代码、哪些是 mock、mock source、drift guard |
| Not Run and cloud boundary | 本地不能证明的 runtime/cloud/no-interruption 能力、owner、Blocks done |
| Handoff QA checklist | 非白屏、CSS/JS/chunk、console/network、submit-flow、progress/change、repo global smoke |

如果 acceptance context pack 无法覆盖 required REQ/SCN/VER/C 或发现 task done 与 verification pending 冲突，必须回流到 atomic execution / verification matrix / contract，而不是进入 mock/product acceptance。

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
| 阶段级 review、执行状态、task receipt、verification log、semantic review、mock row evidence | `multi-perspective-reviews/<stage>.yaml` / `workflow-state.yaml` / `task-verification-log.yaml` / `execution-state.yaml` / `task-semantic-review.yaml` / `mock-acceptance-execution.yaml` |
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
| `atomic-issues/Txxx.md` | 必须由 `atomic_issue_compile.py` 从 packet 编译生成；可以直接作为 GitHub issue 独立派发；不读完整全局文档也能独立执行：所属模块、模块职责、consumed/provided contracts、背景、范围、决策摘录、代码参考、文件级实现步骤、验证预期、失败含义、禁止事项齐全 |

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
- 已完成适用阶段的 Controlled Multi-Perspective Review gate；阶段级 review 结果已写入 `multi-perspective-reviews/<stage>.yaml`，compiled Atomic Issue quality review 已写入 `atomic-issue-quality-review.yaml`，且无未关闭 blocker。`task-semantic-review.yaml` 属于 execution/pass-task gate，pre-execution 不得要求或伪造 task-local review。
- 若需求涉及 mock acceptance / no-cloud acceptance / repo-specific acceptance runtime，已完成 Production-vs-Acceptance Boundary Matrix、Mock Drift Guard 和 mock Atomic Issue 拆分。
- 若需求涉及多接口后端用户流程，已完成 API Flow DAG、Edge Contract Matrix、Path Coverage Matrix、State/Time Assertion Matrix 和 backend composition acceptance issue 拆分。
- 已完成 Contract Materialization Gate；每个 Atomic Issue 的 Execution Preconditions、Consumed Contract Snapshot、Provided Contract Obligation、Invariant Carryover、Preconditions Failure Handling 均为可执行事实和义务，不是 ID、标题或一句摘要。
- 已完成 `Task DAG` 和拓扑顺序校验。
- 已生成结构化 sidecar：`workflow-state.yaml`、`semantic-objects.yaml`、`contracts.yaml`、`verification.yaml`、`task-dag.yaml`、`backflow.yaml`、`atomic-issue-packets.yaml`。
- `atomic-issues/Txxx.md` 必须由 `atomic_issue_compile.py specs/changes/<change-id>` 从 `atomic-issue-packets.yaml` 编译生成；进入执行前必须运行 `atomic_issue_compile.py specs/changes/<change-id> --check`。
- `atomic_issue_compile.py --check` 只证明 packet 与已生成 Markdown 同步，不是 pre-execution admission，也不代表任务树、DAG、AIP、carrier 或 artifact 质量通过。任何 agent 都不得把该命令输出描述为“任务可执行”“门禁通过”或“可以先执行已闭合任务”。
- `workflowctl.py validate pre-execution specs/changes/<change-id>` 必须通过；它负责真实解析 DEC/C/T/VER 引用图、Task DAG、supersession/backflow、Not Run blocking 和 Atomic Issue Markdown/YAML 对齐。
- `workflowctl.py validate pre-execution` 还会检查 `stage_status.execution` 必须仍是 `not_started`，并检查 git worktree 中不能有 `specs/changes/<change-id>` 之外的改动；如果失败，说明已经过早进入执行，必须回流。
- 发生回流时必须运行 `workflowctl.py backflow specs/changes/<change-id> BF-xxx`，让失效的 DEC/C/VER 自动传播到 direct tasks、downstream tasks 和需要重跑的 verification；不得只手工改当前发现的一个 issue。
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

- 进入 `atomic-execution-sdd` 前必须先运行 `python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py validate pre-execution specs/changes/<change-id>` 和 `python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/validate_artifacts.py specs/changes/<change-id>`。
- 任一失败时，必须回流到 `atomic-task-planning` 或最早缺失阶段；不得读取手写 Markdown-only issue 开始改代码，也不得修改 `specs/changes/<change-id>` 之外的文件。
- 两个 pre-execution gate 都通过后，必须运行 `python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py begin-execution specs/changes/<change-id>`；没有 `execution_receipt` 时不得修改业务文件。
- 各阶段完成时不能手工编辑 `stage_status` 为 `passed`；必须运行 `python3 ${CODEX_HOME:-$HOME/.codex}/skills/ai-dev-methodology/scripts/workflowctl.py pass-stage <stage> specs/changes/<change-id>`。该命令会先运行阶段 validator 和 `validate_artifacts.py --stage <stage>`，再写入 `stage_status` 和 `stage_receipts`。如果后续修改了被签收 artifact，hash 会失效，必须重跑 `pass-stage`。
- 缺少结构化 sidecar 或 `atomic-issue-packets.yaml` 时，视为没有合格 Atomic Issues；即使 `tasks.md` 存在且标 ready/done，也不得执行。
- `atomic-issues/Txxx.md` 必须由 `atomic_issue_compile.py` 从 packet 编译，且 `atomic_issue_compile.py specs/changes/<change-id> --check` 通过；否则不得进入实现。
- 只执行 `tasks.md` 中索引的 Atomic Issue。
- 单个任务执行时，Atomic Issue 是 primary input；`proposal/spec/plan` 只能用于核对 source of truth，不能用于补齐 issue 缺失语义。
- 每个任务改代码前必须运行 `workflowctl.py admit-task Txxx specs/changes/<change-id>`；改完后必须运行 `workflowctl.py validate-task-diff Txxx specs/changes/<change-id>`；通过验证并记录 fresh result 后必须运行 `workflowctl.py pass-task Txxx specs/changes/<change-id>`。
- 如果 diff 超出 admitted file allowlist，必须 backflow/reseal/re-admit；不得用 “mechanical dependency / compile dependency / necessary consequence” 作为豁免。
- 遇到新决策，暂停并回写 `proposal/spec/plan/tasks`。
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

当需要人类决策时，输出改为单条 Human Decision Prompt，不使用上面的批量 workflow 启动表来关闭决策。Prompt 必须说明当前阶段、决策背景、关键语义、推荐方案、备选方案、影响范围和需要用户回答的内容；用户回答并落盘后，才能输出下一条决策。
