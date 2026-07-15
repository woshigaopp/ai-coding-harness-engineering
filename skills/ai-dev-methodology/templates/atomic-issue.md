# Txxx: <中文动宾短标题，保留代码/API 标识原文>

> 本文件必须能直接作为 GitHub issue 独立派发。worker 只读取本 issue 和下方列出的文件路径，应能完成实现、运行验证，并且不做新产品/架构/接口决策。

## 目标

用中文说明本任务要交付什么、为什么存在、推进哪个 REQ/SCN/DEC/Contract。不要只写任务标题。

## 范围

| In scope | Out of scope |
|---|---|
|  |  |

## 来源上下文

复制完成本任务必需的上游语义。不能只列 ID，不能写“见 spec/plan”。必要时包含输入、输出、错误、权限、状态、边界条件和用户可见行为。

| Source | Required excerpt / meaning |
|---|---|
| REQ-xxx |  |
| SCN-xxx |  |
| DEC-xxx |  |
| C-xxx |  |

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
| DEC-xxx |  |  |

## 契约摘录

| Contract | Trigger | Normal path | Failure path | Consistency | Timing | Verification excerpt |
|---|---|---|---|---|---|---|
| C-xxx |  |  |  |  |  |  |

## 执行前提

写前置任务或上游契约完成后已经成立的事实和证据。不能只写 “Txxx completed”。

| Upstream task/contract | Already true before this task starts | Evidence / verification that should have passed | If false |
|---|---|---|---|
| Txxx / C-xxx |  |  | Stop and backflow to planning/contract/verification; do not patch upstream in this task |

## Consumed Contract Snapshot

复制本任务可无条件依赖的契约语义。不能只写 contract ID、标题或一句总结。

| Contract | Provider task/module | This task may assume | Field/state/error/timing details | Forbidden interpretation |
|---|---|---|---|---|
| C-xxx |  |  |  |  |

## Provided Contract Obligation

写本任务完成后必须交付给下游 consumer 的可观察保证。

| Contract | Downstream consumer | This task must guarantee | Observable output / state | Verification proving it |
|---|---|---|---|---|
| C-xxx |  |  |  |  |

## Invariant Carryover

| Invariant | Source | Must remain true after this task | Regression check |
|---|---|---|---|
|  |  |  |  |

## Preconditions Failure Handling

| Failure | Classification | Required backflow | Do not do |
|---|---|---|---|
| 前提事实不成立 / 契约未物化 / provider guarantee 不满足 consumer assumption | contract-materialization-gap | 更新 Backflow Invalidation Matrix，回到 contract/task planning 补齐后再执行 | 不临时猜测、不顺手修上游、不重新定义契约 |

## 现有代码参考

| Pattern/reference | Exact path | What to follow | What not to inherit |
|---|---|---|---|
|  |  |  |  |

## 修改文件

每行必须是可定位路径。新文件必须写出目标包/目录、命名规则和职责；不得只写 “new helper under ...”。

| Path | Required change | Ownership / notes |
|---|---|---|
|  |  |  |

## 行为细节

| Item | Detail |
|---|---|
| Inputs |  |
| Outputs |  |
| Error behavior |  |
| State / persistence |  |
| Compatibility |  |
| Boundary conditions |  |

## Frontend User Task Contract

前端/UI/page/form/route/action 任务必填。非前端任务可省略。

| Field | Value |
|---|---|
| User task ID |  |
| User goal |  |
| Entry points |  |
| Page/routes |  |
| Visible controls |  |
| Required data |  |
| Primary action |  |
| Loading/empty/error states |  |
| Success next state |  |
| Failure feedback |  |

## Action-To-Route-To-Component

| Action ID | Visible action | Source component | Permission/visibility guard | Handler | Route/API | Router definition | Landing component | Mode branch required | Forbidden inherited UI/API | Success feedback | Failure feedback | Verification |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |  |  |  |  |

## Mode Field Display Matrix

| Surface | Mode/state | Data source | Must show | Must hide | Label/i18n | Empty/error state | Fixture ref | Assertion |
|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |

## Form State Matrix

| Form/step | Mode/state | Active fields | Inactive/hidden fields | Default/reset rule | Validation trigger | Submit participation | Error location |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

## Mode Leakage Negative Assertions

- 前端任务必须列出旧 mode 字段/文案/payload/事件/入口不得出现或不得参与提交的负向断言。

## Fixture Needs

| Fixture | State needed | Consumer page/action | Contract source | Required for verification |
|---|---|---|---|---|
|  |  |  |  |  |

## Browser Verification Obligation

| Item | Value |
|---|---|
| Required | true |
| Steps |  |
| Network assertions |  |
| DOM assertions |  |
| Screenshot or trace |  |
| Negative assertions |  |
| Failure meaning |  |

## Experience Rubric

| Dimension | Score / evidence |
|---|---|
| task_clarity |  |
| form_ergonomics |  |
| state_completeness |  |
| error_readability |  |
| mode_separation |  |
| route_action_closure |  |
| design_consistency |  |
| responsive_layout_sanity |  |

## 实现步骤

1. 文件级步骤；写清在哪个文件做什么。
2. 不要求实现者重新选择字段名、错误码、UI 表现、事务边界或验证方式。
3. 如必须发现现有 pattern，写清搜索命令或参考路径。

## 验证

| Check | Command/manual step | Expected result | Proves | Failure meaning / Not Run risk |
|---|---|---|---|---|
|  |  |  | REQ/SCN/DEC/C |  |

## 禁止事项

- 不做新的产品或架构决策。
- 不修改 Files To Change 表之外的文件；如必须修改，先更新本 issue。
- 不做无关重构。
- 不把必要语义留在 `proposal/spec/plan` 中；执行所需语义必须补进本 issue。

## 完成标准

- [ ] All in-scope changes are implemented.
- [ ] Verification commands/steps were run or Not Run risk is recorded.
- [ ] No prohibited changes were made.
- [ ] No new decision gap remains open.
- [ ] 本 issue 可以不依赖完整全局文档独立复现实现与验证。
