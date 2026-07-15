# Semantic Consumption Matrix

> 本表证明每个阶段没有丢失上游语义。后续阶段不能靠回读 PRD/plan 补语义；必须把需要的语义消费、派生、复制或明确丢弃。

## Upstream Semantic Inventory

| Upstream object | Type | Source artifact | Required downstream? | Core semantics |
|---|---|---|---:|---|
| REQ-001 / SCN-001 / PDEC-001 / DEC-001 / C-001 / MIG-001 / VER-001 | requirement / scenario / product-decision / engineering-decision / contract / migration / verification | proposal/spec/plan/tasks/decision-reviews | yes/no |  |

## Stage Consumption Matrix

| Upstream object | Consuming stage | Required by stage? | How consumed | Derived object | Copied semantics | Dropped semantics | Drop reason / decision | Verification / gate | Status |
|---|---|---:|---|---|---|---|---|---|---|
| REQ-001 | new-feature-design / code-archaeology / contract / verification / task-planning | yes/no | transformed / copied / verified / N/A / blocked | DESIGN-DEC-xxx / C-xxx / VER-xxx / Txxx |  |  | DEC-xxx / N/A because... |  | consumed / dropped-with-decision / blocked |

## Downstream Semantic Handoff

| Derived object | Carries upstream objects | Semantics copied into downstream artifact? | Next consumer | Handoff risk |
|---|---|---:|---|---|
| C-001 / VER-001 / T001 | REQ-001,PDEC-001 | yes/no | verification-matrix / atomic-task-planning / atomic-execution |  |

Exit gate:

- [ ] Every upstream object appears in Stage Consumption Matrix.
- [ ] Every `Required downstream?=yes` object is consumed, transformed, verified, or blocked.
- [ ] `Dropped semantics` is empty unless `Drop reason / decision` cites a locked decision.
- [ ] Every derived object lists the upstream objects it carries.
- [ ] Every Atomic Issue receives copied semantics; it may cite PRD IDs for audit, but not depend on PRD text for execution.
- [ ] No row remains `blocked` when entering the next stage.
