# Example: Connect Cluster Infrastructure Selection

This example shows how two backend tasks are connected by a contract rather
than by a checklist dependency.

## Feature

When creating a Connect Cluster, users should be able to select:

- VPC;
- Subnet;
- Security Group;
- IAM Role.

Do not give the agent a vague task like:

> Support backend infrastructure selection.

Instead, decompose it into contract-connected Atomic Issues.

## T001: Infrastructure Resource Query

Primary module: Infrastructure Catalog.

Task:

Provide an API that returns selectable cloud resources based on account, region,
resource type, and optional parent resource.

This task retrieves and normalizes options. It does not create a Connect
Cluster.

### Provided Contract: C001 Infrastructure Catalog Option Contract

| Dimension | Semantics |
|---|---|
| Trigger | A resource option query API is called. |
| Input | `accountId`, `region`, `resourceType`, optional `parentResourceId`. |
| Normal Path | Return selectable options. Each option contains at least `id`, `displayName`, `status`, and `parentId`. |
| Failure Path | Permission failure, unsupported region, or provider unreachable returns explicit error or unavailable state. |
| Consistency | Options must belong to the current account and region. |
| Timing | No strong real-time guarantee, but one response must be internally consistent. |
| Verification | Mock provider covers success, empty list, permission failure, provider unreachable. |

## T002: Connect Cluster Creation Consumes Resource Selection

Primary module: Connect Cluster Creation.

Task:

Accept `vpcId`, `subnetIds`, `securityGroupIds`, and `iamRoleId` in the create
request. Validate them against the selectable resources provided by C001. If
valid, store them in the create task context.

This task does not reimplement resource query and does not redefine resource
option fields.

### Consumed Contract

C001 guarantees:

- candidate resources belong to the current account and region;
- each option has `id`, `displayName`, `status`, and `parentId`;
- provider failure has standardized semantics.

### Provided Contract: C002 Connect Cluster Create Infrastructure Selection Contract

| Dimension | Semantics |
|---|---|
| Trigger | User submits a Connect Cluster create request. |
| Normal Path | Submitted resource IDs are found in candidate options. Request enters accepted state. Resource selection is stored in task context. |
| Failure Path | Missing resource, region mismatch, parent mismatch, or unavailable status returns field-level error. |
| Consistency | Stored resource IDs must match user-submitted values. Backend must not silently replace them. |
| Timing | Validation occurs before async task submission. Validation failure creates no async task. |
| Verification | Cases cover valid resources, missing resource, Subnet not in VPC, Security Group region mismatch, unavailable IAM Role. |

## Why This Matters

T001 and T002 are not connected by the checklist instruction "do T001 before
T002."

They are connected by C001.

When the agent executes T002, it should not decide:

- what fields a resource option contains;
- how provider failure is represented;
- whether empty list equals unreachable provider;
- who validates parent relationship;
- whether invalid resources produce warnings or hard errors.

Those semantics are already in C001.

The agent executes T002 by consuming C001 and providing C002.

