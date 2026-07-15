---
name: mock-acceptance-gate
description: 严格契约驱动 mock acceptance 最终门禁。Use after implementation for AutoMQ features that must be accepted without physical cloud/runtime deployment while still proving production adapter calls and real product paths, especially automqbox/CMP Connect playground acceptance, frontend+backend user workflows, no-cloud external adapters for cloud API/K8s API/kafka instance API/Connect REST API, fixture graph consistency, real-controller routing, packaged playground restart/freshness, or when the user asks to verify all logic through mocks before deployment.
---

# Mock Acceptance Gate

## Position

This is the final automated acceptance gate after implementation. It is not a playground demo step.

Generic mock acceptance applies to every repo that needs no-cloud or simulated
external dependency acceptance. It requires concrete backend/frontend/fixture
matrix rows and row-level execution evidence.

`playground` is not a generic workflow concept. It means only the automqbox/CMP
packaged playground for Connect-related features. For automqbox/CMP Connect work,
playground, fixture, and simulator code are first-class deliverables and packaged
playground is a pre-release acceptance environment, not a best-effort demo. For
automqbox/CMP non-Connect work, the agent must not read or reason from
`cmp-playground`; use generic mock acceptance only. Other repos may define their
own repo-specific acceptance runtime, but they must not generate or consume
automqbox/CMP `playground-*`, `cmp-playground`, or packaged-playground artifacts
unless they explicitly define an equivalent runtime and artifact set.

The goal is to prove, without physical cloud/runtime deployment, that production
code still performs the required production adapter calls and state mutations:

- Real frontend pages/actions/routes/API clients exercise real backend HTTP/controller/DTO/service paths.
- For automqbox/CMP Connect playground, product code stays real: frontend, API client, HTTP route, controller, DTO/VO, service, manager, task, repository, and domain semantics must execute normally.
- Only physical external interfaces may be simulated: cloud API, K8s API, kafka instance API, and Kafka Connect REST API. Metrics and logs must be exposed through those real external interfaces, not by mocking product metrics/log services.
- Mock behavior is sourced from official/real/locked contracts, not from implementation guesses.
- Mock output, and automqbox/CMP Connect playground output when applicable, is isomorphic to the real external contract for paths, bodies, response shapes, enums, errors, state machines, progress, and terminal semantics.
- Any acceptance failure is classified and backflowed to the earliest missing requirement, frontend contract, cross-module contract, verification, implementation, or runtime-data stage.

No-cloud acceptance cannot downgrade production implementation obligation. It
only swaps the final physical external system behind the same production adapter
call. A valid ASG create flow, for example, must be:

```text
ConnectClusterController
  -> ConnectClusterService/Manager/Task
  -> InfraProvider.createService(..., NodeGroupOperator.class)
  -> NodeGroupOperator.create / setCapacity / delete / update
  -> production: real cloud provider
  -> acceptance: no-cloud adapter/simulator receives the same call
```

Forbidden anti-pattern:

```text
if ASG:
  validate local resolved config
  emit progress events
  return success
```

DB rows, progress events, route load, static freshness, local simulator state,
or controller allowlist evidence cannot close a runtime/cloud/K8s mutation row
unless the same row proves the production external adapter mutation call or has
a locked Non-Goal decision.

If a flow contains progress, change events, lifecycle status, terminal states, polling, retry, or mock state graph, mock acceptance must carry the same stateful behavior matrix as backend/frontend contracts. A mock that only has happy-path fixture data is not acceptable even when packaged browser smoke passes.

## When Required

Run this gate when the feature involves any of:

- Frontend/backend user flows: list, create/check, review/submit, progress/change, detail, update, delete, workers, metrics, logs.
- New or changed deployment, runtime, cloud, provider, K8s, worker, autoscaling, or mode semantics.
- Acceptance without physical cloud/runtime deployment while production code still calls production external adapters.
- Mock environments, no-cloud adapters, or repo-specific acceptance runtimes used for acceptance or demos.
- External dependencies such as cloud APIs, K8s APIs, kafka instance/control-plane APIs, Kafka Connect worker REST APIs, metrics endpoints, pod logs, or provider APIs.

## Required Inputs

Do not start mock acceptance until these exist or are explicitly marked N/A with a reason:

- `Mock Acceptance Plan` created before or during task planning.
- Acceptance context pack, when using contextpack workflow.
- Sealed `tasks.md` task index plus `task-verification-log.yaml`, `execution-state.yaml`, `workflow-state.yaml.task_receipts`, and applicable `mock-acceptance-execution.yaml`.
- Atomic Issue Done Criteria, Provided Contract Obligation, and Verification evidence.
- `git diff --stat` and actual changed-file list.
- Verification Matrix rows that require mock acceptance.
- Frontend contract, cross-module contract, mock boundary, runtime lifecycle, and mode semantic checks.
- Package/runtime freshness evidence when a packaged/browser acceptance URL will be handed off; for automqbox/CMP Connect features this means playground freshness evidence.

Block entry if task done status conflicts with verification, diff scope does not match the issue, mock/real boundary is unlocked, or P0/P1 Not Run risks remain open.

For automqbox/CMP Connect features, there is one additional hard input when mock
acceptance actually starts, or when the current owner task explicitly modifies the
playground foundation: re-read the current runtime implementation and
`references/cmp-playground.md`. Do not read these runtime implementation
details during PRD/design/contract/task-planning for ordinary product work.
Those earlier stages only plan production adapter obligations and acceptance
dimensions. At this gate the agent must verify the current code facts for:

