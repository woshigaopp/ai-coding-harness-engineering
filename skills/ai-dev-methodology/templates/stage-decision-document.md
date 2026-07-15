# <阶段名> 决策文档

> 本文档默认使用中文。每个决策必须独立成节，禁止使用 `PDEC-001..022`、`ADEC-001..004`、`C-001..C-006` 这类 range 合并。本文档的目的不是摘要，而是让下游 Atomic Issue 能复制并消费每个决策。

## 来源输入

| Source | Path/URL | Used for |
|---|---|---|
|  |  |  |

## 决策摘要

| ID | Type | Decision key | Question | Final decision | Decided by | Status |
|---|---|---|---|---|---|---|
| DEC-xxx | product/architecture/interface/migration/contract/pattern/validation | stable semantic key |  |  | user-confirmed/ai-recommended/ai-engineering | locked/open/superseded |

## 决策详情

### DEC-xxx: <title>

| Item | Content |
|---|---|
| Question |  |
| Decision key |  |
| Final decision |  |
| Decided by | user-confirmed / ai-recommended / ai-engineering |
| Supersedes / superseded by |  |
| Alternatives considered |  |
| Rejected alternatives and reasons |  |
| Reason for selected decision |  |
| Product constraint alignment | Which PRD/PDEC/REQ/SCN this decision preserves; if it changes product semantics, return to PRD. |
| Affected modules/artifacts |  |
| Downstream Atomic Issue impact | Which Txxx must copy this decision and what exact semantic excerpt they need. |
| Verification | Exact check or verification matrix row; include expected result if known. |
| Feishu/Lark URL |  |

## 开放决策

| ID | Question | Recommended decision | Blocks | Owner | Next step |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Rules:

- Product decisions must be `user-confirmed` or explicitly authorized as `ai-recommended` before PRD is locked.
- `ai-engineering` is allowed only for engineering choices that do not change product-visible behavior, scope, defaults, errors, permissions, or compatibility.
- Every row must also appear in the main Decision Registry.
- If Lark write permission is available, sync this document to Feishu/Lark and record the URL.
- Every Decision Summary row must have exactly one matching `### DEC-xxx` detail section.
- Do not collapse multiple decisions into one detail section.
- Two active decisions cannot answer the same Decision key differently; if a decision changes, mark the old one superseded and record the new one.
- If a decision affects implementation but cannot be copied into an Atomic Issue, it is not complete.
