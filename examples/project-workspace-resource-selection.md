# Example: Project Workspace Resource Selection

This example shows how two backend tasks are connected by a contract rather
than by a checklist dependency.

## Feature

When creating a Project Workspace, users should be able to select:

- environment;
- resource group;
- access policy;
- runtime profile.

Do not give the agent a vague task like:

> Support backend resource selection.

Instead, decompose it into contract-connected Atomic Issues.

## T001: Resource Catalog Option Query

Primary module: Resource Catalog.

Task:

Provide an API that returns selectable resources based on organization,
environment, resource type, and optional parent resource.

This task retrieves and normalizes options. It does not create a Project
Workspace.

### Provided Contract: C001 Resource Catalog Option Contract

| Dimension | Semantics |
|---|---|
| Trigger | A resource option query API is called. |
| Input | `organizationId`, `environmentId`, `resourceType`, optional `parentResourceId`. |
| Normal Path | Return selectable options. Each option contains at least `id`, `displayName`, `status`, and `parentId`. |
| Failure Path | Permission failure, unsupported environment, or provider unreachable returns explicit error or unavailable state. |
| Consistency | Options must belong to the current organization and environment. |
| Timing | No strong real-time guarantee, but one response must be internally consistent. |
| Verification | Test doubles cover success, empty list, permission failure, and provider unreachable. |

## T002: Workspace Creation Consumes Resource Selection

Primary module: Workspace Provisioning.

Task:

Accept `environmentId`, `resourceGroupId`, `accessPolicyId`, and
`runtimeProfileId` in the create request. Validate them against the selectable
resources provided by C001. If valid, store them in the provisioning request and
the later async task context.

This task does not reimplement resource query and does not redefine resource
option fields.

### Consumed Contract

C001 guarantees:

- candidate resources belong to the current organization and environment;
- each option has `id`, `displayName`, `status`, and `parentId`;
- provider failure has standardized semantics.

### Provided Contract: C002 Workspace Create Resource Selection Contract

| Dimension | Semantics |
|---|---|
| Trigger | User submits a Project Workspace create request. |
| Normal Path | Submitted resource IDs are found in candidate options. Request enters accepted state. Resource selection is stored in task context. |
| Failure Path | Missing resource, environment mismatch, parent mismatch, or unavailable status returns field-level error. |
| Consistency | Stored resource IDs must match user-submitted values. Backend must not silently replace them. |
| Timing | Validation occurs before the async task is submitted. Validation failure creates no async task. |
| Verification | Cases cover valid resources, missing resource, resource group not in selected environment, access policy mismatch, unavailable runtime profile. |

## Why This Matters

T001 and T002 are not connected by the checklist instruction "do T001 before
T002."

They are connected by C001.

When the agent executes T002, it should not decide:

- what fields a resource option contains;
- how provider failure is represented;
- whether an empty list is the same as an unreachable provider;
- who validates parent relationships;
- whether invalid resources produce warnings or hard errors.

Those semantics are already in C001.

The agent executes T002 by consuming C001 and providing C002.