- `cmp-app -Pplayground` packaging includes `cmp-playground`, and runtime starts with `--spring.profiles.active=playground`.
- affected controller route classification: every affected product controller must be `REAL_CONTROLLER_PATH` through `PlaygroundAcceptanceProperties.realControllerClasses`.
- no product business class, controller, service, manager, task, DTO/VO, API client, route, or frontend page is replaced or classpath-shadowed.
- strict mode flags: `PACKAGED_RUNTIME_PLAYGROUND_STRICT_MOCK_MODE=true` and `PACKAGED_RUNTIME_PLAYGROUND_CONTROLLER_MOCK_ENABLED=true`.
- no-cloud external adapters for cloud API, K8s API, kafka instance API, and Kafka Connect REST API.
- seeded SQLite/no-cloud graph ownership in `PlaygroundDatabaseSeeder` and `NoCloudRuntimeSimulator`.
- metrics via Connect `/metrics` and logs via K8s pod logs; do not treat metrics/log product services as mockable product logic.
- frontend build copied into `cmp-app/src/main/resources/static` and packaged by
  `cmp-app -Pplayground`.
- packaged playground pitfalls: stale `main-*.js`, stale JAR/static residue,
  old screen/process freshness, app/ops port ownership, Ace dynamic resources,
  browser console/runtime errors, and real-controller allowlist drift.
- packaged startup contract from `references/cmp-playground.md`: build frontend,
  package `cmp-app -Pplayground`, start the real `cmp-app` JAR with
  `--spring.profiles.active=playground`, strict env, isolated app/ops/K8s
  API/Connect REST/metrics ports, isolated `user.home`, and runtime audit.

If these facts cannot be verified from current code, mock acceptance is blocked
until the playground architecture reference and scripts are updated.

For final automqbox/CMP Connect mock acceptance, run both audits before declaring a
acceptance URL usable:

```bash
python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/cmp_playground_contract_audit.py \
  --repo /path/to/automqbox \
  --controllers <AffectedController1>,<AffectedController2> \
  --out specs/changes/<change-id>/acceptance/cmp-playground-contract-audit.md

python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/cmp_packaged_playground_runtime_audit.py \
  --repo /path/to/automqbox \
  --base-url http://127.0.0.1:<app-port> \
  --out specs/changes/<change-id>/acceptance/cmp-playground-audit.json
```

The static audit catches affected controllers that are not on the real-controller
allowlist before packaging. The runtime audit catches stale
bundle/JAR, wrong static MIME, old process, Ace dynamic-resource failures,
top-level route runtime exceptions, and browser network/console blockers after
the packaged process starts.

## Strict Case System

Mock acceptance is a generated test system, not a prose checklist. The agent must first turn product/backend/frontend/runtime semantics into finite dimensions, then compile concrete cases, then execute every blocking case and record row-level evidence.

There are two validation modes:

- Planning mode runs before implementation, during task planning / pre-execution. It requires the concrete case system to exist and be executable, but rows may still have `result: planned` or `result: not_run`.
- Execution mode runs after implementation, during per-task mock owner pass-task, mock acceptance, or product acceptance. The sealed matrix/case files are still validated as planning artifacts; execution results must be written to the mutable `mock-acceptance-execution.yaml` ledger. Every blocking backend/frontend/event/package row must have a terminal ledger entry with row-level evidence.

Planning mode is mandatory whenever the change mentions mock acceptance, no-cloud acceptance, external dependencies, cloud/K8s/kafka instance/Connect REST APIs, metrics/logs through external interfaces, browser acceptance, or any repo-specific acceptance runtime. For automqbox/CMP Connect features, `playground` is the repo-specific acceptance runtime backed by `cmp-playground`; for automqbox/CMP non-Connect features it is out of scope. This prevents the common failure where the agent writes “mock matrix should cover X” in prose, then implements a page-load smoke and marks the task done without concrete case rows.

Generic required artifacts:

```text
specs/changes/<change-id>/mock-backend-matrix.yaml
specs/changes/<change-id>/mock-frontend-action-matrix.yaml
specs/changes/<change-id>/mock-test-dimensions.yaml
specs/changes/<change-id>/mock-event-state-matrix.yaml   # required when lifecycle/progress/event/status/terminal signals exist
specs/changes/<change-id>/mock-acceptance-cases.yaml
specs/changes/<change-id>/mock-fixture-graph.yaml
specs/changes/<change-id>/mock-acceptance-execution.yaml                # execution only; mutable after begin-execution
specs/changes/<change-id>/mock-acceptance.md
```

Additional automqbox/CMP Connect playground-only artifacts for mock-acceptance
execution or for a task that explicitly changes the playground foundation:

```text
specs/changes/<change-id>/playground-external-dependency-contract.yaml
specs/changes/<change-id>/playground-domain-fixture-graph.yaml
specs/changes/<change-id>/playground-scenario-graph.yaml
```

These three files are not generic mock acceptance artifacts. They are required
only after mock acceptance actually starts for automqbox/CMP Connect features, or
when the current task explicitly changes the playground foundation. Task-planning /
pre-execution for ordinary product work should produce planned backend,
frontend, fixture, and packaged-case rows plus packaged playground coverage row ids, not read
current runtime implementation details or generate playground-specific
architecture facts. They are never required for automqbox/CMP non-Connect work or
other repositories.

Run this gate before `workflowctl.py pass-stage mock-acceptance`:

```bash
python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/validate_mock_acceptance_cases.py \
  specs/changes/<change-id>
```

Run planning mode before `workflowctl.py pass-stage task-planning` and before `workflowctl.py validate pre-execution` when mock acceptance or a repo-specific acceptance runtime is in scope:

```bash
python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/validate_mock_acceptance_cases.py \
  specs/changes/<change-id> --mode planning
```

`workflowctl.py validate mock-acceptance` and `validate_artifacts.py --stage mock-acceptance` also call this validator. Missing case artifacts, unexecuted blocking cases, only-smoke evidence, or row-level evidence gaps must fail the stage.

`mock-test-dimensions.yaml` must define finite dimensions and coverage sets. Each coverage set must declare its target layer:

- `backend_matrix`: fast real controller/service/manager/task combinations that consume mock/no-cloud external adapters.
- `frontend_action_matrix`: fast real-page/action/API-client/DOM/payload combinations.
- `packaged_cases`: representative packaged/browser cases that prove integration and freshness after the fast matrices pass; for automqbox/CMP Connect features these are packaged playground cases.

