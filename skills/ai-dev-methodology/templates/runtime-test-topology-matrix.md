# Runtime Test Topology Matrix

Use this during archaeology and verification planning when a proof crosses
runtime modules, Maven/Gradle modules, generated artifacts, local SNAPSHOTs,
browser bundles, packaged playground images, or representative no-cloud
fixtures. It locks the proof owner files and freshness prerequisites before
Atomic Task Planning.

## Runtime Test Topology Matrix

| Topology ID | Behavior/contract | Production path | Proof module/package | Proof file/path | Fixture/support files | Required build/install/freshness step | Why this proof owner is necessary | Staleness risk if skipped | Verification command | Expected result | Owner issue |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RTT-001 | C-xxx runtime side effect | service manager -> runtime task/provider | runtime module tests | `services/runtime/src/test/...Test.java` | fixture paths | build/install producer module before runtime proof | service-only test cannot observe final runtime manifest/provider boundary | runtime module may use stale local artifact | exact test command | BUILD SUCCESS and assertions | Txxx |

## Proof Owner File Matrix

| Verification ID | Owner issue | Proof file/path | Must be in task-dag files? | Must be in packet files_to_change? | Fixture/support file | Reason | Status |
|---|---|---|---:|---:|---|---|---|
| VER-xxx | Txxx | `services/.../Test.java` | yes | yes | N/A | behavior proof must be allowed before execution | planned |

## Freshness Local Audit

| Topology ID | Auditor finding | Missing build/install step | Missing proof file allowlist | Missing fixture file allowlist | Required backflow | Blocks task planning |
|---|---|---|---|---|---|---:|
| RTT-xxx | none | none | none | none | none | no |
