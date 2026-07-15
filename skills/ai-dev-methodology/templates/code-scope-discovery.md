# Code Scope Discovery

> PRD/AIP/design 前的当前项目理解范围协议。目标是证明“已读到与 propose 相关的现状”，不是做完整代码考古。

## Discovery Seeds

| Seed | Source | Search terms / paths | Why relevant |
|---|---|---|---|
|  | Propose / PRD / AIP / user phrase |  |  |

## Search Coverage

| Area | Required? | Search method | Evidence path / command | Finding | Stop condition met? |
|---|---:|---|---|---|---:|
| UI route/page | yes/no | rg / route map / browser |  |  | yes/no |
| API route/client | yes/no | rg path/client/controller |  |  | yes/no |
| Config/schema | yes/no | rg field/schema/Terraform |  |  | yes/no |
| State/status/error | yes/no | rg enum/status/error |  |  | yes/no |
| Permission/visibility | yes/no | rg permission/menu/action |  |  | yes/no |
| Runtime/cloud/task | yes/no | rg task/provider/resource |  |  | yes/no |
| Tests/fixtures | yes/no | rg test/fixture |  |  | yes/no |
| Docs/current specs | yes/no | rg docs/specs/current |  |  | yes/no |

## Current Product/Code Understanding

| Area | Current behavior | Evidence path / command | Product / design implication | Gap / decision |
|---|---|---|---|---|

Exit gate:

- [ ] Every user phrase such as “参考/复用/类似/改造/优化” has at least one evidence path or a documented not-found search.
- [ ] Every required area has `Stop condition met?=yes`.
- [ ] Any conflict between current behavior and propose becomes PDEC/DEC or blocker.
- [ ] Findings are copied into PRD/AIP/design; they are not left only in chat.