Use full cross product for tightly coupled dimensions in backend/frontend matrices. Use pairwise or representative coverage only when the dimension file records the N/A/exclusion decision. Do not put every combination into packaged/browser acceptance by default; the packaged playground is the final integration sample, not the exhaustive matrix runner. Typical dimensions:

- user flow/action: list, create, check, review, submit, progress, detail, update, resize, delete, workers, metrics, logs.
- mode/capacity/spec: deployment mode, capacity mode, worker spec type, autoscaling policy.
- selector/resource state: default, auto-create, existing, derived, empty, permission error, wrong parent, invalid, reset.
- managed external resource ownership: auto-create/default-created/generated/select-existing, provider writer call, resource identity/provenance persistence, runtime readback consumer, owned cleanup, existing protect/detach, partial cleanup failure.
- runtime/state: creating, running, failed, deleting, terminal, unavailable, query error, empty data.
- negative assertions: no old-mode fields in DOM, no hidden inactive payload fields, no wrong route, no real external call outside no-cloud adapters.
- mutation state owner: DB table/repository, cloud/K8s resource, runtime graph,
  task/change/event store, cache/topic, or other authoritative state that must
  change when create/update/delete/resize/save/scale succeeds.
- schema/resource compatibility: old required fields or resources that may become
  nullable, derived, defaulted, forbidden, retired, or compatibility-only for a
  new mode/variant.

`mock-backend-matrix.yaml` must contain one row per backend/mock-external combination that can be tested without starting the packaged browser runtime. Each row must include coverage sets, dimensions, HTTP method/path, request shape, real controller/service/manager/task, mock/no-cloud external adapters, mocked external dependency categories, fixture refs, state assertions, command, expected result, proves, and result.

For any persistent mutation row (`create`, `submit`, `update`, `resize`,
`delete`, `scale`, `save`, `bind`, `import`, worker spec or capacity changes),
backend matrix proof must not stop at request shape, DTO validation, service
unit tests, or simulator fixture construction. The row must name the
authoritative state owner and prove write plus readback:

```yaml
state_owner:
  persistence: connect_cluster SQLite row via ConnectClusterDAO/MyBatis
  runtime: no-cloud ASG/runtime graph when external resources are created
persistence_assertions:
  - DAO insert/update/delete succeeds for the mode-specific payload
  - schema/nullability/compatibility constraints match the new mode
  - old-mode required fields/resources that are legitimately absent in this mode
    do not block the real writer
readback_assertions:
  - detail/list/query reads the same created id and mode-specific fields
  - progress/change/event state is tied to the same created id when applicable
```

The state owner wording is generic: it may be a DB table, K8s resource, cloud
resource, task/change/event store, topic, cache, or runtime simulator graph.
If the user-visible state is persisted through SQLite/MyBatis/repository, the
row must cover the real repository/mapper/schema
write and detail/list readback. A constructed entity object or no-cloud fixture
object is supporting evidence only; it does not prove the mutation row.
Likewise, packaged route audit, controller allowlist audit, static freshness
audit, page-load smoke, or HTTP 200 without state verification cannot close a
mutation row unless the row also executes the mutation and proves authoritative
write plus readback.

For any auto-create/default-created/generated/select-existing external resource
row, backend matrix proof must additionally name and prove managed resource
ownership:

```yaml
managed_resource_ownership:
  resource_type: cloud/K8s/provider resource type
  selection_mode: auto-create | default-created | generated | select-existing
  provider_writer: production provider/API/operator/resource writer under test
  resource_identity_assertions:
    - generated id/name/tag is persisted or readable by the authoritative state owner
  provenance_assertions:
    - owned resources are marked/read back as owned or generated
    - selected existing resources are marked/read back as existing and are not created
  cleanup_assertions:
    - delete/update cleans owned resources
    - delete/update protects or detaches existing resources
    - partial cleanup failure produces typed residual state
```

Selector option tests, resolved config tests, route smoke, or no-cloud fixture
construction are supporting evidence only. They cannot close managed resource
ownership unless the row proves provider mutation, ownership readback, and
cleanup/protect behavior.

`mock-frontend-action-matrix.yaml` must contain one row per frontend action combination that can be tested with a fast frontend harness or equivalent DOM/network test. Each row must include coverage sets, dimensions, route, component, user action, API client, fixture refs, browser/user steps, network assertions, DOM assertions, negative assertions, command, expected result, proves, and result.

`mock-event-state-matrix.yaml` is required whenever any case, fixture, contract, or report mentions lifecycle/progress/event/status/terminal/polling/retry/state graph. It must contain one row per operation/mode/status/terminal/failure transition consumed by mock backend rows, frontend action rows, or packaged cases. Each row must include row id, source contract, operation, mode/variant, from state, trigger, event/step, status, to state, terminal, failure reason, producer, consumer, fixture refs, frontend assertion, backend assertion, command, expected result, proves, and result.

Every backend, frontend, event-state, and packaged row must also declare its execution owner when generated during atomic planning:

```yaml
owner_task: T007        # or owner_issue; backend matrix owner
```

Owner meaning is strict:

- backend matrix rows belong to the `mock-backend` owner task.
- frontend action rows belong to the `mock-frontend` owner task.
- packaged representative cases belong to the `packaged-acceptance` owner task; automqbox/CMP Connect work may name this owner `packaged-playground`.
- event-state rows should name the first matrix/case owner that must execute that transition, or be referenced by the concrete owner rows.

`workflowctl.py pass-task` validates mock acceptance by owner/layer. It must not force a backend API/domain/adapter task to execute frontend action rows or packaged/browser cases just because the task text mentions no-cloud, fixture, runtime, provider, frontend consumer, or automqbox/CMP playground. Conversely, a mock owner task cannot pass with summary evidence; it must add terminal entries for its owned rows to `mock-acceptance-execution.yaml` with row-level evidence.

Do not rewrite truthful task text just to avoid mock validator keywords. If a task is misclassified, fix `task-dag.yaml` layer / `mock_acceptance_target` / `owner_task` metadata or the workflow tool, then reseal. Keyword avoidance is treated as a workflow bug, not a valid implementation strategy.

