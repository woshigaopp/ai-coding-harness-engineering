# External Side Effect Contract Matrix

Use this when a requirement depends on a real external side effect, including
cloud APIs, K8s operators/controllers, Terraform/Helm/IAM/network/storage,
runtime schedulers, provider SDKs, third-party APIs, or no-cloud/playground
acceptance substitutes.

## External Side Effect Contract Matrix

| Effect ID | Source | Operation/action | External system | Production side-effect owner | Required production call/resource mutation | Physical dependency allowed? | No-cloud/playground substitute boundary | Minimum acceptable proof | Failure/partial failure semantics | State/readback consumer | Contract ID | Verification ID | Owner issue |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ESE-001 | REQ-xxx/C-xxx | ConnectCluster capacity update | AWS ASG / K8s HPA | Connect runtime manager/provider adapter | `operator.setCapacity(...)` and locked policy/scheduler side effect | no real cloud in playground | mock only replaces physical cloud endpoint, not manager/provider call | provider call capture + terminal event + readback for same cluster id | typed failed state/event/readback on provider error | detail/progress/event/API consumer | C-xxx | VER-xxx | Txxx |

## Side Effect Alternative Decision Matrix

| Decision ID | Effect ID | Candidate implementation | Selected? | Rejected alternatives | Why selected satisfies contract | Product/ops impact | Verification impact |
|---|---|---|---:|---|---|---|---|
| ESE-DEC-001 | ESE-001 | provider API call + terminal event | yes | DB-only state, fixture-only event, log-only hook | production path crosses provider boundary and readback proves outcome | no-cloud acceptance stays representative | integration/mock-composition proof |

## Side Effect Local Audit

| Effect ID | Auditor finding | Missing production owner | Missing physical/substitute boundary | Missing failure/readback semantics | Required backflow | Blocks next stage |
|---|---|---|---|---|---|---:|
| ESE-xxx | none | none | none | none | none | no |
