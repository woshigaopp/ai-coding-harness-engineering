# Existing Object-Action-Consumer Graph

Use this during code archaeology when a requirement changes an existing object,
mutation/action, runtime implementation, deployment shape, or post-create
consumer surface. The graph is code-derived evidence, not a PRD keyword match.

## Existing Object-Action-Consumer Graph

| Graph ID | Object/entity | Action / mutation | Entry point API/page/controller | Existing variant/discriminator | Producer chain | State owner / storage | Readback API / VO | Consumer surface | Hidden old-variant assumption | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| OAC-001 | ConnectCluster | create | `POST /connect/clusters` | k8s | `InstanceChange -> task_table -> task events` | change/task tables | `/last-change`, `/changes/{changeId}` | progress page | K8s task steps and Pod wording | exact code paths |

## Existing Consumer Assumption Matrix

| Assumption ID | Object/action | Consumer surface | Consumer reads from | Required producer/state | Correlation key | Empty behavior | Failure behavior | Old-variant-only parts | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| ECA-001 | ConnectCluster/create | progress page | `/last-change`, `/changes/{changeId}` | change record and task/event steps | `clusterId -> changeId` | empty progress state | failed step with reason | Kubernetes labels | exact code paths |

## Local Audit

| Row | Auditor finding | Missing producer | Missing state owner | Missing readback consumer | Required backflow | Blocks next stage |
|---|---|---|---|---|---|---|
| OAC-xxx | none | none | none | none | none | no |