The fast matrices are not optional prechecks. They are the exhaustive proof surface for combinations. `mock-acceptance-cases.yaml` must reference them through `backend_matrix_refs` and `frontend_action_refs`, and should only keep representative packaged cases that prove real integration, process freshness, routing, static assets, no-cloud adapter wiring, and top-level automqbox/CMP health.

After implementation, the matrix/case YAML files stay sealed planning artifacts. Do not change `mock-backend-matrix.yaml`, `mock-frontend-action-matrix.yaml`, `mock-event-state-matrix.yaml`, or `mock-acceptance-cases.yaml` just to mark rows passed; that creates stale receipt hashes and reseal loops. `mock-acceptance-execution.yaml` is execution-mutable before mock acceptance passes, then the mock-acceptance stage receipt seals its final hash. `task-verification-log.yaml` may summarize results, but it does not replace row-level matrix evidence. Every blocking row in backend, frontend, event-state, and packaged cases must have a matching terminal row in `mock-acceptance-execution.yaml`:

```yaml
owner_task: T007
target: backend                 # backend / frontend / packaged / event-state
row_id: MB-006                  # or frontend_action_id / case_id / event_state_row_id
result: passed              # or failed / blocked / not_applicable
command: <backend mock acceptance command from the sealed matrix row>
command_exit_code: 0
executed_by: <test or script id>
assertion_refs:
  - sealed row assertion 1 passed
  - sealed row assertion 2 passed
evidence: "MB-006 proves the sealed backend matrix behavior with row-level assertions."
evidence_refs:
  - acceptance/backend/MB-006.log
completed_at: "2026-05-31T18:09:20+08:00"
```

Rules:

- A single aggregate command may cover many rows, but every row must name its own `executed_by` test/method or manual runner and `assertion_refs`.
- `passed` without `command`, `command_exit_code: 0` or manual verdict, `executed_by`, `assertion_refs`, `evidence_refs`, and `completed_at` is not accepted.
- `evidence` is explanatory text only. It cannot replace `evidence_refs`; row evidence must point to real logs, reports, HAR, traces, screenshots, or other durable artifacts. Summary files such as `task-verification-log.yaml`, `execution-state.yaml`, `workflow-state.yaml`, `tasks.md`, or `mock-acceptance.md` do not count as row evidence.
- For persistent mutation rows, execution evidence must mention and point to
  artifacts proving both state write and readback. Payload helper tests, route
  audit, controller allowlist audit, runtime freshness audit, page-load smoke,
  HTTP 200 without state verification, or simulator fixture construction are
  supporting evidence only. They cannot close a mutation row by themselves.
- For managed resource ownership rows, execution evidence must mention and point
  to artifacts proving provider create/delete/update calls, owned/existing
  provenance readback, and cleanup/protect assertions. A selector test or
  resolvedConfig assertion is not enough.
- `blocked` or `failed` execution rows must keep their blocker in the ledger, classify the owner/backflow, and cannot pass mock acceptance unless the sealed matrix row has `blocks_acceptance: false` or the execution row is `not_applicable` with a locked decision.
- `planned` rows are allowed only in sealed planning matrices. Execution mode fails when a blocking sealed row has no terminal `mock-acceptance-execution.yaml` entry.
- `workflowctl.py pass-task` for a mock acceptance owner task runs execution-mode validation for that owner layer; T007/backend-matrix cannot pass with only a summary sentence like “ConnectClusterMockTest covers MB-001 through MB-008”, T008/frontend-action cannot pass without row-level DOM/network evidence, and T009/packaged cannot pass without packaged/browser evidence. For automqbox/CMP Connect features, packaged evidence means packaged playground/browser evidence.
- For automqbox/CMP packaged rows, evidence must include the real-controller routing audit
  and packaged playground runtime audit output, or an equivalent row-level artifact that
  proves the same real-controller/no-cloud routing, freshness, static
  resource, browser console/network, and top-level route checks.

Do not collapse the three layers into one Atomic Issue unless a locked N/A decision proves the layer is genuinely absent:

| Layer | Must exist before implementation | Must pass after implementation |
|---|---|---|
| Backend Mock Matrix | concrete sealed `mock-backend-matrix.yaml` rows with planned commands, real controller/service/manager/task, no-cloud adapters, and fixture refs | all blocking backend rows have terminal `mock-acceptance-execution.yaml` command/log evidence |
| Frontend Action Matrix | concrete sealed `mock-frontend-action-matrix.yaml` rows with browser/user steps, network assertions, DOM assertions and negative assertions | all blocking frontend rows have terminal `mock-acceptance-execution.yaml` DOM/network/trace evidence |
| Packaged / Repo-Specific Representative Cases | concrete sealed `mock-acceptance-cases.yaml` rows referencing backend/frontend matrix refs | representative packaged browser cases have terminal `mock-acceptance-execution.yaml` freshness, HAR/trace/screenshot/log evidence |

HTTP API smoke can support a backend matrix row, but it cannot close a frontend action row or packaged browser case. A packaged/browser API script that never clicks/selects/types/submits in the real browser is not mock acceptance completion.

`mock-acceptance-cases.yaml` must contain one row per required case. Every blocking case must include:

