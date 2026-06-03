# Atomic Issue Standard

An Atomic Issue is the final execution packet for an AI coding agent.

It should be possible to paste an Atomic Issue into a GitHub issue and assign it
to an agent without requiring the agent to reread the entire PRD, architecture
proposal, plan, or contract library.

## Required Properties

An Atomic Issue must:

- bind to exactly one primary module, unless it is a pure contract verification issue;
- state execution preconditions;
- copy consumed contract snapshots;
- copy provided contract obligations;
- list invariant carryover;
- list forbidden re-decisions;
- define file scope or precise file discovery rules;
- provide ordered file-level implementation steps;
- include verification commands or manual steps;
- include expected results;
- explain what failure means;
- define what to do if preconditions fail.

## Minimum Sections

```markdown
# Txxx: Title

## Primary Module

## Goal

## Execution Preconditions

## Consumed Contract Snapshot

## Provided Contract Obligation

## Locked Decisions

## Invariant Carryover

## Semantic Carriers

## Files To Change

## Implementation Steps

## Verification

## Forbidden Re-decisions

## If Preconditions Fail
```

## Anti-Patterns

The following are not Atomic Issues:

- "Implement backend API."
- "Add frontend support."
- "Follow the PRD."
- "Refer to C001."
- "Use existing pattern" without naming the reference files and constraints.
- "Run tests" without expected results and proof target.
- A task that spans multiple independent state machines.
- A task that changes provider and consumer contracts at the same time.

## Rule of Thumb

If the worker must make a new product, architecture, field, error, UI,
compatibility, or validation decision, the issue is not atomic.

If the worker must read the full global design to understand the task, the issue
is not atomic.

If the worker cannot validate the result in a short loop, the issue is not
atomic.

