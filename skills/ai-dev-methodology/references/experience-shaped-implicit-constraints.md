# Experience-Shaped Implicit Constraints

本文件是 AI coding workflow 的“经验型隐式约束”目录。它不保存某个需求的结论，而保存可复用的问题形状：人类工程师看到这些词会自然继续追问，但 AI 容易把它压缩成一句话后漏实现。

一条经验能进入本目录，必须同时满足：

| Criteria | Meaning |
|---|---|
| 可泛化 | 不是某个需求或某个仓库的专用补丁，而是一类大需求会反复出现的问题形状 |
| AI 易压缩 | AI 容易把它写成 `mode-specific`、`auto-create`、`support lifecycle`、`follow existing pattern` 等薄语义 |
| 可结构化 | 能展开成矩阵、contract、semantic carrier、Atomic Issue packet section 和 verification |
| 可验证 | 能定义明确的 proof，不能只靠人工觉得合理 |

使用方式：

- PRD/readiness 阶段：把命中的问题形状列入 `decision-surface-discovery.md`。
- archaeology/design/contract 阶段：把它展开成事实、决策和契约，而不是留给实现阶段。
- verification/task-planning 阶段：把它复制进 `semantic_carriers` 和 owner packet 的执行 section。
- mock/product acceptance 阶段：验收失败时优先反查是否有经验型隐式约束没有被发现或没有被物化。

## Contents