```yaml
case_id: MAC-ASG-CREATE-UNKNOWN-REACHABILITY
coverage_sets: [asg-create-reachability]
dimensions:
  action: create-submit
  deploymentMode: asg
  capacityMode: provisioned
  selectorState: existing
  reachability: unknown
user_goal: ASG create continues with a visible warning
frontend_route: /connect/clusters/create
real_code_under_test:
  frontend: frontend/cmp-app/src/pages/connect/clusters/create
  api_client: frontend/cmp-app/src/service/interface/connect.ts
  controller: cmp/cmp-cmp-app/src/main/java/.../ConnectClusterController.java
  service: cmp/cmp-service/src/main/java/.../ConnectClusterServiceImpl.java
mocked_external_dependencies: [cloud-api, k8s-api, kafka-instance-api, connect-rest-api]
forbidden_mocks: [frontend component, API client, controller, DTO, service]
fixture_refs: [fixture-asg-instance-main, fixture-provider-reachability-unknown]
command: pnpm --dir frontend/app test -- connect-asg-create.spec.ts
browser_steps:
  - open /connect/clusters/create
  - select deploymentMode=asg
  - expand VPC selector and choose vpc-main
  - click Submit
network_assertions:
  - POST /connect/clusters/check body has deploymentMode=asg and no kubernetes fields
  - POST /connect/clusters succeeds with warning
dom_assertions:
  - warning text is visible before final completion
  - Kubernetes namespace/serviceAccount fields are absent
api_assertions:
  - detail returns deploymentMode=asg and workerSpec.asg.instanceType
negative_assertions:
  - no raw AWS ID text box is used in the ordinary path
  - no K8s field is submitted
evidence_refs:
  - acceptance/browser/MAC-ASG-CREATE-UNKNOWN-REACHABILITY.trace.zip
  - acceptance/network/MAC-ASG-CREATE-UNKNOWN-REACHABILITY.har
result: passed
command_exit_code: 0
executed_by: test:connect-asg-create.spec.ts/MAC-ASG-CREATE-UNKNOWN-REACHABILITY
assertion_refs:
  - network POST /connect/clusters/check excludes Kubernetes fields
  - DOM warning is visible and namespace/serviceAccount are absent
completed_at: "2026-05-31T18:09:20+08:00"
blocks_acceptance: true
```

`mock-fixture-graph.yaml` must be the data source for selectors and downstream pages. Each fixture row must declare `fixture_id`, `type`, `contract_source`, `provides`, and `consumed_by`. Empty selectors, dangling references, stale enum values, missing progress/detail state, or data that cannot drive the frontend are blockers.

If `frontend-fixture-need-matrix.md` exists, every frontend fixture need row must map to a `mock-fixture-graph.yaml` fixture id and be referenced by at least one `mock-acceptance-cases.yaml` case through `fixture_refs`. A frontend fixture need that never becomes fixture data and a case is untested UI behavior, not accepted coverage.

For automqbox/CMP mock-acceptance execution, `mock-fixture-graph.yaml` is not
enough by itself. It must be backed by the stricter playground simulation
contract:

- `playground-external-dependency-contract.yaml` defines exactly what external
  cloud API, K8s API, kafka instance API, and Kafka Connect REST API behavior is
  simulated, which no-cloud adapter implements it, which real
  frontend/API/controller/service consumes it, and which product layers are
  forbidden to mock.
- `playground-domain-fixture-graph.yaml` defines the whole no-cloud business
  graph. For Connect features this means instance, provider resources,
  ConnectCluster, workers, connector, connector tasks, progress/change, events,
  metrics, and logs are connected by ids and consumed by real pages/APIs.
- `playground-scenario-graph.yaml` defines ordered user scenarios. A create
  scenario must continue to detail, progress/change, events, connector
  downstream flows, tasks/workers, metrics/logs, update/resize, and delete
  unless a locked N/A decision removes a branch.

If the current runtime module cannot express a required edge or state, the
correct output is a runtime implementation task and backflow entry. It is
not acceptable to narrow acceptance to the subset the current mock happens to
support.

`mock-acceptance.md` must be generated or updated from the executed cases. It must include:

- `Mock Acceptance Summary`
- `Acceptance Context Rehydration`
- `Dimension Coverage Matrix`
- `Backend Mock Matrix`
- `Frontend Action Matrix`
- `Case Execution Matrix`
- `Fixture Graph Matrix`
- `CMP Playground Architecture Matrix` only for automqbox/CMP Connect features
- `Playground Simulation Contract` only for automqbox/CMP Connect features
- `CMP Playground Coverage Matrix` only for automqbox/CMP Connect features
- `Frontend User-Flow Local Audit Report`
- `Backend Flow Local Audit Report`
- `Contract Source Local Audit Report`
- `Real Controller / No-Cloud Guard Report`
- `Runtime Freshness Local Audit Report`
- `Packaged / Runtime Handoff QA`
- `Not Run And Cloud Boundary`

Never close a case with `build`, `typecheck`, payload helper tests, HTTP 200,
API smoke, route smoke, runtime audit, controller audit, or page-load smoke
alone. These are supporting evidence only. Mutation flows require real browser
action evidence and state proof:

```text
click/select/type/submit
  -> network method/path/body
  -> response/error
  -> authoritative state write
  -> detail/list/progress/event readback of the same id
  -> DOM feedback/navigation/next state
```

If packaged browser execution cannot prove the state write/readback, record the
case as `failed` or `blocked` and backflow to the earliest missing owner:
requirements/contract when the state owner was never defined, backend
persistence/runtime task when the write fails, frontend action task when the
browser cannot submit the intended payload, or runtime implementation when
the no-cloud external adapter/fixture graph cannot represent the state.

## Pre-Implementation Mock Plan

For any feature that will rely on mock acceptance or a repo-specific acceptance runtime, create the mock plan before implementation tasks are marked executable:

```markdown
### Mock Acceptance Plan

| User goal | Real code that must be tested | External dependency to mock | Contract source | Fixture/state needed | Frontend evidence | Backend evidence | Browser/runtime evidence | Blocks if missing |
|---|---|---|---|---|---|---|---|---:|
```

Rules:

- `Real code that must be tested` names frontend page/action/API client and backend controller/DTO/service; these cannot be mocked.
- `External dependency to mock` is limited to cloud API, K8s API, kafka instance API, and Kafka Connect REST API for automqbox/CMP Connect features. Metrics/logs are tested through Connect REST `/metrics` and K8s pod-log APIs, not by mocking product metrics/log services.
- `Contract source` must exist before mock data is accepted. Missing source is a decision gap, not an implementation detail.
- `Fixture/state needed` must include reference graph edges, progress/change/event state, terminal states, and failure states.
- Each row must map to a Verification Matrix item and an owner task/Atomic Issue.
- If the plan cannot identify browser/runtime evidence for a user goal, the feature cannot be declared product-accepted through mock acceptance.
- Convert every row into one or more `mock-test-dimensions.yaml` coverage sets, then into `mock-backend-matrix.yaml`, `mock-frontend-action-matrix.yaml`, and representative `mock-acceptance-cases.yaml` cases. A plan row that never becomes a fast matrix row or packaged case is a blocker.

