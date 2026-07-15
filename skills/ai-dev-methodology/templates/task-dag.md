# Task DAG

> 本图证明 Atomic Issues 的顺序不是自然语言排序，而是由 contract provider/consumer、文件 ownership 和 verification gate 决定。

## DAG Nodes

| Task | Primary module | Layer | Provides contracts | Consumes contracts | Files owned | Verification gate | Status |
|---|---|---|---|---|---|---|---|
| T001 |  | backend-domain / API / frontend / terraform / verification | C-xxx | C-yyy |  | VER-xxx | pending |

Provider ownership rule:

- `Provides contracts` is semantic ownership, not participation. A task may list coarse `C-xxx` only when it owns every `semantic_contract_edge` obligation under that contract and those `C-xxx-OBL-yyy` rows are also listed in `task-dag.yaml.tasks[Txxx].provides_obligations`.
- Carrier/order/proof/prerequisite work, including API wire carriers, DTO/request shape, fixtures, build freshness, browser harness, and acceptance proof, must not be listed as `Provides contracts`; use typed DAG edges and packet preconditions/carriers/proof sections instead.

## DAG Edges

| From task | To task | Dependency type | Reason | Can parallel? | Failure propagation if skipped |
|---|---|---|---|---:|---|
| T001 | T002 | semantic_contract_edge / carrier_order_edge / verification_prerequisite_edge / proof_only_edge / file-order / migration-before-code |  | yes/no |  |

## Topological Execution Order

| Order | Task | Why now | Blocked by | Unlocks |
|---:|---|---|---|---|
| 1 | T001 |  | none | T002 |

## Parallel Groups

| Group | Tasks | Disjoint files? | Disjoint contracts? | Shared verification? | Risk |
|---|---|---:|---:|---:|---|
| P1 | T001,T003 | yes/no | yes/no | yes/no |  |

Exit gate:

- [ ] Every task appears as a DAG node.
- [ ] Every consumed contract has an upstream provider task or explicit external provider.
- [ ] Every consumer task is ordered after its provider task and required verification.
- [ ] Parallel tasks have disjoint files and no provider/consumer dependency.
- [ ] No task can fail in a way that silently corrupts a later task input.