- [EXP-001 Stateful Behavior Closure](#exp-001-stateful-behavior-closure)
- [EXP-002 Frontend Action-Flow Closure](#exp-002-frontend-action-flow-closure)
- [EXP-003 Persistent Mutation And Schema Compatibility](#exp-003-persistent-mutation-and-schema-compatibility)
- [EXP-004 Managed External Resource Ownership Lifecycle](#exp-004-managed-external-resource-ownership-lifecycle)
- [EXP-005 Reference UI Pattern Materialization](#exp-005-reference-ui-pattern-materialization)
- [EXP-006 Production Vs Acceptance Boundary](#exp-006-production-vs-acceptance-boundary)
- [EXP-007 Existing Object-Action Variant Consumer Parity](#exp-007-existing-object-action-variant-consumer-parity)
- [EXP-008 External Side Effect Boundary](#exp-008-external-side-effect-boundary)
- [EXP-009 Runtime Test Topology And Proof Owner](#exp-009-runtime-test-topology-and-proof-owner)
- [EXP-010 Runtime Mode Materialization Parity](#exp-010-runtime-mode-materialization-parity)
- [EXP-011 External Mechanism Mapping Closure](#exp-011-external-mechanism-mapping-closure)

## EXP-001 Stateful Behavior Closure

触发词：`lifecycle`、`progress`、`event`、`status`、`terminal`、`polling`、`retry`、`task step`、状态机、进度、事件、终态、轮询、重试。

必须展开：

- operation、mode/variant、from/to state、trigger、guard。
- event/step、status、terminal、failure reason、retry/idempotency。
- producer、consumer、API/VO/frontend/mock 读取路径。
- frontend assertion、fixture、backend/API/runtime verification。

只写“实现事件机制 / progress graph / mock state graph”不合格。

## EXP-002 Frontend Action-Flow Closure

触发词：按钮、操作下拉、tab action、行操作、wizard submit、update-config、resize、delete、logs、metrics、workers、progress。

必须展开：

- source page/component、visible action、handler、route/API、router definition、landing component。
- permission/mode visibility、loading/empty/error/success feedback。
- forbidden inherited route/API/UI。
- DOM/network/browser proof 和 negative assertion。

只写“前端按 mode 区分 / 更新详情页 / action route”不合格。

## EXP-003 Persistent Mutation And Schema Compatibility

触发词：create/update/delete/resize/save/scale/import/bind、新 mode、新资源类型、旧字段在新 mode 下缺失、DB/schema/mapper/VO/API 兼容。

必须展开：

- authoritative state owner。
- writer path。
- old required field/resource constraint。
- new nullable/default/derived/compat-placeholder/forbidden/retired rule。
- readback consumers。
- write proof + readback proof。

只写“persist canonical state / additive migration / save new fields”不合格。

## EXP-004 Managed External Resource Ownership Lifecycle

触发词：`auto-create`、`default-created`、`generated resource`、`managed resource`、`select-existing`、`existing resource`、自动创建、默认创建、生成资源、托管资源、选择已有；并且对象是云资源、K8s 资源、IAM/Role/Profile、network/security group、storage、DNS、bucket、compute group、external provider resource 等外部资源。

这个问题形状必须和 selector 区分开：

- selector 只回答用户如何选择、候选如何加载、空态/错误态如何展示。
- managed resource ownership 回答外部资源是否真的被创建、谁拥有、谁清理。

必须展开：

| Required aspect | Required answer |
|---|---|
| Selection mode | auto-create、default-created、generated、select-existing、user-provided、derived 或 N/A |
| Create timing | 在 check、submit、async task、runtime reconciliation、deploy step 中哪一步创建 |
| Provider writer | 哪个真实 provider/API/operator/resource writer 被生产代码调用 |
| Resource identity | 资源 ID/name/ARN/UID/tag 如何生成和识别 |
| Provenance state | owned/existing/derived/generated 状态由谁持久化，字段在哪 |
| Runtime consumer | 哪些 runtime/deploy/update/detail/readback 路径消费资源 ID |
| Update rule | 配置变化时是 reuse、replace、patch、detach、forbid 还是 needs-decision |
| Delete cleanup | delete 时清理 owned 资源，保护 existing 资源；部分失败如何保留 residual summary |
| Idempotency | 重试 create/delete/update 时如何识别已有资源并避免重复或误删 |
| Failure behavior | provider failure、permission denied、quota、partial create、cleanup failure 的 typed error/state |
| Verification | provider create/delete/update call proof、ownership persistence/readback proof、cleanup/protect proof |

只写“auto-create SG/IAM / use provider selector / resolved config”不合格。只写“delete cleans resources”也不合格；必须证明 owned/existing provenance 与真实 provider mutation 闭合。

## EXP-005 Reference UI Pattern Materialization

触发词：参考、复用、沿用、像某页面、same experience、follow existing UI、visual parity、layout parity。

必须展开：

- reference file/component。
- must reuse/adapt。
- must not inherit。
- visual/layout obligation。
- interaction/state obligation。
- browser/visual proof。

只写“参考现有页面 / 保持一致”不合格。

## EXP-006 Production Vs Acceptance Boundary

触发词：mock acceptance、no-cloud、playground、repo-specific acceptance runtime、不上真实云验收、simulator。

必须展开：

- 生产代码必须调用的真实 controller/service/manager/task/repository/provider/API/resource 副作用。
- 验收适配器只替换物理外部依赖，不替换业务逻辑。
- mock/backend/frontend/package matrix 证明真实产品路径。
- drift guard 防止 mock 与真实契约漂移。

不得把 no-cloud/playground 理解成生产实现可以本地假成功、只写 DB、只发事件或跳过 provider/resource adapter。

## EXP-007 Existing Object-Action Variant Consumer Parity

触发结构：需求新增或替换底层实现形态，但代码仍复用同一个业务对象、同一个 create/update/delete/resize/save/scale/import/bind action、同一个 API/page/controller 入口、同一套 readback API/VO 或创建后 consumer。这个结构可能被叫做 mode、deployment type、runtime backend、provider、runner、execution environment、placement、adapter，也可能完全不出现这些词。

必须展开：

- 从代码生成 `existing-object-action-consumer-graph.md`：object/action、entrypoint、existing variant、producer chain、state owner/storage、readback API/VO、consumer surface、hidden old-variant assumption。
- 生成 `variant-impact-matrix.md`：新形态是否复用旧 consumer；每个旧 consumer 是否必须被新形态满足；不支持是否有 locked decision。
- 如果旧 consumer 包含 progress/change/last-change/change detail/task step/event step/terminal polling，生成 `progress-change-producer-chain-matrix.md`：canonical writer、state owner/table、task/event producer、correlation key、last-change readback、change detail readback、terminal/failure、verification、owner issue。
- 原子任务拆分必须先有生产 writer/readback provider task，再有 consumer task 或 proof-only verification，并在 DAG 中建立 producer -> consumer 边。

只写“新 mode 参考旧模式 / mode-specific progress / mock fixture covers progress / 最终状态正确”不合格。必须证明同一个创建对象 id 能从 mutation API 关联到 last-change 和 change detail；`VER-xxx id` 或 fixture-only proof 不算生产链路闭包。

## EXP-008 External Side Effect Boundary

触发词：external side effect、provider side effect、cloud-runtime、provider API、operator、resource mutation、runtime scheduler、autoscaling policy、AWS、ASG、K8s、Terraform、Helm、IAM、no-cloud、playground、外部副作用、云资源、验收替代。

必须展开：

- `external-side-effect-contract-matrix.md`：production side-effect owner、required production call/resource mutation、physical dependency policy、no-cloud/playground substitute boundary、minimum acceptable proof、failure/partial failure semantics、state/readback consumer、contract、verification、owner issue。
- no-cloud/playground 只能替换物理外部端点；不能替换业务 manager/task/provider 调用链。
- 如果真实外部系统能力不足，必须用 alternative decision 锁定可接受 proof 和 product/ops impact。

只写“调用 provider / playground mock / runtime side effect / log hook / final state correct”不合格。DB-only、fixture-only、frontend-only、log-only 或 compile-only 都不能关闭外部副作用契约。

## EXP-009 Runtime Test Topology And Proof Owner

触发词：runtime proof、proof owner、build/install、freshness、SNAPSHOT、reactor、Maven、Gradle、cross-module test、packaged playground、packaged playground image、验证落点、构建拓扑、模块依赖、新鲜度。

必须展开：

- `runtime-test-topology-matrix.md`：production path、proof module/package、proof file/path、fixture/support files、required build/install/freshness step、staleness risk、verification command、expected result、owner issue。
- Proof Owner File Matrix：每个 verification proof file 是否必须进入 owner task 的 packet `files_to_change` 和 `task-dag.yaml.files`。
- task planning 的 Proof Owner Allowlist Matrix 和 Semantic Load Split Matrix 必须消费这些行。

只写“额外跑 integration test / 需要 install / proof in cluster-manager test”不合格。证明文件没进 allowlist 是 task-planning gap，不是执行期临时扩 scope。

## EXP-010 Runtime Mode Materialization Parity

触发结构：需求新增、替换、重构或缩减 deployment/runtime mode、runtime substrate、execution environment、runner、provider backend、VM/container/orchestrator/bootstrap path、插件/配置/secret 注入路径，并且产品能力需要继续成立。

这是按需经验，不在本目录展开细节。命中后读取：

`references/experience/runtime-mode-materialization-parity.md`

必须先分类：新增并存模式、替换/退役旧模式、内部 substrate 重构、能力降级/范围收缩。分类不明时是 PRD/AIP decision gap，不得由实现阶段猜。

必须产出或更新：

- `runtime-materialization-parity.md`
- `decision-surface-discovery.md` 中的 runtime materialization surface
- runtime materialization contract / verification / owner Atomic Issue

只写“新 mode 支持运行时 / 创建资源后启动 worker / 使用 userdata / 复用旧模式能力 / mock 验收通过”不合格。必须证明新/改 mode 如何物化产品运行时需要的 artifact、配置、插件/扩展、安全配置、依赖端点、启动入口、生命周期操作和 readback/observability。新增并存模式不得删除、降级或重写旧模式，除非有明确 replacement/retirement 决策。
## EXP-011 External Mechanism Mapping Closure

触发词：外部能力、official mechanism、cloud API、provider API、SDK/API reference、autoscaling、HPA、ASG、target tracking、metrics source、CloudWatch、metrics-server、IAM permission、logs source、runtime capability、storage lifecycle、K8s API、AWS API、外部系统真实机制、指标来源、权限失败。

这个问题形状回答“产品语义如何落到外部系统真实机制”，不是回答“有没有调用 provider”。

必须展开到 `external-capability-research.md` 的 `External Mechanism Decision Matrix`：

- Product semantic：产品真正想表达的语义。
- External system 和 official mechanism/API/resource：官方真实机制、资源、API、指标来源。
- AutoMQ field mapping：产品/API/DB/VO 字段如何映射到外部机制参数。
- Non-equivalent / unsupported semantic：外部机制不能等价表达的语义，例如单 target value 与双阈值不等价。
- Failure/permission/metric-missing behavior：权限不足、指标缺失、区域/版本限制、partial failure 的 AutoMQ 行为。
- Required DEC/ADEC、C、VER、owner task / packet carrier。

只写“参考官方文档 / AWS 支持 autoscaling / HPA 支持 CPU / provider 支持 metrics”不合格。必须证明字段映射和不等价语义已经进入 DEC/C/VER 和 Atomic Issue packet。
