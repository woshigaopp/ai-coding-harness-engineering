# Mock Acceptance

## Mock Acceptance Summary

| Item | Result | Evidence | Blocks acceptance |
|---|---|---|---:|
| Strict case validation |  |  | yes |
| Backend mock matrix execution |  | mock-acceptance-execution.yaml | yes |
| Frontend action matrix execution |  | mock-acceptance-execution.yaml | yes |
| Packaged/runtime representative cases |  | mock-acceptance-execution.yaml | yes |
| Repo-specific runtime audit, if applicable |  | acceptance/repo-specific-runtime-audit.md | yes |

## Acceptance Context Rehydration

| Artifact/source | Read status | Consumed facts | Missing/blocked reason |
|---|---|---|---|
| mock-backend-matrix.yaml |  |  |  |
| mock-frontend-action-matrix.yaml |  |  |  |
| mock-acceptance-cases.yaml |  |  |  |
| mock-acceptance-execution.yaml |  |  |  |
| repo-specific runtime reference, if applicable |  |  |  |
| task verification log |  |  |  |

## Dimension Coverage Matrix

| Coverage set | Required dimensions | Cases | Result | Blocks acceptance |
|---|---|---|---|---:|

## Backend Mock Matrix

| Backend row ID | API path | Contract source | No-cloud adapters | Fixture refs | Command/evidence | Result | Blocks acceptance |
|---|---|---|---|---|---|---:|
| MBM-xxx | POST /example/path | C-xxx / VER-xxx | repo no-cloud/mock adapter names | fixture-xxx | planned command in mock-backend-matrix.yaml | planned | yes |

## Frontend Action Matrix

| Frontend action ID | Route/component | User action | API client/path | Fixture refs | Command/evidence | Result | Blocks acceptance |
|---|---|---|---|---|---|---|---:|
| MFM-xxx | /example/route | Perform locked user action | apiClient.method | fixture-xxx | planned command in mock-frontend-action-matrix.yaml | planned | yes |

## Case Execution Matrix

| Case ID | Backend refs | Frontend refs | User goal | Browser evidence | Network evidence | DOM/API evidence | Result | Blocks acceptance |
|---|---|---|---|---|---|---|---|---:|
| MAC-xxx | MBM-xxx | MFM-xxx | Locked user workflow through packaged/runtime UI | planned trace | planned HAR | planned DOM/API assertions | planned | yes |

## Fixture Graph Matrix

| Fixture ID | Contract source | Provides | Consumed by case_id | Result | Blocks acceptance |
|---|---|---|---|---|---:|

## Frontend User-Flow Local Audit Report

| Flow/action | Has real entry/click/submit? | API/path/payload evidence | Success/failure evidence | Mode negative assertion | Required backflow | Blocks acceptance |
|---|---|---|---|---|---|---:|

## Backend Flow Local Audit Report

| Path/edge | Test/Not Run evidence | State/time assertion | Failure/terminal coverage | Required backflow | Blocks acceptance |
|---|---|---|---|---|---:|

## Contract Source Local Audit Report

| Contract/mock | Source trusted? | Mock boundary finding | Drift guard finding | Severity | Required backflow | Blocks acceptance |
|---|---|---|---|---|---|---:|

## Real Controller / No-Cloud Guard Report

| Request/path | Expected route classification | Static coverage | Runtime real/no-cloud evidence | Real external call observed? | Residual risk | Blocks acceptance |
|---|---|---|---|---:|---|---:|

## Runtime Freshness Local Audit Report

| Artifact/process | Observed branch/commit/time/PID/port | Fresh? | Smoke evidence | Finding | Blocks display acceptance |
|---|---|---:|---|---|---:|
| Packaged/runtime audit | acceptance/repo-specific-runtime-audit.md |  | static/runtime freshness, route console/network, representative browser/API evidence |  | yes |

## Packaged / Runtime Handoff QA

| Check | Evidence | Result | Blocks handoff |
|---|---|---|---:|
| Representative packaged/runtime entry smoke |  |  | yes |
| User workflow handoff route |  |  | yes |
| Static/browser runtime sanity |  |  | yes |

## Not Run And Cloud Boundary

| Item | Why not covered by mock | Accepted boundary | Owner | Blocks done |
|---|---|---|---|---:|
