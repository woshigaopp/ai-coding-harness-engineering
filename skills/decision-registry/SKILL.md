---
name: decision-registry
description: 维护大需求全流程决策登记表。Use whenever product, AIP, archaeology, new design, migration diff, contract locking, or implementation discovers a decision, to record source, alternatives, affected modules, status, and verification so implementation remains zero-decision.
---

# Decision Registry

## 定位

这是贯穿全流程的决策 source of truth。

目标是防止：

- 实现阶段临时做选择。
- 上下文压缩后决策丢失。
- AIP、spec、plan、tasks 中同一个决策表述不一致。

## 输出位置

优先放在：

```text
specs/changes/<change-id>/plan.md
```

建议章节：

```markdown
## Decision Registry
```

如果放独立文件，`plan.md` 必须引用。

创建或重写 Decision Registry 时必须使用或等价满足 `ai-dev-methodology/templates/decision-registry.md`。

每个产生决策的阶段还必须生成独立阶段决策文档，不能只把决策埋在主文档段落里：

```text
specs/changes/<change-id>/decision-reviews/<stage>-decisions.md
```

`plan.md` 的 Decision Registry 必须维护 Decision Document Index，记录每个阶段决策文档、本地路径、飞书链接和同步状态。

如果当前环境有 `lark-cli` 写权限，阶段决策文档必须同步到飞书文档，并把 URL 回写到 Decision Document Index。

阶段决策文档默认使用中文。代码标识、API path、字段名、命令、错误码和外部原文可以保留原文。

## 决策类型

| Type | 示例 |
|---|---|
| product | 用户可见行为、配置、状态、错误 |
| architecture | controller-driven vs native autoscaler |
| interface | API 字段、Terraform schema、错误码 |
| migration | 删除/保留/重命名/兼容 |
| contract | 跨模块一致性、时序、失败处理 |
| pattern | 参考哪个页面/模块/框架语义 |
| validation | 用什么验证证明完成 |

## 决策分层规则

| Decision layer | Who may decide | Rule |
|---|---|---|
| Product decision | 用户确认，或用户明确授权 AI 采用推荐决策 | PRD 完成后必须 locked，不能留给 AIP/实现 |
| Architecture/interface/contract/migration decision | AI 可以基于已锁定 PRD/AIP 自主决策 | 不得改变产品语义；必须记录 alternatives/reason/impact/verification |
| Pattern/validation micro-decision | AI 可以根据代码库 pattern 自主决策 | 必须有现有实现参考或明确理由 |
| Implementation decision | 不允许 | 发现缺口时暂停，登记 open decision 并回到对应阶段 |

如果某个工程决策会改变用户可见行为、scope、默认值、错误语义、权限或兼容承诺，它必须升级为 Product Decision，回到 PRD 决策流程。

## 表结构

```markdown
| ID | Type | Decision key | Decision | Alternatives | Source | Affected modules | Supersedes | Superseded by | Status | Verification |
|---|---|---|---|---|---|---|---|---|---|---|
| DEC-001 | product | stable semantic key |  |  | requirement/AIP/user |  | N/A | N/A | locked/open/superseded |  |
```

状态只允许：

- `locked`
- `open`
- `superseded`

`open` 阻塞实现。

`Decision key` 是同一语义问题的稳定键。两个 active locked 决策不能用同一个 key 给出不同结论；如果后续阶段需要改变决策，必须将旧决策标为 `superseded`，新增新决策，并触发回流失效重算。

必须维护：

```markdown
## Decision Consistency Matrix

| Decision key | Active decision | Potentially conflicting decisions | Conflict? | Resolution | Status |
|---|---|---|---:|---|---|
```

`Conflict?=yes` 或 `Status=open` 阻塞 `atomic-task-planning` 和 `atomic-execution-sdd`。

## Stage Decision Document

每个阶段产生或修改决策时，必须更新对应阶段决策文档：

| Stage | File |
|---|---|
| PRD | `decision-reviews/prd-decisions.md` |
| AIP | `decision-reviews/aip-decisions.md` |
| Requirement readiness | `decision-reviews/readiness-decisions.md` |
| New feature design | `decision-reviews/design-decisions.md` |
| Code archaeology | `decision-reviews/archaeology-decisions.md` |
| Migration diff | `decision-reviews/migration-decisions.md` |
| Frontend contract | `decision-reviews/frontend-decisions.md` |
| Cross-module contract | `decision-reviews/contract-decisions.md` |
| Verification matrix | `decision-reviews/verification-decisions.md` |
| Atomic task planning | `decision-reviews/task-planning-decisions.md` |

