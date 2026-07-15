# Atomic Task Decomposition

## Contract Granularity Admission Matrix

| Txxx | Contract / matrix row | Semantic type | Required details copied into packet | Missing detail | Backflow target | Admission |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## Contract Edge Decomposition Matrix

| Edge ID | Source contract / row | Sub-obligation | From -> To | Operation / surface | Semantic type | Canonical owner | Owner module | Consumer module(s) | Provider guarantee to create/preserve | Consumer assumption to use | Failure / timing detail | State/resource owner | Verification proof | Candidate task owner |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|  |  | provider guarantee / consumer assumption / failure path / timing / resource-state owner / verification proof |  |  |  | authoritative owner role | MOD-xxx |  |  |  |  |  |  | Txxx / proof-only / locked N/A |

## Mechanism Row To Task Map

| Mechanism row | Design model row type | Contract obligation | Verification | Candidate owner module | Candidate Txxx | Packet execution section | Merge/split decision | Backflow if not executable |
|---|---|---|---|---|---|---|---|---|
| MECH-xxx / OPSEQ-xxx / EXTAPI-xxx / EVT-xxx / RMM-xxx / RLM-xxx / FCM-xxx / MIM-xxx | mechanism / sequence / external-parameter / event-state / runtime-materialization / resource-lifecycle / failure-consistency / module-interface | C-xxx-OBL-xxx | VER-xxx |  | Txxx / proof-only / locked N/A | behavior_details / stateful_behavior / external_side_effects / runtime_materialization / managed_resource_ownership / implementation_steps / verification | split / merge with same module+semantic type+operation+short verification proof | design / contract / verification |

## Provider Consumer Task Decision Matrix

| Edge row | Provider task needed? | Provider task / existing task | Consumer task needed? | Consumer task / proof-only | Reason | Regression / acceptance proof |
|---|---:|---|---:|---|---|---|
|  |  |  |  |  |  |  |

## Owner Legitimacy Matrix

| Edge row | Row kind | Edge type | Canonical owner | Owner module | Proposed provider task | Proposed task primary module | Owner legitimacy | If not provider: carrier/proof edge | Backflow if invalid |
|---|---|---|---|---|---|---|---|---|---|
| C-xxx-OBL-xxx / ESE-xxx / PCP-xxx / RMM-xxx | provider guarantee / consumer assumption / failure/timing / verification proof / carrier-only / locked N/A | semantic_contract_edge / carrier_order_edge / verification_prerequisite_edge / proof_only_edge | authoritative state/schema/resource/event/UI role | MOD-xxx | Txxx / proof-only / locked N/A | MOD-xxx | valid-owner / carrier-only / proof-only / invalid-backflow | Txxx -> Tyyy with carrier_order_edge / verification_prerequisite_edge / proof_only_edge | contract / verification / task-planning backflow |

## Task Merge Split Decision Matrix

| Candidate rows | Proposed Txxx | Owner legitimacy passed for all rows? | Same primary module? | Same semantic type? | Same operation/surface? | Same short verification? | Decision | Reason / backflow |
|---|---|---:|---:|---:|---:|---:|---|---|
|  |  |  |  |  |  |  |  |  |

## Provider Ownership Propagation Check

| Txxx | Task DAG provides/provides_obligations | Packet provided_contract_obligations | Compiled issue provider claims | Carrier/proof refs moved to consumed/precondition/proof sections | Result / backflow |
|---|---|---|---|---|---|
| Txxx | C-xxx / C-xxx-OBL-xxx | exact same set only | exact same set only; no stale owns/provides text | API wire / DTO / frontend / fixture / harness refs use typed edge, not provider claim | pass / backflow to packet regeneration |

## Proof Owner Allowlist Matrix

| Verification row | Owner Txxx | Proof file/path | Fixture/support file/path | Source topology row | Added to packet files_to_change? | Added to task-dag files? | Required freshness/build step | Backflow if missing |
|---|---|---|---|---|---:|---:|---|---|
|  |  |  |  |  |  |  |  |  |

## Semantic Load Split Matrix

| Candidate Txxx | Primary module count | Touched layers | Provider side-effect owners | State/event/progress producers | Readback/consumer owners | Verification loops | Cross-module build/test? | Split required? | Merge rationale / backflow |
|---|---:|---|---|---|---|---|---:|---:|---|
|  |  |  |  |  |  |  |  |  |  |
