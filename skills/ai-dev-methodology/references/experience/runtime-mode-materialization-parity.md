# Runtime Mode Materialization Parity

This reference covers one problem shape: a requirement adds, replaces, or
refactors a deployment/runtime mode while expecting the product capability to
remain coherent. It is not specific to Connect, ASG, K8s, Docker, VM, or any
repository.

Do not load this file for ordinary field, UI, or CRUD changes. Load it only when
the requirement or current code suggests a runtime substrate, deployment mode,
execution environment, runner, provider backend, VM/container/orchestrator,
bootstrap path, plugin/config/secret injection path, or lifecycle controller is
being added or changed.

## Contents

- [First Classify The Change](#first-classify-the-change)
- [What Must Be Proven](#what-must-be-proven)
- [Required Artifact](#required-artifact)
- [Runtime Mode Change Classification](#runtime-mode-change-classification)
- [Product Capability Parity Matrix](#product-capability-parity-matrix)
- [Runtime Materialization Mapping](#runtime-materialization-mapping)
- [Runtime Parity Negative Assertions](#runtime-parity-negative-assertions)
- [Consumption Requirements](#consumption-requirements)
- [Invalid Shortcuts](#invalid-shortcuts)
- [Backflow Rule](#backflow-rule)

## First Classify The Change

Before design or task planning, classify the runtime mode change. If the
classification is unclear, mark a product/architecture decision gap. Do not let
the implementation worker decide.

| Change type | Meaning | Default protection |
|---|---|---|
| Additive coexisting mode | A new mode is added beside an existing mode, and both remain user-visible or supported. | Existing mode is protected. Use it as a product-capability parity baseline, not as code to delete or replace. |
| Replacement / retirement | The requirement explicitly retires an old mode or moves users from old mode to new mode. | Requires locked PRD/AIP/MIG decisions for user impact, compatibility window, data migration, rollback, old entry removal, and observability. |
| Internal substrate refactor | Product-visible mode stays the same, but the implementation substrate changes. | API/UI/status/product semantics must stay unchanged unless explicitly decided. |
| Capability reduction / scoped mode | New or changed mode intentionally supports fewer capabilities. | Missing capability must be product-visible: hidden, disabled, rejected by API, or documented as Not Supported with verification. Silent partial support is invalid. |

If the requirement does not explicitly say replacement/retirement, default to
`Additive coexisting mode`.

## What Must Be Proven

Runtime materialization means the production system actually creates the runtime
environment needed by the product capability. A provisioned resource, started
process, VM, pod, task, ASG, deployment, or final status is not enough by
itself.

For every supported mode, identify how these capability inputs are materialized:

| Capability input | Questions to answer |
|---|---|
| Runtime artifact | Which binary/image/package/AMI/container/agent/runtime version is executed? |
| Product config | Who renders product-level config, and where does the runtime read it from? |
| Plugins/extensions | How are plugins, extensions, drivers, or custom artifacts installed or mounted? |
| Secrets/security config | How are credentials, certificates, truststores, IAM, ACLs, or security properties delivered? |
| Dependency endpoints | How are bootstrap URLs, internal topics, service endpoints, ports, and cluster identity provided? |
| Local filesystem/volumes | Which paths, permissions, ownership, and persistence semantics are required? |
| Bootstrap/entrypoint | Which init container, systemd unit, userdata, startup script, sidecar, init job, agent, or controller performs setup? |
| Lifecycle operations | How do create, update, resize/scale, restart, delete, retry, and partial failure update runtime state? |
| Readback/observability | Which API/status/event/log/metric proves the runtime used the intended materialized inputs? |

Existing mode evidence is a baseline for product capability, not a mandate to
reuse the same implementation mechanism. A K8s init container, Docker volume,
Helm template, VM userdata, systemd unit, sidecar, or agent may all be valid
mechanisms if the resulting product capability is equivalent and verified.

## Required Artifact

When triggered, create or update
`specs/changes/<change-id>/runtime-materialization-parity.md`.

Minimum sections:

## Runtime Mode Change Classification

| Decision ID | Source | Existing mode(s) | New / changed mode | Classification | Evidence | Locked decision | Owner stage |
|---|---|---|---|---|---|---|---|

## Product Capability Parity Matrix

| Capability ID | Product capability | Existing mode baseline | New / changed mode obligation | Supported? | If not supported, product/API/UI expression | Contract ID | Verification ID | Owner issue |
|---|---|---|---|---|---|---|---|---|

## Runtime Materialization Mapping

| Mapping ID | Mode | Capability input | Existing mode materialization evidence | New / changed mode materialization design | Production owner | Required files/modules | Failure semantics | Verification | Owner issue |
|---|---|---|---|---|---|---|---|---|---|

## Runtime Parity Negative Assertions

| Assertion ID | Forbidden shortcut | Why invalid | Detection proof | Backflow target |
|---|---|---|---|---|
| RMP-NEG-001 | Resource created but product config/plugins/secrets are not materialized | Resource existence does not prove runtime capability | Runtime config/plugin/secret readback or startup failure assertion | design/contract/task-planning |

## Consumption Requirements

The parity artifact must be consumed by downstream stages:

- `decision-surface-discovery.md`: include a runtime materialization surface for every supported or scoped mode.
- `external-capability-research.md`: include external runtime or substrate facts when official/provider/runtime behavior matters.
- `contracts.yaml` / contract docs: include runtime materialization provider guarantees and consumer assumptions.
- `verification.yaml` / verification matrix: include proof for materialized config/plugins/secrets/bootstrap and negative shortcut assertions.
- `atomic-issue-packets.yaml`: copy the relevant mapping rows into owner task execution sections.
- `task-dag.yaml`: runtime materialization provider tasks must precede tasks that depend on the runtime being usable.

## Invalid Shortcuts

These are never enough to prove runtime materialization:

- resource exists / ASG exists / pod exists / process starts.
- desired/min/max capacity is set.
- endpoint or port is reachable but product config is not verified.
- DB state says running.
- final progress event says success with no runtime input readback.
- mock fixture or no-cloud status without production owner call proof.
- assuming the image/AMI/container already contains required plugins, config, or secrets without a locked source.

## Backflow Rule

If implementation or acceptance discovers a runtime materialization gap, classify
it as `runtime-materialization-parity-gap`, update Backflow Invalidation Matrix,
invalidate affected DEC/C/VER/T, and return to the earliest missing stage. Do
not patch only the final failing test or runtime fixture.