阶段决策文档至少包含：

```markdown
# <Stage> Decisions

## Source Inputs

| Source | Path/URL | Used for |
|---|---|---|

## Decision Summary

| ID | Type | Question | Final decision | Decided by | Status |
|---|---|---|---|---|---|

## Decision Details

### DEC-XXX: <title>

| Item | Content |
|---|---|
| Question |  |
| Final decision |  |
| Decided by | user-confirmed / ai-recommended / ai-engineering |
| Alternatives |  |
| Reason |  |
| Product constraint alignment |  |
| Affected modules/artifacts |  |
| Verification |  |
| Feishu/Lark URL |  |
```

规则：

- `Decided by=ai-engineering` 只允许用于不改变产品语义的工程决策。
- 所有阶段决策必须同步回总 Decision Registry。
- 飞书同步失败时，保留本地文档，并在 Decision Document Index 标记 `not-created` 和失败原因。
- 每个决策必须有独立 `### DEC-XXX: <title>` 详情段。禁止把多个决策合并成 `PDEC-001..022`、`ADEC-001..004`、`C-001..C-006` 或“同上”。
- 每个独立详情段必须包含 alternatives 和反选理由；即使最终决策来自用户/PRD，也要写明不采用哪些可能方案以及原因。
- 每个独立详情段必须说明对下游 Atomic Issues 的影响：涉及哪些 task、需要复制哪些决策语义、验证如何进入 issue。
- 如果某个决策不能被下游 Atomic Issue 消费，说明它还不是可执行决策，必须补充影响面或验证方式。

## Open Decision Review

当 Decision Registry 中存在会阻塞实现的 `open` 决策时，必须生成面向人类评审的决策评审文档，而不是只在 registry 里写 `TBD`。

输出位置：

```text
specs/changes/<change-id>/decision-review.md
```

并尽量用 `lark-cli` 创建飞书文档，方便评审：

```bash
lark-cli docs +create --title "<需求名> 决策评审" --markdown @specs/changes/<change-id>/decision-review.md --wiki-space "7460028547143417875" --as user
```

每个 open decision 至少包含：

```markdown
### DEC-XXX: <title>

| 项 | 内容 |
|---|---|
| 问题 | 需要人类锁定的选择是什么 |
| 推荐决策 | 推荐采用哪个选项 |
| 状态 | open / 建议锁定为 locked |
| 推荐理由 | 为什么这个选项更适合当前需求和代码库 |
| 现有实现参考 | 相关代码路径、已有 pattern、历史约束 |
| 不推荐方案 | 备选方案和拒绝原因 |
| 实现影响 | API / DB / backend / frontend / deployment / tests 影响 |
| 验证方式 | 决策落地后如何证明正确 |
```

规则：

- 推荐决策必须明确，不能只提问。
- 如果涉及已有系统能力，必须先考古并引用现有实现 pattern。
- 飞书链接创建成功后，回写到 `proposal.md` 或 `plan.md`。
- 只要仍有 blocking `open` 决策，不得进入 `atomic-execution-sdd`。

## 使用规则

### 添加决策

每当出现“也可以这样，也可以那样”时，必须登记。

### 修改决策

不得静默改旧行。应：

1. 将旧决策标记为 `superseded`。
2. 新增新决策。
3. 说明替换原因。
4. 更新 `Backflow Invalidation Matrix`，列出失效的 contracts、Atomic Issues 和 verification。

### 执行阶段发现缺口

输出 Decision Gap，并回写 registry：

```markdown
| ID | Type | Decision | Alternatives | Source | Affected modules | Status | Verification |
| DEC-NEW |  | TBD |  | task Txxx |  | open |  |
```

## 退出检查

- [ ] 所有产品/AIP/迁移/契约关键选择都有决策记录。
- [ ] 没有 `open` 决策进入实现。
- [ ] 每个决策有 source 和 affected modules。
- [ ] 每个决策有 Decision key。
- [ ] Decision Consistency Matrix 没有 open conflict。
- [ ] 所有 superseded 决策都有 superseded-by，并触发 backflow invalidation。
- [ ] 每个决策有验证方式或说明为何不可直接验证。
- [ ] 每个决策有 alternatives，除非它是用户或产品直接约束。
