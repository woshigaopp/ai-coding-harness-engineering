# Progress / Change Producer Chain Matrix

Use this whenever old code, requirement, or frontend/API surface contains
progress, change tracking, last-change, change detail, task steps, event steps,
terminal polling, or user-visible operation status. This matrix locks the
production write/readback chain. Mock fixtures can mirror it, but cannot replace
the production producer.

## Progress / Change Producer Chain Matrix

| Chain ID | Object/action | Variant | Mutation API / entrypoint | Canonical change writer | State owner / table | Task/event producer | Correlation key | Write timing | Last-change readback | Change detail readback | Frontend/mock consumer | Terminal / polling rule | Failure behavior | Verification | Owner issue |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PCP-001 | ConnectCluster/create | asg | `POST /connect/clusters` | `InstanceChange` writer or locked alternative | change/task tables | create task steps/events | `clusterId -> changeId` | before/while runtime side effect starts | `/last-change` non-empty for same cluster id | `/changes/{changeId}` has ASG create steps | progress page, mock fixture | terminal stops polling | failed step with reason | same-id API proof | Txxx |

## Producer Chain Equivalence Matrix

| Equivalence row | Existing variant chain | New variant chain | Equivalent consumer assumption | Allowed difference | Forbidden shortcut | Verification |
|---|---|---|---|---|---|---|
| PCE-001 | k8s create change/task steps | asg create change/task steps | `/last-change` returns current create change | step names and provider details | fixture-only progress or DB-only final state | same created id readback |

## Producer Chain Local Audit

| Chain row | Auditor finding | Missing writer | Missing correlation | Missing API readback | Fixture-only risk | Required backflow | Blocks next stage |
|---|---|---|---|---|---|---|---|
| PCP-xxx | none | none | none | none | none | none | no |