For automqbox/CMP Connect features, the mock-acceptance execution plan must additionally include:

- affected controller list for static audit.
- route classification for each affected controller/method: `REAL_CONTROLLER_PATH`; if an affected controller is not allowlisted, add it to `PlaygroundAcceptanceProperties.realControllerClasses` or block acceptance.
- no-cloud graph owner for every lifecycle/progress/detail result.
- external adapter fixture ids for every selector and downstream page state.
- `playground-external-dependency-contract.yaml` rows for every simulated cloud
  API, K8s API, kafka instance API, and Kafka Connect REST API dependency.
- `playground-domain-fixture-graph.yaml` rows for the full business graph:
  instance -> ConnectCluster -> worker -> connector -> task -> progress/change
  -> event -> metrics/logs. If a branch is truly absent, lock N/A with a reason.
- `playground-scenario-graph.yaml` ordered user scenarios that prove downstream
  pages after creation, not only the create page itself.
- backend matrix owner for real controller/service/manager/task plus no-cloud adapter combinations.
- backend mutation owner for real state owner write/readback through repository,
  resource writer, runtime graph, task/change/event store, or equivalent
  authoritative state.
- frontend action matrix owner for route/component/API-client/DOM/payload combinations.
- packaged/browser runtime build/package/restart evidence owner; for
  automqbox/CMP Connect features this is the packaged playground owner.
- top-level application smoke areas that can be broken by the diff; for
  automqbox/CMP this belongs to playground only when the feature is Connect-related.

If current `cmp-playground` cannot represent the required selector state,
external REST/K8s state, event/progress edge, connector downstream edge, or metrics/logs
branch, create or update runtime module code as part of the implementation
plan. Do not replace this with temporary endpoints, static frontend data, or a
manual waiver. Playground is allowed to change; product logic is not allowed to
be mocked.

## Core Layers

| Layer | Must Prove | Insufficient Evidence |
|---|---|---|
| External contract evidence | Cloud API/K8s API/kafka instance API/Connect REST fields, enums, errors, states, timing, and terminal semantics have a trusted source | Invented mock data |
| Backend composition | User scenario paths go through real controller/DTO/service and cover success, failure, boundary, and state progression | Isolated service/unit tests |
| Frontend user flow | Real page/DOM/browser or equivalent test covers inputs, mode switches, next/review/submit, API call, error display, and navigation | Payload helper or type check only |
| Drift guards | Real implementation, mock implementation, and frontend consumption agree on path/body/response/enum/state/error/progress | Manual page glance |
| Mock delivery | No-cloud adapters, fixtures, simulators, real-controller allowlist guards, strict demo-mock guards, and scripts are committed and packaged | Local temporary demo data |
| Playground display | Packaged runtime is fresh and browser smoke passes after automated gates | URL opens |

## automqbox/CMP Connect Addendum

Use this addendum only when both conditions are true: the target repo/app is
automqbox/CMP, and the feature is Connect-related. For automqbox/CMP non-Connect
features, do not read [references/cmp-playground.md](references/cmp-playground.md)
and do not generate playground artifacts; use generic mock acceptance only.

For automqbox/CMP Connect features, read [references/cmp-playground.md](references/cmp-playground.md) before acceptance. It contains the playground architecture facts, required matrices, fixture graph rules, packaged playground freshness rules, and handoff QA.

Minimum repo-specific gates:

1. Re-read current playground code and record the architecture facts consumed by this run. Generic mock knowledge is not enough.
2. Run the playground contract audit for every affected controller. `REAL_CONTROLLER_PATH` is required. A new or changed controller must be added to `PlaygroundAcceptanceProperties.realControllerClasses`; product acceptance must not be closed by mocking product code.
3. Create and validate the playground simulation contract:
   `playground-external-dependency-contract.yaml`,
   `playground-domain-fixture-graph.yaml`, and
   `playground-scenario-graph.yaml`. These rows define the no-cloud business
   world and the external-only mock boundary.
4. Run the fixture graph script and fix or contractually waive every blocking row.
5. Execute and record the fast backend matrix. It must cover real controller/service/manager/task/no-cloud-adapter/state combinations, including success, failure, boundary, terminal, retry/idempotency and external-output-to-consumer-input paths.
6. Execute and record the fast frontend action matrix. It must cover route/component/API-client/DOM/payload combinations, including mode switches, selector states, submit/update/resize/delete actions, loading/empty/error states and negative mode leakage.
7. Produce the strict case artifacts above plus `CMP Playground Architecture Matrix`, `Fixture Graph Matrix`, `Playground Simulation Contract`, and `CMP Playground Coverage Matrix` inside `mock-acceptance.md`.
8. Use packaged playground only after the two fast matrices and playground simulation contract pass. After frontend changes, rebuild frontend, repackage backend/static artifact, and restart the process.
9. Execute representative real browser packaged cases for every new or modified lifecycle family: create/check/submit, progress/change, detail, update/resize, delete, metrics/logs/workers where applicable. Selectors must be expanded and real options selected.
10. Verify progress/change after create/update/resize/delete; list/detail/progress states must agree.
11. Run top-level application smoke across Instances, Connect Clusters, Connectors, Plugins, Accounts/Access, and Support/Settings. This cannot replace fast matrix execution or packaged representative cases.

Useful commands:

```bash
python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/cmp_playground_contract_audit.py \
  --repo /path/to/automqbox \
  --controllers ConnectorController,ConnectClusterController,ProviderController \
  --out specs/changes/<change-id>/acceptance/cmp-playground-contract-audit.md

python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/cmp_playground_fixture_graph_audit.py \
  --repo /path/to/automqbox

python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/validate_playground_simulation_contract.py \
  specs/changes/<change-id> --mode planning
```

