# AI Coding Harness Engineering

Contract-driven execution for large software features.

This repository presents an English version of a practical harness engineering
methodology for AI coding agents.

The core idea is simple:

> Do not ask AI to guess through a large feature. Compile the feature into
> executable semantic units.

Most AI coding workflows still rely on an interactive loop:

```text
prompt -> code -> review -> fix -> review -> fix
```

That loop works for small, well-scoped tasks. It becomes unreliable for large
features because the agent is forced to infer product decisions, engineering
tradeoffs, hidden constraints, cross-module contracts, and validation criteria
during implementation.

This repository argues for a different shape:

```text
source intake
-> decision surface discovery
-> current-system understanding
-> module boundary validation
-> cross-module contracts
-> verification matrix
-> context rehydration
-> contract-closed Atomic Issues
-> gated execution
-> acceptance and backflow
```

This is harness engineering for AI coding: build the semantic rails, gates, and
feedback loops around the coding agent so that execution happens inside a
reliable region.

## Why This Exists

AI coding agents are already strong at atomic tasks.

The hard question is:

> If AI can solve atomic coding problems well, why does it still fail on large
> features?

The answer is not simply code volume or business complexity.

Large features contain many hidden decision points:

- product behavior;
- API fields;
- state transitions;
- compatibility rules;
- UI behavior;
- permissions;
- runtime lifecycle;
- mock behavior;
- observability;
- cross-module timing and consistency;
- validation criteria.

When these decisions are not explicit, the agent fills the gaps with plausible
answers. Those answers may be locally reasonable but globally wrong.

If the success rate for one clear atomic task is `P`, and a large feature
contains `N` hidden decisions that the agent must infer, the overall success
rate behaves like `P^N`.

The goal of this methodology is to reduce the number of decisions left to the
execution phase.

## Atomic Task

An atomic task is not just a small task.

It is a task that an AI agent can execute without making new decisions.

An atomic task should satisfy four basic conditions:

1. Decisions are already clear.
2. The boundary is clear.
3. The context is self-contained.
4. The result can be validated quickly.

In a large-feature workflow, an atomic task also needs a fifth property:

5. Its output does not become an unverified input to downstream tasks.

In practice, that means an atomic task should be modeled as a contract-closed
unit:

```text
Inside one module,
assuming its consumed contracts already hold,
implement or preserve the provided contract this module owes downstream,
and verify that contract through a short feedback loop.
```

## From Spec-Driven to Harness-Driven

Spec-driven development is a useful step beyond prompt-driven coding.

But in complex systems, a spec is not enough.

A spec may describe the desired behavior, but it does not guarantee that:

- all decision surfaces were discovered;
- old-code constraints were understood;
- module boundaries are valid;
- provider/consumer assumptions are compatible;
- dense semantics were copied into each execution task;
- validation proves the right behavior;
- context survives phase transitions;
- failed validation invalidates downstream artifacts.

This methodology treats specs as input, not as the final control mechanism.

The real control mechanism is the harness:

- structured artifacts;
- module contract graphs;
- semantic carriers;
- context packs;
- validators;
- receipts;
- task admission;
- diff validation;
- acceptance gates;
- backflow invalidation.

## Repository Layout

```text
README.md
methodology/
  core-methodology.md
  atomic-issue-standard.md
harness/
  workflow.md
  gates.md
templates/
  source-intake-ledger.md
  decision-surface-discovery.md
  module-contract-graph.md
  cross-module-contract.md
  verification-matrix.md
  context-pack.md
  atomic-issue.md
  backflow-invalidation.md
examples/
  connect-cluster-infrastructure-selection.md
tools/
  README.md
```

## Core Vocabulary

| Term | Meaning |
|---|---|
| Atomic Task | A self-contained task the agent can execute without new decisions. |
| Atomic Issue | A GitHub-issue-shaped execution packet containing context, decisions, contracts, files, steps, and validation. |
| Module | A responsibility boundary that owns data, state, resources, or lifecycle. |
| Consumed Contract | A contract the current task can assume has already been provided by another module. |
| Provided Contract | A contract the current task must implement or preserve for downstream consumers. |
| Semantic Carrier | Dense semantics that must not be compressed into vague summaries, such as states, fields, errors, selectors, defaults, routes, mock fixtures, and timing. |
| Context Pack | A rehydrated, stage-specific input pack built by rereading canonical artifacts before the next phase. |
| Gate | A hard admission condition that prevents incomplete artifacts from becoming downstream inputs. |
| Backflow | The process of invalidating and regenerating downstream artifacts when a missing decision, contract, or validation is discovered. |

## One-Sentence Summary

AI coding for large features should not be prompt-driven. It should be
contract-driven, context-rehydrated, and gate-validated.

