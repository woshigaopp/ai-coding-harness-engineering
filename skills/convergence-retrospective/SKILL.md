---
name: convergence-retrospective
description: 大需求实现后的收敛复盘。Use after implementation or after multiple fix commits to classify convergence into unavoidable N2 contract changes versus avoidable N1 failures, identify missing requirements, archaeology, contracts, patterns, or verification, and update skills/current/knowledge for future work.
---

# Convergence Retrospective

## 定位

这是闭环阶段。目标不是复盘情绪，而是改进 workflow。

执行或评审本阶段时，必须按 `ai-dev-methodology/references/artifact-completeness-spec.md` 的 “Stage 12: Convergence Retrospective” 检查正交维度、Required Artifacts、Completeness Criteria 和 Exit Gate。

问题分类：

- `N2 expected`: 跨模块语义约束收敛，理论下限的一部分。
- `N1 avoidable`: 模块内部、工程纪律、pattern、验证、考古遗漏导致的可消除收敛。
- `product-acceptance finding`: 产品语义验收发现的问题；必须反查最早缺失阶段，而不是只按实现 bug 处理。
- `workflow-closure leak`: source intake、decision consistency、task DAG、backflow invalidation 或 Not Run 阻断没有真正执行，导致错误穿透到实现或完成声明。

## 输入

- 初始实现 commit。
- 后续 fix / review / test 收敛 commits。
- `specs/changes/<change-id>/` artifacts。
- 测试报告、review comments、bug list。
- `acceptance/product-acceptance-review.md`，如果执行过产品验收。

## Local Audit Gate: Retrospective Source Completeness Audit

开始分类前，主 agent 必须本地二次审计复盘输入是否完整。本地审计不做最终 N1/N2 分类，只指出缺失 source。

输出：

```markdown
### Retrospective Source Local Audit Report

| Source | Status | Missing / unavailable detail | Classification impact | Blocks retrospective |
|---|---|---|---|---:|
```

阻塞条件：

- 关键 fix/review/test evidence 缺失。
- 应执行产品验收但缺 PAR 报告。
- specs/changes artifacts 不完整到无法判断最早缺失阶段。

## 分类表

```markdown
## Convergence Classification

| Commit/Issue | Symptom | Category | Root cause | Should have been caught by | Workflow fix |
|---|---|---|---|---|---|
```

Category 只能是：

- `N2-contract`
- `requirement-gap`
- `aip-decision-gap`
- `archaeology-miss`
- `contract-miss`
- `migration-diff-miss`
- `pattern-miss`
- `atomic-task-too-large`
- `atomic-issue-not-self-contained`
- `sdd-template-overfit`
- `verification-miss`
- `product-acceptance-miss`
- `product-semantic-conflict`
- `execution-discipline`
- `source-intake-miss`
- `decision-conflict`
- `task-dag-miss`
- `backflow-invalidation-miss`
- `not-run-completion-leak`

新增分类含义：

| Category | Meaning |
|---|---|
| `atomic-issue-not-self-contained` | 任务只是 `tasks.md` checklist item，缺少独立执行所需背景、决策、契约、代码参考或验证预期 |
| `sdd-template-overfit` | 为适配 SDD 轻量模板而牺牲 AutoMQ AI coding 所需 artifact 粒度或质量 |
| `product-acceptance-miss` | 应执行产品语义验收但未执行，或验收没有真实浏览器/runtime evidence |
| `product-semantic-conflict` | 代码可运行但用户可见语义冲突，例如 mode 泄漏、状态不一致、不支持能力仍展示 |
| `runtime-lifecycle-miss` | 只验证创建或 happy path，没有覆盖更新、删除、失败恢复、指标链路、自动调节触发等创建后能力 |
| `source-intake-miss` | 用户提供或 workflow 发现的 source 未登记/未读取/未映射，后续 artifact 基于不完整输入生成 |
| `decision-conflict` | 同一 Decision key 存在多个冲突 active locked 决策，或 supersession 未正确关闭旧决策 |
| `task-dag-miss` | Atomic Issue 顺序没有按 provider/consumer、文件 ownership、verification gate 建 DAG，导致依赖倒置或并行污染 |
| `backflow-invalidation-miss` | 决策、契约、验证或验收变化后，没有使受影响 DEC/C/T/VER 失效并重写/重跑 |
| `not-run-completion-leak` | P0/P1、关键契约或 `Blocks done=yes` 的 Not Run 未阻塞完成声明 |

## Local Audit Gate: Classification Consistency Audit

Convergence Classification 初稿完成后，主 agent 必须本地二次复核 N2/N1、category、root cause 和 should-have-been-caught-by 是否自洽。

输出：

```markdown
### Classification Local Audit Report

| Item | Auditor category | Earliest missed gate | Evidence | Proposed skill/artifact fix | Disagrees with main? |
|---|---|---|---|---|---:|
```

阻塞条件：

