# Verification Matrix

> 本文件默认使用中文。验证矩阵不仅证明单个模块正确，还必须证明模块边界合理、模块组合后满足 REQ/SCN。

## Source Verification Matrix

| Source | Behavior / contract | Verification type | Command / manual step | Expected result | Proves | Required before merge | Risk if not run |
|---|---|---|---|---|---|---:|---|
| REQ-xxx / SCN-xxx / DEC-xxx / C-xxx / MIG-xxx |  | unit/integration/api-route/frontend/runtime/manual/docs |  |  |  | yes/no |  |

## Module Boundary Validation Matrix

> 验证“模块为什么这样切”。只列模块表不算完成；必须证明所有权、状态机、契约可枚举性和粒度决策。

| Module | Boundary decision | Ownership evidence / proof | State-machine proof | Contract enumerability proof | Granularity risk | Command / manual step | Expected result | Risk if not run |
|---|---|---|---|---|---|---|---|---|
|  | keep/split/merge |  |  | consumed/provided contracts enumerable | too-large / too-small / none |  |  |  |

## Module Composition Verification Matrix

> 验证“模块各自正确以后，组合起来是否满足用户需求”。模块内部单测不能替代这一表。

| REQ/SCN | Composition path | Provider contracts | Consumer assumptions | Verification type | Command / manual step | Expected result | Proves |
|---|---|---|---|---|---|---|---|
| REQ-xxx / SCN-xxx | ModuleA -> ModuleB -> ModuleC | C-xxx | ModuleA assumes C-xxx normal/failure/timing semantics | integration/e2e/browser/runtime/manual |  |  | provider output satisfies consumer input and REQ/SCN holds |

## Representative Fixture / Runtime Smoke

| Source object | Required real-ish fields | Missing-field case | Verification | Expected result | Risk if skipped |
|---|---|---|---|---|---|

## Not Run

| Check | Source | Reason | Risk | Severity | Owner / approval | Blocks done? |
|---|---|---|---|---|---|---:|
|  | REQ/SCN/C/VER |  |  | P0/P1/P2/P3 |  | yes/no |

## Exit Gate

- [ ] 每个 REQ/SCN/DEC/C/MIG 都有 proof 或明确 Not Run risk。
- [ ] 每个核心模块都有 Module Boundary Validation；没有 `needs-review`、`unknown` 或空 decision。
- [ ] 每个关键 REQ/SCN 都有 Module Composition Verification，或明确 Not Run risk 和 owner。
- [ ] 每个 consumed contract 都能追溯到 provider contract。
- [ ] 每条组合验证都能复制进对应 Atomic Issue 或独立验证 issue。
- [ ] 任何 P0/P1 或 `Blocks done=yes` 的 Not Run 项都阻塞完成声明。
