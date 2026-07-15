# Backflow Invalidation Matrix

> 当 PRD/AIP/archaeology/contract/verification/acceptance 发现 gap 或决策变化时，本表决定哪些产物失效、哪些 issue 必须重写、哪些验证必须重跑。

## Backflow Trigger

| Trigger ID | Found in | Finding category | Description | Earliest missing stage | Required backflow |
|---|---|---|---|---|---|
| BF-001 | implementation / verification / product acceptance / review | prd-missing-decision / aip-design-gap / archaeology-miss / contract-gap / verification-gap / implementation-bug / runtime-data-gap |  | PRD / AIP / archaeology / contract / verification / task / deployment |  |

## Invalidation Matrix

| Trigger ID | Invalidated artifacts | Invalidated decisions | Invalidated contracts | Invalidated Atomic Issues | Verification to rerun | New status |
|---|---|---|---|---|---|---|
| BF-001 | proposal/spec/plan/tasks/atomic-issues/acceptance | DEC-xxx | C-xxx | Txxx | VER-xxx | blocked / pending-rewrite / pending-rerun |

## Supersession Record

| Old object | New object | Reason | Copied semantics? | Review required |
|---|---|---|---:|---:|
| DEC-xxx / C-xxx / Txxx / VER-xxx | DEC-yyy / C-yyy / Tyyy / VER-yyy |  | yes/no | yes/no |

Exit gate:

- [ ] No superseded DEC/C/T/VER remains referenced by active Atomic Issues.
- [ ] Every affected issue is marked blocked/pending until rewritten.
- [ ] Every affected verification is rerun or recorded as Not Run risk with owner.
- [ ] Product acceptance cannot pass while P0/P1 backflow triggers remain open.