- 存在未分类 convergence item。
- N1 avoidable 被归为 N2 expected。
- product acceptance finding 未反查最早缺失阶段。
- Not Run leak 未作为阻塞项处理。
- 主审计和 本地审计分类冲突未说明最终裁决理由。

## 指标

```markdown
| Metric | Count |
|---|---:|
| Total convergence items |  |
| N2 expected |  |
| N1 avoidable |  |
| Requirement/AIP gaps |  |
| Verification misses |  |
| Product acceptance misses |  |
| Product semantic conflicts |  |
| Runtime lifecycle misses |  |
| Source intake misses |  |
| Decision conflicts |  |
| Task DAG misses |  |
| Backflow invalidation misses |  |
| Not Run completion leaks |  |
```

## 输出

```markdown
## Retrospective Actions

| Action | Target | Reason | Owner |
|---|---|---|---|
| Update skill |  |  |  |
| Update current spec |  |  |  |
| Add pattern |  |  |  |
| Add verification |  |  |  |
```

## 沉淀规则

- 发现长期系统事实变化：更新 `specs/current/<area>/`。
- 发现 workflow 缺口：更新对应 skill。
- 发现任务不能独立派发：更新 `atomic-task-planning` 产物要求，并补 `atomic-issues/`。
- 发现项目 pattern：更新 archaeology/pattern 文档或 current spec。
- 发现验证缺口：更新 verification matrix 模板。
- 发现产品语义冲突：更新 `product-acceptance-review`、PRD、frontend contract、cross-module contract 或 verification matrix 中最早缺失的一环。
- 发现创建后能力遗漏：同时更新 PRD runtime lifecycle、code archaeology runtime lifecycle、contract、verification、atomic task planning 和 product acceptance 的最早缺失阶段。
- 发现 source intake 漏读：更新 `source-intake-ledger.md`，补 Source To Semantic Object Map，并使基于旧输入生成的 DEC/C/T/VER 进入 Backflow Invalidation Matrix。
- 发现决策冲突：更新 Decision key、Decision Consistency Matrix 和 supersession 记录，受影响 task 必须 pending-rewrite。
- 发现 Task DAG 缺失或错误：更新 `tasks.md` 的 Task DAG，重新计算 provider/consumer/verification 顺序，并检查已执行 task 是否需要回滚或重跑。
- 发现回流失效遗漏：补 Backflow Invalidation Matrix，列出失效 artifacts、decisions、contracts、issues 和 verification rerun。
- 发现 Not Run 泄漏：更新 Verification Matrix / tasks.md Not Run 表，明确 Severity、Owner/approval、Blocks done，并撤销错误的完成声明。

## Local Audit Gate: Workflow Closure Audit

Retrospective Actions 完成后、退出前，主 agent 必须本地二次审计每个 N1 是否真正反哺 workflow/current/skill。

输出：

```markdown
### Retrospective Closure Local Audit Report

| N1 item | Workflow fix present? | Target artifact updated | Evidence | Remaining gap | Blocks retrospective closure |
|---|---:|---|---|---|---:|
```

阻塞条件：

- N1 avoidable 没有 workflow fix。
- source intake、decision consistency、task DAG、backflow invalidation 或 Not Run 缺口未更新对应 artifact。
- 错误 done 未撤销或未记录用户明确风险接受。
- 应更新 skill/current/knowledge 但只写在复盘文字里。

## 退出检查

- [ ] 所有收敛项已分类。
- [ ] N2 和 N1 已区分。
- [ ] 每个 N1 avoidable 有 workflow fix。
- [ ] 每个 `atomic-issue-not-self-contained` 都明确缺失的 issue section。
- [ ] 每个 `sdd-template-overfit` 都明确应新增或加厚的 artifact。
- [ ] 每个 `source-intake-miss` 都补 Source Intake Ledger，并列出受影响 semantic object。
- [ ] 每个 `decision-conflict` 都补 Decision Consistency Matrix / supersession。
- [ ] 每个 `task-dag-miss` 都补 Task DAG 并重算执行顺序。
- [ ] 每个 `backflow-invalidation-miss` 都补 Backflow Invalidation Matrix。
- [ ] 每个 `not-run-completion-leak` 都撤销错误 done 或记录用户明确风险接受。
- [ ] 如果有产品验收问题，已反查最早缺失阶段，并区分是 PRD/考古/契约/验证/实现/部署缺口。
- [ ] 如果有创建后能力问题，已区分是 runtime lifecycle PRD 缺口、考古链路缺口、契约缺口、验证缺口还是执行纪律缺口。
- [ ] 如果应执行但未执行产品验收，已归类为 `product-acceptance-miss` 并补 workflow fix。
- [ ] 需要沉淀的事实已写入 current/knowledge/skill。
- [ ] 已完成 Retrospective Source、Classification、Workflow Closure Local Audit Reports；无阻塞项。
- [ ] 已满足 artifact-completeness-spec Stage 12 的 Classification、Metrics、Retrospective Actions artifact 要求。
