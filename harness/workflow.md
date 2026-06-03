# Harness Workflow

This workflow turns a large feature into contract-closed Atomic Issues.

It is not a documentation workflow. It is a semantic compilation workflow.

## Phase 1: Source Intake

Register every input before using it:

- user request;
- PRD;
- design proposal;
- issue;
- code path;
- API document;
- external documentation;
- current runtime evidence;
- historical implementation;
- team pattern.

Unread behavior-affecting sources block downstream stages.

## Phase 2: Current-System Understanding

Before designing the new behavior, understand the relevant current system:

- pages;
- APIs;
- state;
- configuration;
- permissions;
- runtime lifecycle;
- errors;
- mocks;
- observability;
- reference patterns.

The workflow must record search seeds, searched paths, evidence, and stop
conditions.

## Phase 3: Decision Surface Discovery

Before locking decisions, discover the surfaces that require decisions.

Common surfaces:

- mode consumer;
- capability;
- frontend action;
- post-create consumer;
- persistent mutation;
- runtime lifecycle;
- mock behavior;
- observability;
- permission;
- compatibility.

Each surface must have an owner stage and one of:

- locked decision;
- contract;
- verification;
- owner Atomic Issue;
- locked N/A.

## Phase 4: Decision Registry

Every decision must become a stable object:

- problem;
- selected option;
- rejected alternatives;
- reason;
- affected modules;
- downstream impact;
- verification.

Conflicting active decisions block execution.

## Phase 5: Module Boundary Validation

Validate module boundaries using:

- data ownership;
- state-machine self-containment;
- external dependency enumerability;
- provided contract enumerability;
- too-large risk;
- too-small risk;
- split/merge/keep decision.

Module boundaries must be justified before cross-module contracts are locked.

## Phase 6: Cross-Module Contracts

For every dependency edge, define:

- trigger;
- normal path;
- failure path;
- consistency;
- timing;
- verification.

Provider guarantees must satisfy consumer assumptions.

## Phase 7: Verification Matrix

Map each requirement, scenario, decision, contract, and migration to proof.

Proof may be:

- unit test;
- integration test;
- API test;
- frontend build or browser check;
- runtime smoke;
- mock drift guard;
- manual acceptance with explicit risk;
- observability proof.

No critical requirement or contract may be marked done without proof.

## Phase 8: Context Rehydration

Before each dense downstream phase, reread canonical artifacts and build a
context pack.

Context packs prevent semantic loss from chat history, memory, and summaries.

Key context packs:

- design context pack;
- contract context pack;
- atomic-planning context pack;
- acceptance context pack.

## Phase 9: Atomic Task Planning

Generate Atomic Issues from the module contract graph.

Each issue must be:

- self-contained;
- contract-closed;
- tied to one primary module;
- ordered by provider/consumer dependencies;
- validated by a short feedback loop.

## Phase 10: Gated Execution

Execution starts only after pre-execution validation passes.

Each task should follow:

```text
admit task
-> edit within allowlist
-> run verification
-> validate diff
-> semantic review
-> pass task
```

## Phase 11: Acceptance and Backflow

Acceptance validates user semantics and runtime behavior.

If acceptance finds a gap, classify the earliest missing stage:

- requirement gap;
- design gap;
- archaeology miss;
- contract miss;
- verification miss;
- task planning miss;
- implementation bug;
- runtime data gap.

Then invalidate downstream artifacts and regenerate them.