`--warn-only` may be used during archaeology, but final acceptance must fail on blocking findings.

After the static scripts, run the strict case validator:

```bash
python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/validate_mock_acceptance_cases.py \
  specs/changes/<change-id>
```

`validate_mock_acceptance_cases.py` automatically invokes
`validate_playground_simulation_contract.py` only when automqbox/CMP Connect
playground scope is explicit and packaged playground signals or the three
playground simulation files are present.

## Mock Delivery Contract

Every mock acceptance artifact needs a delivery row:

```markdown
| Mock artifact | Real contract source | Replaced dependency | Tested real code path | Drift guard | Owner issue |
|---|---|---|---|---|---|
```

Rules:

- `Real contract source` must be an API spec, real adapter/source code, external documentation, real environment response, locked cross-module contract, or fixture evidence.
- `Replaced dependency` must be cloud API, K8s API, kafka instance API, Kafka Connect REST API, or state owned by the no-cloud external adapter graph. Do not mock the API/controller/service being tested to bypass logic.
- `Tested real code path` must name the real controller/DTO/service/frontend page/action.
- `Drift guard` must check path, body, response shape, enum, error code/message, state machine, terminal state, and unavailable/null semantics.
- Mock code without an owner issue cannot close acceptance.

## Frontend Minimum Closure

For each core flow, prove:

1. Page loads real dependencies such as instance/profile/VPC/subnet/plugin/version.
2. User-visible action maps to route builder/click handler, final route/API, router definition, and landing component.
3. Current mode renders correctly after create/update; old mode fields, text, events, and payload branches have negative assertions.
4. Users can choose mode/resources/capacity and reach review; new selectors are opened and real options selected.
5. Hidden or non-current-mode fields do not submit or validate.
6. Submit triggers the expected API method/path/body, or displays readable field-level errors.
7. Success navigates to progress/detail or next state.
8. Detail/workers/metrics/logs/progress/delete residual pages consume response fields consistently.
9. List/detail/progress/API agree on status, errors, terminal state, and unavailable semantics.

If browser/DOM tooling is missing, record a verification gap, add the closest executable contract regression, and still run real frontend plus mock backend manually or with a browser tool before declaring product acceptance.

Output a local audit:

```markdown
### Frontend User-Flow Local Audit Report

| Flow/action | Has real entry/click/submit? | API/path/payload evidence | Success/failure evidence | Mode negative assertion | Required backflow | Blocks acceptance |
|---|---|---|---|---|---|---:|
```

Block if there is no browser/DOM/equivalent evidence, only payload evidence, submit is not proven, or old-mode leakage has no negative assertion.

In `mock-acceptance-cases.yaml`, every frontend mutation case must have `browser_steps`, `network_assertions`, `dom_assertions`, `api_assertions`, `negative_assertions`, and `evidence_refs`. A case without a real click/select/submit step or without HTTP method/path/body evidence is not executed.

## Backend Minimum Closure

Backend mock acceptance must be generated from the Verification Matrix/API Flow DAG, not from a manual endpoint list. It must cover:

- Dependency list/select -> validate/check -> create -> progress -> detail -> workers/runtime -> metrics/logs -> update/autoscaling -> delete/retry paths.
- Success paths and user-reachable failure paths.
- Mode/capacity/auto-create/select-existing/managed role/existing role/missing resource/invalid resource/dependency unavailable/runtime not ready/residual resource combinations.
- Field-specific or contract-specific mock failures, not generic failure for all errors.
- Externalized/adapter-normalized no-cloud responses equivalent to real external interface output.
- For automqbox/CMP Connect features, no-cloud adapter and fixture output must satisfy frontend selectors and downstream create/update inputs.

Required backend artifacts:

```markdown
| Artifact | Acceptance requirement |
|---|---|
| API Flow Graph | Every core scenario has entry-to-terminal path |
| Edge Contract Matrix | Data carried, precondition, failure, timing, and idempotency are verifiable |
| Path Coverage Matrix | Happy, branch, failure, terminal, transition, retry/idempotency paths are covered |
| State/Time Assertion Matrix | Cross-API state consistency, terminal stop, retry, delete behavior are asserted |
| Orthogonal Dimension Matrix | Coupled dimensions are covered; representative pairs and N/A decisions are justified |
```

Backend rows must be materialized into `mock-backend-matrix.yaml`; report prose is not enough. If a backend combination is user-reachable and can be exercised through real controller/service/manager/task plus mock/no-cloud adapter tests, it belongs in this matrix before packaged/browser acceptance starts.

Output a local audit:

```markdown
### Backend Flow Local Audit Report

| Path/edge | Test/Not Run evidence | State/time assertion | Failure/terminal coverage | Required backflow | Blocks acceptance |
|---|---|---|---|---|---:|
```

Block if matrices are missing, tests only assert HTTP status, failure/terminal/idempotency/retry paths are missing, or provider output to consumer input is unproven.

Backend API smoke must be mapped to case IDs. A statement such as “Connect ASG smoke passed” without a case row, fixture row, network assertion, terminal state assertion, and evidence reference does not close any case.

## Contract Drift Audit

Output:

```markdown
### Contract Source Local Audit Report

| Contract/mock | Source可信? | Mock boundary finding | Drift guard finding | Severity | Required backflow | Blocks acceptance |
|---|---|---|---|---|---|---:|
```

Block if there is no trusted source, the tested API/controller/service is mocked, `REAL_CONTROLLER_PATH` is not covered by static/runtime evidence, or any path/body/response/enum/state/error/progress drift lacks a guard.

## Real Controller / No-Cloud Guard

Mock acceptance must prove affected paths stay on real product code and external calls are intercepted only by no-cloud adapters.

Required order:

