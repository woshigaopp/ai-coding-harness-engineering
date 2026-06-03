# Gates

Gates prevent uncertainty from pretending to be progress.

Candidate artifacts are not downstream inputs.

An artifact can be consumed downstream only when it has passed the relevant
gate, including required content, validation, and receipt.

## Gate Principles

- A document with headings is not enough.
- IDs without copied semantics are not enough.
- A partial packet is not enough.
- A compiler check is not an execution admission gate.
- A local test that proves the wrong thing is not enough.
- A manually edited "passed" status is not enough.

## Required Gate Types

| Gate | Purpose |
|---|---|
| Source intake gate | Prevent unread behavior-affecting inputs. |
| Decision surface gate | Prevent unnoticed decisions from entering execution. |
| Decision consistency gate | Prevent conflicting active decisions. |
| Module boundary gate | Prevent subjective or invalid module splits. |
| Module composition gate | Prove modules compose into requirements. |
| Contract materialization gate | Ensure tasks copy contracts, not just IDs. |
| Dense semantic carrier gate | Ensure dense semantics are assigned to owner tasks. |
| Verification feasibility gate | Ensure proof exists and is executable. |
| Context rehydration gate | Ensure downstream phases read canonical artifacts. |
| Pre-execution gate | Ensure all Atomic Issues are sealed before code changes. |
| Task admission gate | Ensure each task edits only its allowed scope. |
| Acceptance gate | Ensure user semantics and runtime behavior are proven. |
| Backflow gate | Ensure changed decisions invalidate downstream artifacts. |

## Backflow

Backflow is not a failure state.

Backflow means the workflow found an uncertainty that cannot safely continue
downstream.

The correct response is to return to the earliest missing stage, repair the
artifact, invalidate affected downstream objects, and rerun the required gates.

