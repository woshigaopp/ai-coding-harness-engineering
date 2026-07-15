# C-xxx: <contract title>

| Field | Value |
|---|---|
| Source | REQ/SCN/DEC/MIG/HiddenConstraint |
| Type | Public API / Frontend-Backend / DB / Async Task / Event / Deployment / Cloud / Terraform / Observability / Derived Configuration |
| Provider module |  |
| Consumer module(s) |  |
| Modules/resources |  |
| Decision | DEC-xxx or N/A |
| Status | locked / needs-human-decision / blocked-by-missing-info |

## Semantics

| Question | Answer |
|---|---|
| Trigger |  |
| Normal path |  |
| Failure path |  |
| Consistency |  |
| Timing |  |
| Verification |  |

## Provider / Consumer Assumptions

| Contract | Provider module | Provider guarantee | Consumer module | Consumer assumption | Mismatch decision | Verification |
|---|---|---|---|---|---|---|
| C-xxx |  |  |  |  | none/contract-updated/consumer-updated/blocked |  |

## Contract Executable Obligation Matrix

| Contract | Sub-obligation ID | Edge | Edge type | Sub-obligation type | Semantic type | Operation / surface | Canonical owner | Fields/resource/state | Provider guarantee | Consumer assumption | Failure / timing detail | State/resource owner | Owner module | Verification proof | Split hint |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C-xxx | C-xxx-OBL-001 | MOD-A -> MOD-B | semantic_contract_edge / carrier_order_edge / verification_prerequisite_edge / proof_only_edge | provider guarantee / consumer assumption / failure path / timing / resource-state owner / verification proof | Wire/API shape / State machine / External side effect / Resource ownership / custom:<name> | single operation or surface | authoritative state/schema/validation/resource writer/event producer/UI action owner | concrete field/resource/state/event/readback surface |  |  |  |  |  |  | provider task / consumer task / proof-only / locked N/A |

The same rows must also be copied into `contracts.yaml.contracts[C-xxx].executable_obligations` using matching `obligation_id` values. `C-xxx` can remain the composition contract ID, but task planning may only generate provider tasks from owner-single `C-xxx-OBL-yyy` rows.

`Provider module` must be owner-single. Do not write `MOD-A / MOD-B`, comma-separated modules, `MOD-A and MOD-B`, frontend proof owners, or acceptance proof owners in this field. If one coarse `C-xxx` contains several owners, keep `Provider module` empty or assign it only to the single semantic provider, and split the actual executable semantics into owner-single `C-xxx-OBL-yyy` rows.

Column integrity rule: the table has exactly 16 columns. `Edge type` is only one of `semantic_contract_edge`, `carrier_order_edge`, `verification_prerequisite_edge`, `proof_only_edge`. Do not repeat that value in `Sub-obligation type`, `Semantic type`, `Operation / surface`, `Canonical owner`, or `Owner module`.

Provider row rule: only `semantic_contract_edge` + `Sub-obligation type=provider guarantee` can become task `provides` / `provides_obligations`. `semantic_contract_edge` + `consumer assumption` / `verification proof` / `carrier-only` is invalid; use carrier/proof edge types for non-provider rows.

`Canonical owner` is a semantic owner role such as state writer, resource writer, event producer, or UI action owner. `Owner module` is the concrete module ID such as `MOD-ASG-RUNTIME`. Do not write `VER-*`, task IDs, proof names, or semantic roles in `Owner module`.

## Type-Specific Details

For Public API / Frontend-Backend:

| Field | Value |
|---|---|
| Exact method/path/query/body |  |
| Frontend caller |  |
| Backend handler |  |
| Auth/permission behavior |  |
| Unauthenticated route smoke | Expected auth error, not 404 |
| Null/unknown/unavailable behavior |  |

For Derived Configuration:

| Target field | Source of truth | Missing behavior | Error semantics | Verification fixture |
|---|---|---|---|---|

## Atomic Issue Mapping

| Contract | Provider issue | Consumer issue(s) | Verification issue/check | Required excerpt copied? |
|---|---|---|---|---:|
| C-xxx | Txxx | Txxx |  | yes/no |
