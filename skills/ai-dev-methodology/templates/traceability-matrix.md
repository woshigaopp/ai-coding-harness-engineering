# Traceability Matrix

> 本矩阵用于证明上游语义最终进入契约闭包 issue。`covered` 不是“文档里出现过 ID”，而是必要语义已进入 contract、verification 和 Atomic Issue。

## Source To Issue Coverage

| Source | Covered by contracts / decisions | Verification | Atomic Issue | Status | Gap |
|---|---|---|---|---|---|
| REQ-xxx | SCN-xxx / C-xxx / DEC-xxx | VER-xxx | Txxx | covered/gap |  |
| SCN-xxx | C-xxx / VER-xxx | VER-xxx | Txxx | covered/gap |  |
| DEC-xxx | C-xxx / MIG-xxx / VER-xxx | VER-xxx | Txxx | covered/gap |  |
| C-xxx | Provider Txxx / Consumer Txxx / VER-xxx | VER-xxx | Txxx | covered/gap |  |
| MIG-xxx | VER-xxx | VER-xxx | Txxx | covered/gap |  |

## Source Intake Coverage

| Source ID | Read status | Extracted objects | Covered by | Gap |
|---|---|---|---|---|
| SRC-xxx | read / blocked / ignored / superseded | REQ/SCN/DEC/C/MIG/VER | Txxx / DEC-xxx / C-xxx |  |

## Module To Issue Coverage

| Module | Responsibility | Provided contracts | Consumed contracts | Atomic Issues | Boundary validation | Gap |
|---|---|---|---|---|---|---|
|  |  | C-xxx | C-xxx | Txxx | passed / risk accepted |  |

## Contract Closure Coverage

| Contract | Provider module | Provider issue | Consumer module(s) | Consumer issue(s) | Composition verification | Excerpt copied into issues? | Gap |
|---|---|---|---|---|---|---:|---|
| C-xxx |  | Txxx |  | Txxx | VER-xxx | yes/no |  |

## Requirement Composition Coverage

| REQ/SCN | Module composition path | Provided contracts proving it | Verification | Atomic Issue(s) carrying proof | Gap |
|---|---|---|---|---|---|
| REQ-xxx / SCN-xxx | ModuleA -> ModuleB | C-xxx | VER-xxx | Txxx |  |

Exit gate:

- No behavior-affecting source is missing from Source Intake Coverage.
- No `gap` rows before Atomic Execution.
- Every core module appears in Module To Issue Coverage.
- Every Contract appears in at least one Atomic Issue.
- Every consumed contract has a provider contract and a consumer issue that states the assumption.
- Every critical REQ/SCN has composition coverage; module-local proof alone is insufficient.
- Every Atomic Issue has at least one Verification row with expected result and proves.
