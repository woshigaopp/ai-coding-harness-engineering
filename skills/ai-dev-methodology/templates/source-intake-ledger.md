# Source Intake Ledger

> 本表是进入 PRD/AIP/design/contract 前的输入完整性门禁。任何用户提供或 workflow 发现的输入，都必须登记读取状态和下游映射。

## Source Inventory

| Source ID | Type | Path / URL / origin | Provided by | Read status | Read method | Used for | If unread, reason | Follow-up |
|---|---|---|---|---|---|---|---|---|
| SRC-001 | requirement / AIP / Feishu / issue / code / API / Terraform / design / runtime evidence |  | user / repo / lark / web / runtime | read / unread / blocked / irrelevant / superseded | local file / lark-cli / browser / rg / command | PRD / AIP / DEC / REQ / SCN / C / MIG / VER |  |  |

## Source To Semantic Object Map

| Source ID | Extracted object | Extracted semantics | Target artifact | Status | Gap / conflict |
|---|---|---|---|---|---|
| SRC-001 | REQ-xxx / SCN-xxx / DEC-xxx / C-xxx / MIG-xxx / VER-xxx |  | proposal/spec/plan/tasks/atomic-issues | mapped / conflict / ignored / blocked |  |

## Source Conflict Matrix

| Conflict | Source A | Source B | Conflicting semantics | Decision required | Resolution DEC | Status |
|---|---|---|---|---|---|---|
|  | SRC-xxx | SRC-yyy |  | yes/no | DEC-xxx | open/locked |

Exit gate:

- [ ] Every user-provided URL/path/document/issue/code reference appears in Source Inventory.
- [ ] No `unread` or `blocked` source is used as if it were read.
- [ ] Every source that affects behavior maps to REQ/SCN/DEC/C/MIG/VER or is explicitly ignored with reason.
- [ ] Every conflict has a locked decision before Atomic Task Planning.
