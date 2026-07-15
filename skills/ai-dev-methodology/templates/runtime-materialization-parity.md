# Runtime Materialization Parity

Use this when a requirement adds, replaces, refactors, or scopes a
deployment/runtime mode, runtime substrate, execution environment, runner,
provider backend, VM/container/orchestrator, bootstrap path, or
plugin/config/secret injection path.

This artifact proves product capability parity. A resource, process, pod, VM,
ASG, deployment, or final success state is not enough.

## Runtime Mode Change Classification

| Decision ID | Source | Existing mode(s) | New / changed mode | Classification | Evidence | Locked decision | Owner stage |
|---|---|---|---|---|---|---|---|
| DESIGN-DEC-xxx | REQ-xxx / ADEC-xxx | existing mode name | new or changed mode name | Additive coexisting mode / Replacement / retirement / Internal substrate refactor / Capability reduction / scoped mode | code/source evidence | locked decision text or decision gap | PRD/AIP/design/migration |

## Product Capability Parity Matrix

| Capability ID | Product capability | Existing mode baseline | New / changed mode obligation | Supported? | If not supported, product/API/UI expression | Contract ID | Verification ID | Owner issue |
|---|---|---|---|---|---|---|---|---|
| RMP-CAP-001 | create runtime worker | existing mode renders config/plugins/secrets/bootstrap and starts workers | new mode must materialize equivalent config/plugins/secrets/bootstrap before ready | yes | N/A | C-xxx | VER-xxx | Txxx |

## Runtime Materialization Mapping

| Mapping ID | Mode | Capability input | Existing mode materialization evidence | New / changed mode materialization design | Production owner | Required files/modules | Failure semantics | Verification | Owner issue |
|---|---|---|---|---|---|---|---|---|---|
| RMP-MAP-001 | new mode | Product config | existing mode renderer / manifest / startup path | new mode renders equivalent config into runtime-readable path | production manager/task/runtime module | exact repo-relative files/modules | typed failed state/event/readback when config cannot be materialized | test/readback proves runtime uses rendered config | Txxx |

Capability inputs that must be considered when applicable:

- Runtime artifact.
- Product config.
- Plugins/extensions.
- Secrets/security config.
- Dependency endpoints.
- Local filesystem/volumes.
- Bootstrap/entrypoint.
- Lifecycle operations.
- Readback/observability.

## Runtime Parity Negative Assertions

| Assertion ID | Forbidden shortcut | Why invalid | Detection proof | Backflow target |
|---|---|---|---|---|
| RMP-NEG-001 | Resource created but product config/plugins/secrets are not materialized | Resource existence does not prove runtime capability | Runtime config/plugin/secret readback or startup failure assertion | design/contract/task-planning |
| RMP-NEG-002 | Image/AMI/container is assumed to contain required plugins/config/secrets without a locked source | Hidden runtime artifact assumptions create false success | Source-backed artifact manifest or runtime readback proof | AIP/design/contract |

## Runtime Materialization Local Audit

| Mapping ID | Auditor finding | Missing product capability input | Missing production owner | Missing readback/observability proof | Required backflow | Blocks next stage |
|---|---|---|---|---|---|---:|
| RMP-MAP-xxx | none | none | none | none | none | no |
