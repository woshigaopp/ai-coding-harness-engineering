---
name: migration-diff-analysis
description: 旧代码大改动中的旧设计与新设计差异分析。Use after code-archaeology-sdd and new-feature-design for refactors, migrations, or major existing-code changes to compare old/new module semantics, decide delete/keep/modify/add actions, produce a migration plan, preserve or retire hidden constraints, update the Decision Registry, and feed cross-module contracts and atomic tasks.
---

# Migration Diff Analysis

## 定位

用于已有代码大改动。它连接：

```text
旧设计考古 -> 新设计 -> 差异分析/迁移计划 -> 跨模块契约 -> 原子任务
```

它解决的问题是：第一次实现没做干净，后面靠收敛 commit 补删字段、改命名、补兼容、改同步异步。

执行或评审本阶段时，必须按 `ai-dev-methodology/references/artifact-completeness-spec.md` 的 “Stage 5: Migration Diff” 检查正交维度、Required Artifacts、Completeness Criteria 和 Exit Gate。

本阶段产生的 delete/keep/modify/add/rename/compatibility 决策，必须写入 `specs/changes/<change-id>/decision-reviews/migration-decisions.md`，使用或等价满足 `ai-dev-methodology/templates/stage-decision-document.md`，并同步进入 Decision Registry。任何影响用户可见兼容性的迁移决策必须对齐 PRD/AIP，不能作为普通工程微决策静默处理。

## 输入

- `code-archaeology-sdd` 产物：模块清单、依赖图、隐式约束、pattern、框架行为规则。
- `new-feature-design` 产物：新模块边界、模块语义、场景、决策。
- Decision Registry。
- 需求文档和 AIP。
- 目标 `specs/changes/<change-id>/`。

## 流程

### Step 1: 旧/新模块映射

```markdown
| 旧模块 | 新模块 | 关系 | 决策 |
|---|---|---|---|
| OldA | NewA | rename/split/merge/replace/remove/new |  |
```

关系必须是以下之一：

- `keep`
- `rename`
- `split`
- `merge`
- `replace`
- `remove`
- `new`

### Step 2: 21 问维度对比

对每个映射模块比较关键语义：

```markdown
| 维度 | 旧设计 | 新设计 | 差异 | 处理决策 | 验证方式 |
|---|---|---|---|---|---|
| 身份/职责 |  |  |  |  |  |
| 输入 |  |  |  |  |  |
| 输出 |  |  |  |  |  |
| 状态机 |  |  |  |  |  |
| 失败语义 |  |  |  |  |  |
| 一致性/事务 |  |  |  |  |  |
| 依赖 |  |  |  |  |  |
| 边界情况 |  |  |  |  |  |
```

### Step 3: 隐式约束处理

每条旧约束必须有处理决策：

```markdown
| 约束 | 来源 | 新设计是否仍需要 | 决策 | 理由 | 验证 |
|---|---|---:|---|---|---|
```

决策只能是：

- `preserve`
- `modify`
- `retire`
- `replace`
- `needs-human-decision`

`needs-human-decision` 阻塞进入实现。

每个 `preserve/modify/retire/replace` 决策必须进入 Decision Registry，类型为 `migration` 或 `pattern`。

如果 `code-archaeology-sdd` 输出了 Persistent Mutation / Schema Compatibility Audit，本阶段必须把每个受影响 mutation 和旧 required constraint 拆成迁移决策。尤其是新 mode/资源类型让旧字段合法缺失时，不能只写“additive migration”或“persist canonical state”；必须决定旧 schema/DO/mapper/VO/API required 约束如何处理。

```markdown
### Persistent Mutation Migration Matrix

| Mutation | Mode/variant | State owner | Writer | Old required field/resource | New rule | Migration action | Compatibility/readback impact | Verification | Decision ID |
|---|---|---|---|---|---|---|---|---|---|
```

`New rule` 只能是 `nullable`、`derived`、`defaulted`、`compat-placeholder`、`forbidden`、`retired` 或 `needs-human-decision`。`needs-human-decision` 阻塞进入跨模块契约。任何选择都必须说明 detail/list/progress/event/readback 会读到什么。

### Step 4: 旧代码处理计划

```markdown
## Migration Plan

### Delete
| 对象 | 原因 | 安全条件 | 验证 |

### Keep
| 对象 | 原因 | 约束 | 验证 |

### Modify
| 对象 | 旧行为 | 新行为 | 验证 |

### Add
| 对象 | 原因 | 依赖 | 验证 |

### Rename
| 旧名 | 新名 | 范围 | 是否纯机械 | 验证 |

### Compatibility
| 旧输入/旧数据/旧 API | 新行为 | 回滚影响 | 验证 |
```

### Step 5: 执行顺序约束

定义哪些改动必须先做：

```markdown
| Step | 内容 | 前置条件 | 阻塞哪些后续任务 | 验证 |
|---|---|---|---|---|
```

### Step 6: 输出映射

- `plan.md`: 放入旧/新差异、隐式约束处理、迁移计划、执行顺序。
- `spec.md`: 放入改变后的行为契约和兼容语义。
- `tasks.md`: 后续由 `atomic-task-planning` 转成具体任务。
- Decision Registry: 写入迁移决策、兼容决策、旧 pattern 保留/废弃决策。

## Local Audit Gate: Migration Coverage Audit

Migration Plan 完成后、进入跨模块契约前，主 agent 必须本地二次审计旧/新差异处理是否闭合。本地审计不做 delete/keep/modify/add 最终决策，只复核每个迁移动作是否有证据、决策和验证。

输入：

- 旧/新模块映射。
- 21 问维度对比。
- 隐式约束处理表。
- Migration Plan 和执行顺序约束。
- Decision Registry。

输出：

```markdown
### Migration Local Audit Report

| Audit scope | Finding | Evidence | Missing migration decision | Required backflow | Blocks contract/task planning |
|---|---|---|---|---|---:|
```

阻塞条件：

- 旧模块/新模块映射缺失或 `relation` 不明确。
- 旧隐式约束没有 preserve/modify/retire/replace 决策。
- Persistent Mutation / Schema Compatibility Audit 中的旧 required constraint 没有迁移决策、state owner、writer、readback 影响或验证。
- 删除/重命名/兼容项缺安全条件或验证。
- 迁移决策未进入 Decision Registry。
- 迁移改变用户可见行为但未回流 PRD/AIP。

## 退出检查

- [ ] 旧模块和新模块都有映射。
- [ ] 每条旧隐式约束都有处理决策。
- [ ] 每个迁移处理决策已进入 Decision Registry。
- [ ] 每个持久化 mutation 的旧 required schema/field/resource 约束都有 nullable/derived/defaulted/compat-placeholder/forbidden/retired 决策，并映射到 readback 验证。
- [ ] 每个删除/重命名/迁移项有安全条件和验证方式。
- [ ] 没有 `needs-human-decision`。
- [ ] 迁移计划能解释“哪些旧东西删、哪些保留、哪些改、哪些新增”。
- [ ] 已完成 Migration Local Audit Report；无 `Blocks contract/task planning=yes` 项。
- [ ] 结果已写入 `specs/changes/<change-id>/plan.md` 或明确引用。
- [ ] 已满足 artifact-completeness-spec Stage 5 的 Old/New Mapping、Semantic Diff、Hidden Constraint Handling、Migration Action、Execution Order、Risk/Rollback artifact 要求。
