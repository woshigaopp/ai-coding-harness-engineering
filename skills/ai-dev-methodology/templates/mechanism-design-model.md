# Mechanism Design Model

Use this in AIP/readiness and new-feature-design when a requirement depends on
non-trivial production mechanisms: cloud APIs, K8s/HPA, ASG, metrics, IAM,
runtime materialization, resource lifecycle, progress/change events, logs,
storage, external adapters, or cross-mode behavior.

This artifact is the design-stage source of truth for how the feature works.
It is not code, but it must be detailed enough that contract and task planning
do not invent provider APIs, runtime shape, event fields, resource ownership,
failure behavior, or verification strategy.

## Mechanism Row Inventory

| Mechanism row | Source | Operation / surface | Product semantic | Selected production mechanism | Rejected alternatives | Current code evidence | External fact / constraint | Canonical owner | Interface fields | State/resource mutation | Runtime materialization | Event/progress model | Failure/consistency/idempotency | Verification | Downstream C/VER | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MECH-001 | REQ-xxx / ADEC-xxx | create ASG autoscaled cluster | user requests CPU autoscaling at create time | create ASG plus explicit scaling policy or locked alternative | DB-only capacity, delayed policy creation | `path/File.java` or `rg ...` | FACT-xxx / CONSTRAINT-xxx | provider/resource writer module | API/DTO/VO fields and canonical path | DB/resource/event writes | RMP-MAP-xxx or locked N/A | EVT-xxx / PCP-xxx | permission/metric/provider failure and retry rule | VER-xxx | C-xxx / VER-xxx | locked |

Rules:

- `Mechanism row` uses `MECH-xxx` and is one operation/surface. Do not combine create/update/delete, or workers/logs/metrics/connectors, in one row.
- `Selected production mechanism` must name real production mechanisms: API/resource/call chain/state writer/runtime carrier. It cannot be only "support X".
- `Rejected alternatives` must include at least one real alternative and why it is rejected.
- `Current code evidence` must be a path or command proving current adjacent behavior or owner location.
- `External fact / constraint` is required for cloud/K8s/ASG/HPA/metrics/IAM/runtime/logs/storage/mock/no-cloud semantics.
- `Interface fields`, `State/resource mutation`, `Runtime materialization`, `Event/progress model`, and `Failure/consistency/idempotency` must be concrete or `locked N/A`.
- `Downstream C/VER` must name the contract and verification rows that will consume this mechanism.
- `Status=blocked/open/TBD` blocks contract, verification, and task planning.

## Operation Sequence Model

| Sequence row | Mechanism row | Operation | Trigger / entrypoint | Preconditions | Ordered production steps | External calls/resources | State writes | Events/progress emitted | Readback/consumer surfaces | Failure branches | Verification | Downstream C/VER |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OPSEQ-001 | MECH-001 | create ASG autoscaled cluster | `POST /...` | validated ASG config and metrics decision | 1. persist cluster intent; 2. create Launch Template; 3. create ASG; 4. create scaling policy; 5. emit progress | `CreateLaunchTemplate`, `CreateAutoScalingGroup`, `PutScalingPolicy` or locked alternative | cluster row, resource provenance, change/event row | EVT-xxx / PCP-xxx | detail/list/progress/frontend tab | permission denied, quota failure, partial resource created, metric unavailable | VER-xxx | C-xxx / VER-xxx |

Rules:

- Each sequence is a real production call chain. If a step is only a mock fixture, mark the row blocked unless the production step is defined elsewhere.
- Include step ordering when partial failure or readback depends on order.
- Failure branches must mention cleanup/protect/residual/retry behavior where resources or state are created.

## External API Parameter Map

| Parameter row | Mechanism row | External system/API/resource | Parameter / option | AutoMQ source field | Source/default/derived rule | Non-equivalent semantic | Permission/metric/failure behavior | Owner module | Verification |
|---|---|---|---|---|---|---|---|---|---|
| EXTAPI-001 | MECH-001 | AWS Auto Scaling `PutScalingPolicy` | target CPU percent / metric config | `capacity.autoscaling.targetCpuPercent` | required for autoscaled ASG; no default unless ADEC locks one | one target value cannot express separate scale-in/scale-out thresholds | metric missing maps to typed scale-blocked reason | provider module | VER-xxx |

Rules:

- A parameter row must explain what each external parameter means for this feature, not just that an API exists.
- If K8s and ASG use different mechanisms, write separate rows.
- If product semantics cannot be represented exactly, record the non-equivalence and the ADEC/PDEC that accepts it.

