# Stateful Behavior Matrix

Use this when a requirement or contract contains lifecycle, progress, event,
status, terminal, polling, retry, task step, change tracking, mock state graph,
or user-visible state semantics.

## Stateful Behavior Inventory

| Behavior ID | Source objects | Owner module | State owner | Producer | Consumers | Verification | Status |
|---|---|---|---|---|---|---|---|
| SB-xxx | REQ-xxx / C-xxx |  |  |  |  | VER-xxx | locked |

## State Transition Rows

| Row ID | Behavior ID | Operation | Mode/variant | From state | Trigger | Guard/precondition | Event/step | User-visible label/key | Status | To state | Terminal | Retry/idempotency | Side effects | Failure event/reason | Forbidden inherited behavior | API/event fields | Frontend assertion | Mock fixture ref | Verification |
|---|---|---|---|---|---|---|---|---|---|---|---:|---|---|---|---|---|---|---|---|
| SBR-xxx | SB-xxx | create | asg | accepted | task starts | resolved compute exists | CREATE_ASG_RUNTIME | connect.progress.asg.createRuntime | running | creating | no | retry keeps cluster id | InstanceChange written | CREATE_ASG_RUNTIME_FAILED + reason | no K8s pod wording | deploymentMode, step, status, reason, terminal | progress keeps polling | fixture-create-asg-running | VER-xxx |

## Transition Coverage

| Coverage ID | Behavior ID | Required operations | Required modes/variants | Required statuses | Required terminal states | Full coverage required for | Representative-only allowed for | Omitted combinations | Coverage decision |
|---|---|---|---|---|---|---|---|---|---|
| SBC-xxx | SB-xxx | create/update/delete | k8s/asg | queued/running/success/failed/blocked | success/failed/blocked | user-reachable transitions, terminal states, failure states | weak display variants with N/A decision | none | full |

## Consumer Matrix

| Consumer ID | Behavior ID | Consumer | Consumed rows | Must show | Must hide | Terminal behavior | Fixture refs | Verification |
|---|---|---|---|---|---|---|---|---|
| SB-CONS-xxx | SB-xxx | Frontend progress page | SBR-xxx | mode-specific label, typed reason | old-mode resource names | stop polling at terminal | fixture-create-asg-running | VER-xxx |

## Local Audit Report

| Behavior/row | Auditor finding | Missing transition | Missing consumer/fixture | Missing verification | Required backflow | Blocks next stage |
|---|---|---|---|---|---|---:|
