# Core Methodology

## The Central Problem

AI agents can produce impressive code for narrow, well-scoped tasks. They fail
more often on large features because large features contain hidden decisions and
cross-module semantic constraints.

The failure pattern is not usually "the model cannot write code."

The failure pattern is:

```text
the model is asked to implement while still needing to decide
```

Those decisions may include product behavior, API shape, error semantics,
runtime lifecycle, UI state, compatibility, mock behavior, permissions, and
validation strategy.

When these decisions are left implicit, the agent guesses.

The methodology therefore aims to prevent one thing:

> Do not let uncertain semantics enter the execution phase.

## P^N Decay

Assume an AI agent has success probability `P` on one clear atomic task.

If a large feature contains `N` unresolved semantic choices, the overall chance
of completing the feature correctly behaves like `P^N`.

This is not a formal proof. It is a useful engineering model.

Even high local accuracy decays quickly when the number of hidden decisions
grows.

The solution is not simply to improve prompts. The solution is to reduce the
number of decisions left to execution.

## N1 and N2

Large-feature complexity can be split into two categories.

| Type | Meaning | Optimization |
|---|---|---|
| N1 | Local implementation work inside a module. | Convert into atomic tasks with clear context and short validation. |
| N2 | Cross-module semantic constraints required by the problem domain. | Make them explicit as contracts and verify them. |

The theoretical goal is not zero convergence.

The goal is to eliminate avoidable N1 convergence and leave only the unavoidable
N2 constraints that must be managed explicitly.

## Module Contract Graph First

A large feature should not be decomposed directly into checklist tasks.

Checklist decomposition often looks like this:

```text
modify backend API
modify frontend page
add mock data
add tests
run acceptance
```

This does not define what connects the tasks.

The right intermediate representation is a module contract graph.

Each module must define:

- owned data, state, resources, and lifecycle;
- internal invariants;
- provided contracts;
- consumed contracts;
- verification responsibility.

Each edge between modules must define:

- trigger;
- normal path;
- failure path;
- consistency;
- timing;
- verification.

Only after this graph exists can Atomic Issues be generated reliably.

## Decision Prepositioning

Execution-phase decisions are a reliability risk.

Before implementation, the workflow must lock:

- product decisions;
- architecture decisions;
- interface decisions;
- migration decisions;
- compatibility decisions;
- contract decisions;
- validation decisions;
- pattern decisions.

If a decision is still open, the workflow should block or backflow to the
earliest missing stage.

## Semantic Consumption

Upstream semantics must not live only in global documents.

Each stage must prove that upstream objects were consumed, transformed, copied,
verified, or explicitly dropped with a locked reason.

Examples of upstream objects:

- requirements;
- scenarios;
- product decisions;
- architecture decisions;
- contracts;
- migration decisions;
- verification objects.

By the time an Atomic Issue is generated, the issue must copy the execution
semantics it needs. It may reference upstream IDs for traceability, but it must
not rely on the worker rereading all global artifacts.

## Dense Semantic Carriers

Some semantics are too dense to summarize safely.

Examples:

- selector/default/auto-create behavior;
- forbidden raw-text paths;
- field ownership and compatibility;
- action -> route -> component -> API -> feedback flows;
- explicit failure vs unknown/warning;
- error codes;
- permissions;
- status transitions;
- terminal states;
- mock fixtures;
- runtime lifecycle;
- partial failure;
- retry and idempotency.

These semantics must be materialized as semantic carriers and copied into the
Atomic Issues that own them.

Vague summaries such as "follow existing pattern" or "support selectors" are
not sufficient.