## Event State Model

| Event row | Mechanism row | Operation | Event / step | Producer | State owner | From state | To state | Terminal? | Fields | Consumer surfaces | Failure reason / status | Verification |
|---|---|---|---|---|---|---|---|---:|---|---|---|---|
| EVT-001 | MECH-001 | create ASG autoscaled cluster | `CREATE_ASG_SCALING_POLICY` | runtime/progress writer | change/task/event table | creating | scaling_policy_created | no | clusterId, changeId, operation, mode, resourceId, status, reason, terminal | last-change, change detail, frontend progress, mock event graph | `SCALING_POLICY_CREATE_FAILED` with provider reason | VER-xxx |

Rules:

- Every user-visible operation status, change, progress, terminal state, retry, or mock state graph must have event rows.
- Event rows define names, fields, terminal behavior, producer, consumers, and failure reasons before implementation.

## Runtime Materialization Model

| Runtime row | Mechanism row | Mode / runtime | Existing mode baseline | New mode materialization design | Artifact/config/plugin/secret/bootstrap carrier | Production owner | Readiness/readback | Failure behavior | Verification |
|---|---|---|---|---|---|---|---|---|---|
| RMM-001 | MECH-xxx | ASG Connect worker | K8s init container downloads plugins and renders worker config | ASG userdata/agent/bootstrap renders same product config and downloads plugin artifacts from locked source | artifact, worker config, plugin bundle, security config, bootstrap servers, endpoint/readiness | runtime materialization owner module | normalized readiness endpoint/readback | typed runtime-materialization failed reason | VER-xxx |

Rules:

- Resource/process existence is not runtime parity.
- If the existing mode uses init containers, generated configs, mounted secrets, metrics defaults, plugin downloads, or bootstrap scripts, each equivalent carrier must be mapped or explicitly locked N/A.
- This table may reference `runtime-materialization-parity.md`, but it must still summarize the selected design in mechanism terms.

## Resource Lifecycle Model

| Resource row | Mechanism row | Resource | Selection/provenance | Create timing | Update rule | Delete cleanup/protect rule | Identity/readback owner | Idempotency/retry | Partial failure residual state | Verification |
|---|---|---|---|---|---|---|---|---|---|---|
| RLM-001 | MECH-xxx | ASG / Launch Template / Security Group / IAM Role/Profile | owned/generated/select-existing | before runtime ready | replace/update according to operation | owned cleanup; existing protect/detach | provenance table/API readback | same cluster/change id does not duplicate owned resource | residual resource id + retryable typed reason | VER-xxx |

Rules:

- Selector/default UI does not close resource lifecycle.
- Owned/generated and existing resources must have different cleanup/protect rules.
- Partial failure must define residual state and retry/cleanup behavior.

## Failure Consistency Model

| Failure row | Mechanism row | Operation | Failure point | DB/state before external side effect | External side effect state | User-visible state/event | Retry/rollback/cleanup rule | Consistency invariant | Verification |
|---|---|---|---|---|---|---|---|---|---|
| FCM-001 | MECH-xxx | ASG update capacity | provider update fails after DB intent accepted | pending change exists with old effective capacity or locked pending state | ASG unchanged or partially changed | change failed with typed reason and retryable residual info | retry uses same desired intent; rollback/cleanup locked | readback never claims capacity succeeded unless provider proof exists | VER-xxx |

Rules:

- For any operation with DB mutation plus provider side effect, define failure ordering and consistency.
- If rollback is not implemented, the design must explicitly choose residual/retry semantics.

## Module Interface Model

| Interface row | Mechanism row | Producer module | Consumer module | Method/API/event/resource surface | Request fields | Response/readback fields | Error/warning fields | Timing/ordering | Verification |
|---|---|---|---|---|---|---|---|---|---|
| MIM-001 | MECH-xxx | frontend/API/service/provider/runtime | consumer module | method/path/event/resource | canonical request fields | canonical response/readback fields | typed errors/warnings | before/after side effect or polling rule | VER-xxx |

Rules:

- Interface rows prepare contract obligations. They must not hide field or timing decisions in prose.
- If one mechanism row touches multiple producer/consumer surfaces, split interface rows.

## Mechanism Design Local Audit

| Mechanism row | Auditor finding | Missing sequence | Missing external parameter map | Missing event/state model | Missing runtime/resource/failure model | Required backflow | Blocks next stage |
|---|---|---|---|---|---|---|---:|
| MECH-xxx | none | none | none | none | none | none | no |
