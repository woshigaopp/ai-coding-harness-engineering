# Txxx: Title

## Primary Module

## Goal

## Execution Preconditions

## Consumed Contract Snapshot

Copy the executable semantics of each consumed contract. Do not only reference
contract IDs.

## Provided Contract Obligation

Describe the observable guarantees this task must provide downstream.

## Locked Decisions

Copy the relevant decisions and their effect on this task.

## Invariant Carryover

List existing behavior that must not change.

## Semantic Carriers

List dense semantics such as fields, states, errors, routes, selectors, defaults,
mock fixtures, timing, idempotency, and failure meanings.

## Files To Change

| File / Discovery Rule | Reason |
|---|---|
|  |  |

## Implementation Steps

1. 
2. 
3. 

## Verification

| Step | Command / Action | Expected Result | Proves | Failure Meaning |
|---|---|---|---|---|
| 1 |  |  |  |  |

## Forbidden Re-decisions

- Do not change product behavior.
- Do not redefine consumed contracts.
- Do not expand file scope without backflow.

## If Preconditions Fail

Stop execution and backflow to the earliest missing stage.