1. Use the project strict mode when available. For current automqbox/CMP, set `PACKAGED_RUNTIME_PLAYGROUND_STRICT_MOCK_MODE=true` and `PACKAGED_RUNTIME_PLAYGROUND_CONTROLLER_MOCK_ENABLED=true`.
2. Static audit must show `REAL_CONTROLLER_PATH` for every affected controller. If an affected controller is not allowlisted, that is a runtime capability gap: add it to `PlaygroundAcceptanceProperties.realControllerClasses` and provide no-cloud external adapters/fixtures for its dependencies.
3. Runtime evidence must show each request used the real controller/service path with no-cloud external adapters.
4. If the runtime has no request-level marker, use logs/network/API behavior plus source audit and mark residual risk.
5. Any call to real cloud/K8s/kafka instance/Connect worker outside the no-cloud adapters during no-cloud acceptance is a blocker unless the contract explicitly marks that path out of mock scope.

Output:

```markdown
### Real Controller / No-Cloud Guard Report

| Request/path | Expected route classification | Static coverage | Runtime real/no-cloud evidence | Real external call observed? | Residual risk | Blocks acceptance |
|---|---|---|---|---:|---|---:|
```

Block if a real external call is observed, static real-controller coverage is missing, runtime no-cloud evidence is missing for a core path, or residual risk affects create/update/progress/detail.

## Runtime Freshness Audit

After automated gates and before giving a acceptance URL:

```markdown
### Runtime Freshness Local Audit Report

| Artifact/process | Observed branch/commit/time/PID/port | Fresh? | Smoke evidence | Finding | Blocks display acceptance |
|---|---|---:|---|---|---:|
```

Block if the bundle, package/image/static artifact, process, API smoke, UI submit-flow smoke, or state/terminal/display smoke is stale or missing.

## Loop Review

Execution order:

1. Confirm `Mock Acceptance Plan` exists and still matches the diff.
2. Write/update `mock-test-dimensions.yaml`, `mock-fixture-graph.yaml`, `mock-backend-matrix.yaml`, `mock-frontend-action-matrix.yaml`, and representative `mock-acceptance-cases.yaml`.
3. For automqbox/CMP during mock-acceptance execution, write/update
   `playground-external-dependency-contract.yaml`,
   `playground-domain-fixture-graph.yaml`, and
   `playground-scenario-graph.yaml`.
4. Run static controller routing, fixture graph, and playground simulation audits.
5. Execute backend matrix rows and record row-level command/evidence/result in `mock-acceptance-execution.yaml`.
6. Execute frontend action matrix rows and record row-level command/evidence/result in `mock-acceptance-execution.yaml`.
7. Run `validate_mock_acceptance_cases.py --mode execution --target backend/frontend --owner-task <Txxx>` for the owner tasks; if it fails, fix implementation/tests or the execution ledger before starting packaged/browser acceptance.
8. Start fresh packaged/browser runtime only after the fast matrices pass. For automqbox/CMP Connect features, start packaged playground using the startup contract in `references/cmp-playground.md` only after the playground simulation contract also passes.
9. Execute representative packaged blocking cases with browser/network/API/DOM evidence and write packaged/event-state rows to `mock-acceptance-execution.yaml`.
10. Generate/update `mock-acceptance.md` from sealed matrix/case rows plus `mock-acceptance-execution.yaml` row-level results.
11. Run `validate_mock_acceptance_cases.py` again and `workflowctl.py validate mock-acceptance`.
12. Backend composition acceptance.
13. Frontend user-flow acceptance.
14. Contract drift/static guards.
15. Real-controller/no-cloud guard.
16. Mock delivery guards.
17. playground architecture/fixture/runtime/scenario gates when applicable.
18. Classify failures as `frontend-contract-gap`, `cross-module-contract-gap`, `verification-gap`, `implementation-bug`, `playground-capability-gap`, or `deployment/runtime-data-gap`.
19. Update backflow invalidation, Verification Matrix, affected Atomic Issues, and runtime module tasks when needed.
20. Fix code/artifacts, rerun affected fast matrix rows, rebuild/repackage/restart runtime if needed, then rerun invalidated packaged representative cases.

P0/P1 blockers must be closed before claiming acceptance.

## Outputs

Write or update generic mock acceptance outputs:

```text
specs/changes/<change-id>/mock-backend-matrix.yaml
specs/changes/<change-id>/mock-frontend-action-matrix.yaml
specs/changes/<change-id>/mock-test-dimensions.yaml
specs/changes/<change-id>/mock-acceptance-cases.yaml
specs/changes/<change-id>/mock-fixture-graph.yaml
specs/changes/<change-id>/mock-acceptance-execution.yaml
specs/changes/<change-id>/mock-acceptance.md
specs/changes/<change-id>/verification-matrix.md
specs/changes/<change-id>/acceptance/product-acceptance-review.md
```

For automqbox/CMP Connect playground only, also write or update:

```text
specs/changes/<change-id>/playground-external-dependency-contract.yaml
specs/changes/<change-id>/playground-domain-fixture-graph.yaml
specs/changes/<change-id>/playground-scenario-graph.yaml
```

When gaps are found, append:

```text
specs/changes/<change-id>/backflow-invalidation.md
```

Final reports must distinguish:

- Automated mock acceptance passed or blocked.
- Browser/display smoke passed or blocked.
- Real cloud/runtime smoke not covered or passed.
- Mock acceptance deliverables included as first-class code; for automqbox/CMP Connect features, playground deliverables included as first-class code when applicable.
- Contract Source, Frontend User-Flow, Backend Flow, Runtime Freshness, and repo-specific reports passed or blocked. Any applicable missing report or `Blocks acceptance=yes` prevents declaring mock acceptance complete.
- Every required backend matrix row and frontend action matrix row has terminal `mock-acceptance-execution.yaml` row-level command/evidence before packaged/browser evidence is accepted.
- Every blocking case in `mock-acceptance-cases.yaml` has terminal `mock-acceptance-execution.yaml` browser/network/DOM/API/fixture evidence. Any missing case, skipped case, only-smoke case, or stale evidence prevents declaring mock acceptance complete.
