# automqbox/CMP Packaged Playground Acceptance Knowledge Base

Use this reference only when the target repo or app is automqbox/CMP and the
feature is Connect-related, or when the task explicitly changes the playground
foundation itself. For automqbox/CMP non-Connect work, do not load this file;
use generic mock acceptance instead.

This file is a reusable knowledge base, not a one-off checklist. Before changing
playground code or accepting a acceptance URL, re-read the current repository
code and compare it with the architecture below. If the code has drifted, update
this reference and the audit scripts before relying on old assumptions.

## Core Position

packaged playground is a pre-release product acceptance runtime. It is not a mock
server, Storybook page, API smoke target, or demo data dump.

The acceptance rule is:

```text
real frontend page/action/API client
  -> real HTTP route
  -> real controller method
  -> real DTO/VO shape
  -> real service/manager/task/repository contract semantics
  -> no-cloud adapters for physical external interfaces only
```

Allowed simulation boundary is exactly the physical external interfaces:
cloud API, K8s API, kafka instance API, and Kafka Connect REST API. Metrics are
exposed through the Connect `/metrics` endpoint, and logs are exposed through the
K8s pod logs API; they are not permission to mock product metrics/log services.
Seeded SQLite/no-cloud graph state is support data for those adapters and real
services, not a free product-logic mock category.

Forbidden mocks are product logic: frontend components, API clients, controller
methods, DTO/VO schema, service contract semantics, route names, payload shapes,
action semantics, progress state names, and visible user feedback.

If a browser flow passes because the frontend is fed static data, a mock-only
endpoint is added, or a controller/service/task/repository path is bypassed,
playground acceptance is invalid.

## Verified Architecture Facts

These facts were verified from current target packaged playground code and must be
rechecked when the runtime module changes.

| Area | Current mechanism | Acceptance implication |
|---|---|---|
| Packaging | `cmp/cmp-app/pom.xml` `playground` profile packages `cmp-playground` into the Spring Boot JAR. | Playground acceptance is the same `cmp-app` runtime with extra playground classes on the classpath; it is not a separate mock server. |
| Runtime profile | Start the JAR with `--spring.profiles.active=playground`. | Only `@Profile("playground")` beans become active; product controllers/services/managers/tasks remain the real classes. |
| Product path | `ConnectClusterController`, `ConnectorController`, `ConnectClusterServiceImpl`, `ConnectorServiceImpl`, deploy managers, task factories/steps, DTO/VO/domain/repository paths run as real code. | Acceptance must prove business behavior through real product paths, not classpath replacement or same-name class shadowing. |
| Real-controller allowlist | `PlaygroundAcceptanceProperties.realControllerClasses` allowlists product controllers that must run as real product code, including `FrontendController`, `HealthCheckController`, `StaticProxyController`, `AuthorizationController`, `InstanceController`, `TopicController`, `ConnectClusterController`, `ConnectorController`, `ConnectorPluginController`, and `ProviderController`. | Every affected product controller must audit as `REAL_CONTROLLER_PATH`. If a feature adds a controller, add it to this allowlist and test the real route. |
| Strict mode | `PACKAGED_RUNTIME_PLAYGROUND_STRICT_MOCK_MODE=true` is a fail-fast guard for playground routing errors. | It is not a permission to accept product behavior through product mocks. |
| Cloud adapter | `NoCloudInfraProvider` is `@Primary @Profile("playground") implements InfraProvider`; `NoCloudRuntimeSimulator` owns cloud/provider runtime state. | Provider selector flows must expand real ProviderController/API-client endpoints and choose adapter-backed options. |
| K8s adapter | `NoCloudKubernetesApiServer` is a local API server, and `NoCloudInfraProvider` writes kubeconfig to point K8s clients at it. | Real service/task code may call Kubernetes operators; the physical K8s API is the simulated boundary. |
| Kafka instance adapter | `NoCloudInstanceOperator` is `@Primary @Profile("playground") implements InstanceOperator`. | ConnectCluster/Connector flows must consume real instance APIs backed by the no-cloud graph. |
| Connect REST adapter | `NoCloudConnectRestClient` is `@Primary @Profile("playground") extends ConnectRestClient` and delegates to `NoCloudRuntimeSimulator`. | Connector create/status/tasks/workers/restart/pause/resume/delete must exercise real Connector service logic; only worker REST is simulated. |
| Metrics endpoint | `NoCloudMetricsServer` exposes Prometheus text consumed through real Connect metrics paths. | Metrics tests must prove parser-compatible text and real service consumption, not product metrics service mocks. |
| Seeder/graph | `PlaygroundDatabaseSeeder` plus `NoCloudRuntimeSimulator` seed provider, instance, runtime, task/change/event, metrics, and logs graph data. | Fixture graph rows must map to seeded/created ids and downstream pages. |
| Smoke script | `cmp-playground/scripts/runtime-smoke.js` starts/uses packaged playground and verifies golden ConnectCluster/Connector flows. | It is representative integration evidence after matrices pass, not a replacement for row-level matrices. |
| Frontend packaging | Vite build copies output to `cmp-app/src/main/resources/static`; `cmp-app -Pplayground` includes `cmp-playground` and `cmp-provider-aws`. | After frontend changes, rebuild frontend, repackage `cmp-app -Pplayground`, restart the exact process, and prove bundle/package freshness. |

## Packaged Runtime Pitfalls

These are reusable packaged playground traps. They must be checked before
the agent spends time hand-debugging a browser session.

| Pitfall | Symptom | Required prevention / response |
|---|---|---|
| Affected controller not allowlisted | New route works in ordinary app but playground acceptance cannot prove it is on the real product path. | Add the controller to `PlaygroundAcceptanceProperties.realControllerClasses`, rerun `cmp_playground_contract_audit.py`, and cover it in backend/frontend matrices. |
| Product class replacement | `cmp-playground` adds a product controller/service/manager/task/model package or same-name class. | Remove the replacement. Add or extend a no-cloud external dependency bean instead. |
| Stale `main-*.js` in JAR | HTML injects an old bundle, or JAR contains multiple `static/main-*.js` files after repeated builds. | Use `clean package` when static files changed, prefer manifest-driven entry selection, and prove HTML script tag matches the intended JAR entry. |
| `target/classes` static residue | Maven package contains old static resources copied from a previous build. | Check JAR contents for main bundle count and static asset mtime. Do not rely only on `src/main/resources/static` listing. |
| Runtime process freshness drift | Old Java process or screen session still serves an earlier JAR/bundle. | Record PID, app port, ops port, command line, JAR mtime, log path, `user.home`, and HTML script hash after restart. Verify with `lsof`/`ps`, not `screen -ls` alone. |
| Ops port residue | App port is free but ops/management port is still occupied, causing startup failure or confusing partial restarts. | Check both app and ops ports before startup. If the owner is not the current acceptance process, choose a fresh port pair and record it. |
| Missing log directory | Shell redirection fails before Java starts because `target/` was cleaned. | Create the log directory before starting the packaged process. |
| Ace dynamic resource path | Browser requests `/static/theme-dawn.js`, `/static/mode-yaml.js`, `/static/mode-properties.js`, `/static/ext-language_tools.js`, or `/static/worker-yaml.js` and receives 404/500/HTML. | Bundle required Ace modes/themes/extensions explicitly or disable unsupported workers. Browser audit must assert no raw Ace `/static/*.js` requests and no worker runtime exception. |
| Ace YAML worker packaging | Vite emits worker as a module/asset, but Ace expects a classic worker and throws runtime errors. | Prefer disabling the YAML worker when the component already has synchronous `js-yaml` validation, or provide a proven classic-worker asset path. |
| `automq-ui` table static items mode | Top-level pages such as `/system` throw `Cannot read properties of undefined (reading 'send')` when a table with static `items` still auto-calls `props.api.send()`. | Mark static tables as manual request or pass a valid API object. Top-level smoke must catch runtime exceptions. |
| Node module mode mismatch | Ad hoc evidence scripts fail before testing because `require` and top-level `await` are mixed under modern Node. | Use checked-in scripts or pure ESM (`node --input-type=module`) for generated evidence commands. |

Run the runtime audit after the packaged process starts:

```bash
python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/cmp_packaged_playground_runtime_audit.py \
  --repo /path/to/automqbox \
  --base-url http://127.0.0.1:<app-port> \
  --out specs/changes/<change-id>/acceptance/cmp-playground-audit.json
```

This audit does not replace user-flow cases. It proves packaged playground
freshness, static resource sanity, browser route health, and known global
runtime pitfalls before row-level product cases are accepted.

## Real-vs-Mock Boundary

Every mock acceptance plan and case must classify each layer.

| Layer | Must be real | May be mocked | Forbidden mock |
|---|---|---|---|
| Browser/UI | route, rendered page, form controls, action buttons, tabs, disabled/error/warning states | none | static fake page, hidden test-only route, manual DOM injection |
| Frontend code | page component, action handler, API client, route builder, request payload construction | none | mocking API client, bypassing route/action code, calling helper directly as proof |
| HTTP/API | method/path/body/status through the real API client and backend route | network capture tooling only | mock-only endpoint, direct service call as acceptance proof |
| Backend entry | real controller class/method, real DTO validation, real VO response shape | none | bypassing controller, changing DTO only in mock |
| Business contract | validation semantics, action split, mode semantics, progress/change/event contract | none | success-for-all mock service, generic HTTP 200, losing error/warning states |
| External dependency | service/manager/task call sites stay real | deterministic no-cloud adapter/simulator for cloud API, K8s API, kafka instance API, Connect REST API | calling real cloud/K8s/Connect worker in no-cloud acceptance, or replacing product logic as an external dependency |
| Data state | coherent seeded SQLite/no-cloud graph plus `mock-fixture-graph.yaml` | generated fixture values that match locked external contracts | dangling JSON, isolated static object, missing progress/detail state |

## Playground Simulation Contract

packaged playground must behave like a no-cloud semantic simulation environment. It
is allowed to replace external dependencies, but it is not allowed to replace
product behavior.

The required shape is:

```text
real browser route/action
  -> real frontend API client
  -> real HTTP method/path/body
  -> real controller method and DTO/VO
  -> real service/manager/task/repository contract
  -> playground simulator for physical external dependencies only
  -> coherent seeded DB/no-cloud graph
  -> downstream real pages consume the same ids and states
```

If the current runtime module cannot support a required selector state,
external REST/K8s state, event/progress transition, connector downstream edge,
metrics/logs branch, or fixture relation, change `cmp-playground` itself. Do not
reduce acceptance to what the old mock happens to support, and do not add
mock-only frontend/API shortcuts.

Required artifacts for automqbox/CMP Connect changes:

```text
specs/changes/<change-id>/playground-external-dependency-contract.yaml
specs/changes/<change-id>/playground-domain-fixture-graph.yaml
specs/changes/<change-id>/playground-scenario-graph.yaml
```

Validate them before implementation and again during acceptance:

```bash
python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/validate_playground_simulation_contract.py \
  specs/changes/<change-id> --mode planning
```

`validate_mock_acceptance_cases.py` also invokes this gate only when explicit
automqbox/CMP Connect playground scope is present.

### External Dependency Contract

`playground-external-dependency-contract.yaml` defines what may be mocked.
Allowed dependency categories are `cloud-api`, `k8s-api`,
`kafka-instance-api`, and `connect-rest-api`.

Each row must declare:

- external dependency id such as `EXT-001`.
- category and real dependency being replaced.
- trusted contract source.
- `implemented_by` / `simulated_by` adapter, simulator, and seeded persistence owner.
- allowed mock boundary and forbidden product mocks.
- request, response, error, and status semantics.
- fixture refs, scenario refs, real consumers, drift guards, and result.

Examples:

- Provider selectors: region -> VPC -> subnet/security group/IAM/instance type;
  parent reset clears children; explicit unreachable blocks; unknown
  reachability is warning-only if locked by product contract.
- Connect REST API: Connect worker availability, worker ids with port `8083`,
  connector task placement, pause/resume/restart/delete, runtime unavailable
  branches, and `/metrics` endpoint variants.
- K8s API: deployment/pod state and pod log variants: available, empty,
  filtered, truncated, query error, and unavailable.
- Kafka instance API: instance listing/detail/operator semantics consumed by
  ConnectCluster and Connector flows.

### Domain Fixture Graph

`playground-domain-fixture-graph.yaml` is the business-world graph. It prevents
the common failure where create page works but detail, progress, events,
connectors, metrics, or logs have no coherent data.

For Connect features, the graph must include these fixture types unless a
locked N/A decision removes the domain:

| Type | Meaning |
|---|---|
| `provider-resource` | Provider profile/region/VPC/subnet/SG/IAM/instance type selector world. |
| `kafka-instance` | Real Kafka instance fixture consumed by ConnectCluster and Connector create. |
| `connect-cluster` | Deployment mode, worker spec, capacity, resolved config, lifecycle state. |
| `worker` | Runtime worker ids/status/port 8083/worker count. |
| `connector` | Connector id, cluster id, plugin, config, task count, lifecycle state. |
| `connector-task` | Runtime tasks and worker assignment. |
| `change-progress` | create/update/resize/delete progress/change id, steps, terminal state. |
| `event` | visible events and autoscaling decisions. |
| `metrics` | cluster/connector metrics variants. |
| `logs` | cluster/connector log entries, filters, empty/unavailable/truncated states. |

Each fixture must declare parents, children, external dependency refs, API
consumers, scenario refs, case refs, backend matrix refs, and frontend action
refs. A fixture that is not consumed by a scenario is dead data.

### Scenario Graph

`playground-scenario-graph.yaml` defines ordered user scenarios and is stricter
than packaged browser smoke. For ConnectCluster create, the scenario must keep
walking after creation:

1. open create page.
2. load provider/instance/plugin selector data.
3. select mode-specific infrastructure and capacity.
4. run check/create through real API client and real controller.
5. follow progress/change to terminal or in-progress state.
6. open detail and verify mode-specific fields/actions.
7. create a connector on the created cluster.
8. inspect connector detail, tasks, workers, metrics, and logs.
9. run update/resize/delete and verify progress/change/events.

Required negative assertions include:

- ASG detail does not show K8s namespace/serviceAccount/scheduling-only fields.
- ASG action menu does not navigate to K8s-only update/config routes.
- K8s mode does not show ASG-only infrastructure selectors.
- inactive mode fields are absent from DOM and payload.
- no mock-only endpoint is called.
- no call to real cloud/K8s/kafka instance/Connect worker occurs outside
  the no-cloud adapters.

If any ordered step cannot be expressed in the current playground, record a
`playground-capability-gap` and add or update playground code. This backflow is
part of the product implementation, not a nice-to-have mock cleanup.

## Controller Routing Contract

For every affected controller, final acceptance must run:

```bash
python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/cmp_playground_contract_audit.py \
  --repo /path/to/automqbox \
  --controllers ConnectorController,ConnectClusterController,ProviderController \
  --out specs/changes/<change-id>/acceptance/cmp-playground-contract-audit.md
```

Use `--controllers` for the affected domains. Omit it only for a full
playground audit. `--warn-only` is allowed during archaeology, never for final
acceptance.

The static gate must treat `REAL_CONTROLLER_PATH` as required for every affected
controller. These findings block acceptance:

- `NOT_REAL_CONTROLLER_PATH`: an affected controller is not in `realControllerClasses`.
- `CONTROLLER_NOT_FOUND`: the requested controller name/FQCN cannot be found.
- `ALLOWLIST_NOT_FOUND`: the current playground foundation does not expose a real-controller allowlist.
- `PRODUCT_CLASS_REPLACEMENT`: `cmp-playground` defines product controller/service/manager/task/model classes instead of no-cloud dependency beans.

For a new controller, the correct fix is: add it to
`PlaygroundAcceptanceProperties.realControllerClasses`, seed or create the real
SQLite/no-cloud graph data it needs, add/extend only external dependency
adapters, then add backend/frontend matrix rows and packaged representative
cases. Do not add product mocks to close acceptance.

## Adding New Playground-Covered Feature Or Controller

When a requirement adds a new product controller, route, action, or external
dependency use, update playground through the real-product-path model:

1. Add or verify the controller in
   `PlaygroundAcceptanceProperties.realControllerClasses`, then run
   `cmp_playground_contract_audit.py --controllers <Controller>`.
2. Keep the controller/service/manager/task/DTO/VO/repository classes real. Do
   not add same-name product classes under `cmp-playground`, do not classpath
   shadow product code, and do not add a mock-only endpoint.
3. Identify physical external dependencies used by the new path. The only
   acceptable replacement categories are cloud API, K8s API, kafka instance API,
   and Kafka Connect REST API.
4. Extend the corresponding no-cloud bean or simulator:
   `NoCloudInfraProvider`, `NoCloudKubernetesApiServer`,
   `NoCloudInstanceOperator`, `NoCloudConnectRestClient`,
   `NoCloudMetricsServer`, or `NoCloudRuntimeSimulator`.
5. Seed or create coherent real data in `PlaygroundDatabaseSeeder`,
   repositories, or the no-cloud runtime graph. The data must be keyed by the
   same ids consumed by list, detail, progress/change, events, connector,
   metrics, and logs pages.
6. Add or update `playground-external-dependency-contract.yaml`,
   `playground-domain-fixture-graph.yaml`, `playground-scenario-graph.yaml`,
   backend matrix rows, frontend action rows, event-state rows when applicable,
   and representative packaged cases.
7. Run the validators before implementation is marked executable and again
   after acceptance evidence is recorded.

If one of these steps cannot be completed, classify it as
`playground-capability-gap` and create an implementation task for
`cmp-playground`. The correct response is to improve playground, not to lower
acceptance coverage.

## Fixture Graph Contract

Fixture data is a graph, not a bag of JSON.

Each fixture must declare:

- `fixture_id`
- `type`
- `contract_source`
- `provides`
- `consumed_by`
- parent references and downstream references where applicable
- states/errors/warnings it can drive
- case ids or coverage sets that consume it

Required graph properties:

| Domain | Required edges |
|---|---|
| Provider selector | profile/region -> VPC -> zone/subnet -> security group -> IAM role/profile -> instance type. Parent changes reset child selections. |
| Instance | instance id, provider, region, profile, VPC/subnet/SG/IAM, state, endpoints, capability/mode fields used by dependent pages. |
| ConnectCluster | cluster id, Kafka instance, deployment mode, worker spec, capacity, compute config, resolved config, workers, metrics/logs, progress/change, events/scaling decisions. |
| Connector | connector id, connect cluster, Kafka instance, plugin/class/version, task count, runtime tasks/workers, metrics/logs, progress/change. |
| Progress/change | create, update, resize, spec update, delete/retry, failed/gated/warning branches; list/detail/progress must agree. |
| Mode leakage | inactive mode fields must be absent from DOM and payload, not merely ignored by backend. |

Dangling references, empty selectors, disabled controls, return type drift, enum
drift, missing progress state, missing terminal state, or mode-specific detail
leakage are blockers.

`mock-fixture-graph.yaml` is the final acceptance source of truth even when
fixtures are seeded in Java code rather than JSON resources. Code-seeded
fixtures must still be represented in the graph so reviewers can see what user
flows they support.

## Required Case System

Do not accept prose such as "full lifecycle covered". Convert product semantics
into finite dimensions and concrete cases.

packaged playground acceptance uses three layers:

```text
Backend Mock Matrix
  -> fast real controller/service/manager/task/no-cloud-adapter/state coverage
Frontend Action Matrix
  -> fast real route/component/API-client/DOM/payload coverage
Packaged Playground Representative Cases
  -> final integration, packaging freshness, real browser routing and handoff QA
```

The backend and frontend matrices are the exhaustive combination surface.
Packaged playground cases are representative integration samples and must
reference matrix rows. Do not move every combination into the slow packaged
runtime by default.

Common dimensions:

- user flow/action: list, create, check, review, submit, progress, detail,
  update, resize, spec update, delete, workers, metrics, logs.
- mode/capacity/spec: deployment mode, capacity mode, worker spec type,
  autoscaling policy.
- selector/resource state: default, auto-create, existing, derived, empty,
  permission error, wrong parent, invalid candidate, parent reset.
- runtime/state: creating, running, failed, deleting, terminal, unavailable,
  query error, empty data.
- negative assertions: no old-mode fields in DOM, no hidden inactive payload
  fields, no wrong route, no raw ID main path, no real external call outside no-cloud adapters.

Required artifacts:

```text
specs/changes/<change-id>/mock-backend-matrix.yaml
specs/changes/<change-id>/mock-frontend-action-matrix.yaml
specs/changes/<change-id>/mock-test-dimensions.yaml
specs/changes/<change-id>/mock-acceptance-cases.yaml
specs/changes/<change-id>/mock-fixture-graph.yaml
specs/changes/<change-id>/mock-acceptance.md
```

`mock-test-dimensions.yaml` coverage sets must declare target layers:
`backend_matrix`, `frontend_action_matrix`, or `packaged_cases`.

`mock-backend-matrix.yaml` rows must prove real controller/service/manager/task
plus no-cloud adapter behavior without starting packaged browser
runtime. Rows carry coverage sets, dimensions, method/path/request shape,
fixture refs, state assertions, command, evidence, expected result and result.

`mock-frontend-action-matrix.yaml` rows must prove real page/action/API-client
behavior with fixture-backed responses. Rows carry coverage sets, dimensions,
route/component, user action, API client, browser/user steps, network assertions,
DOM assertions, negative assertions, command, evidence, expected result and
result.

Each blocking case must include:

- case id and coverage set
- backend matrix refs and frontend action refs
- dimensions
- user goal
- frontend route
- real code under test: frontend page, API client, controller, DTO/service
- mocked external dependencies
- forbidden mocks
- fixture refs
- browser steps with real click/select/type/submit when mutation is involved
- network assertions with method/path/body/status
- DOM assertions
- API assertions
- negative assertions
- evidence refs: trace/HAR/screenshot/log
- result
- blocks acceptance

Mutation cases cannot be closed by unit tests, typecheck, page-load smoke, HTTP
200, route smoke, or API smoke alone. They require browser action evidence:

```text
click/select/type/submit
  -> network method/path/body/status
  -> response or field-specific error
  -> authoritative state owner write
  -> detail/list/progress/event readback of the same id
  -> DOM feedback/navigation/next state
```

Backend matrix rows for mutation flows must prove the same state owner at fast
test speed before packaged cases run. For automqbox/CMP this is usually real
SQLite/MyBatis/repository state, a task/change/event table, or a no-cloud
runtime graph/resource owner reached through real product code. A fixture object
constructed inside a simulator test is not enough unless the row is explicitly a
fixture-shape row and does not claim create/update/delete success.

## Mock Acceptance Report Contract

`mock-acceptance.md` must contain the generic strict mock acceptance sections and
repo-specific sections:

- `Mock Acceptance Summary`
- `Acceptance Context Rehydration`
- `Dimension Coverage Matrix`
- `Backend Mock Matrix`
- `Frontend Action Matrix`
- `Case Execution Matrix`
- `Fixture Graph Matrix`
- `CMP Playground Architecture Matrix`
- `CMP Playground Coverage Matrix`
- `Frontend User-Flow Local Audit Report`
- `Backend Flow Local Audit Report`
- `Contract Source Local Audit Report`
- `Real Controller / No-Cloud Guard Report`
- `Runtime Freshness Local Audit Report`
- `Packaged Playground Handoff QA`
- `Not Run And Cloud Boundary`

Every row in `Backend Mock Matrix`, `Frontend Action Matrix`,
`CMP Playground Architecture Matrix`, `Fixture Graph Matrix`, and
`CMP Playground Coverage Matrix` must reference a row id, `case_id`, or a locked
N/A decision. Rows without cases or matrix evidence are untested behavior. Cases
without backend and frontend matrix refs are not product acceptance coverage.

## Packaged Runtime Freshness

Only start packaged playground after backend and frontend matrices pass. If the
fast matrices are failing, a runtime browser check run is only a symptom finder; it
cannot close acceptance.

The packaged playground is the real `cmp-app` Spring Boot JAR with the playground
profile active. Do not start a sidecar mock server, dev-only mock controller, or
classpath replacement of product code. `cmp-playground` is present because
`cmp-app -Pplayground` packages it as a dependency; its `@Profile("playground")
@Primary` beans replace only physical external dependencies.

Before handing a acceptance URL to a user:

1. Confirm backend matrix, frontend action matrix, event-state matrix when
   applicable, controller audit, fixture graph audit, and simulation contract
   validation have passed.
2. Rebuild frontend after frontend changes.
3. Repackage backend/static artifact after frontend build.
4. Start a fresh packaged playground process with isolated app, ops, K8s API,
   Connect REST, and metrics ports.
5. Restart rather than reusing a previous process when code, static resources,
   fixture graph, or no-cloud adapter code changed.
6. Verify the exact process and ports before running browser cases.
7. Run packaged playground runtime audit and representative browser cases.
8. Run top-level automqbox/CMP smoke for Instances, Connect Clusters, Connectors,
   Plugins, Accounts/Access, and Support/Settings.

Record branch, commit, frontend build command, frontend bundle file,
bundle mtime, package/JAR mtime, PID, app port, ops port, K8s API port, Connect
REST port, metrics port, log path, `user.home`, target URL, and health/API
evidence.

Use this command shape, adjusted per worktree and free ports:

```bash
pnpm --dir frontend/app build
./mvnw -pl cmp/cmp-app -am -Pplayground -DskipTests -Dcheckstyle.skip=true -Dpmd.skip=true package

mkdir -p <worktree>/target/runtime-logs <worktree>/target/runtime-home

PACKAGED_RUNTIME_PLAYGROUND_STRICT_MOCK_MODE=true \
PACKAGED_RUNTIME_PLAYGROUND_CONTROLLER_MOCK_ENABLED=true \
PACKAGED_RUNTIME_PLAYGROUND_K8S_API_PORT=<k8s-api-port> \
PACKAGED_RUNTIME_PLAYGROUND_CONNECT_REST_PORT=<connect-rest-port> \
PACKAGED_RUNTIME_PLAYGROUND_METRICS_PORT=<metrics-port> \
PACKAGED_RUNTIME_PLAYGROUND_OPS_PORT=<ops-port> \
java -Duser.home=<worktree>/target/runtime-home \
  -jar cmp/cmp-app/target/cmp-app-*.jar \
  --spring.profiles.active=playground \
  --server.port=<app-port> \
  > <worktree>/target/runtime-logs/cmp-playground.log 2>&1 &
```

Notes:

- `--management.server.port` may be supplied directly, but the current
  runtime acceptance profile also reads `PACKAGED_RUNTIME_PLAYGROUND_OPS_PORT`.
- `PACKAGED_RUNTIME_PLAYGROUND_K8S_API_PORT`, `PACKAGED_RUNTIME_PLAYGROUND_CONNECT_REST_PORT`, and
  `PACKAGED_RUNTIME_PLAYGROUND_METRICS_PORT` must be unique and free; they are the no-cloud
  physical dependency endpoints.
- `PACKAGED_RUNTIME_PLAYGROUND_STRICT_MOCK_MODE=true` is required for acceptance runs.
- `PACKAGED_RUNTIME_PLAYGROUND_CONTROLLER_MOCK_ENABLED=true` keeps the routing guard enabled;
  affected product controllers still must audit as `REAL_CONTROLLER_PATH`.
- If the checked-in `cmp-playground/scripts/runtime-smoke.js` is used, it
  may start the packaged process itself. Its app/ops/no-cloud ports and
  `user.home` still count as the runtime freshness record.

After startup, verify:

```bash
lsof -nP -iTCP:<app-port> -sTCP:LISTEN
lsof -nP -iTCP:<ops-port> -sTCP:LISTEN
lsof -nP -iTCP:<k8s-api-port> -sTCP:LISTEN
lsof -nP -iTCP:<connect-rest-port> -sTCP:LISTEN
lsof -nP -iTCP:<metrics-port> -sTCP:LISTEN
ps -fp <pid>
```

Then run:

```bash
python3 /Users/keqing/.codex/skills/mock-acceptance-gate/scripts/cmp_packaged_playground_runtime_audit.py \
  --repo /path/to/automqbox \
  --base-url http://127.0.0.1:<app-port> \
  --out specs/changes/<change-id>/acceptance/cmp-playground-audit.json
```

Only after this audit passes should representative packaged browser cases be
accepted as handoff evidence. A shorthand `java -jar ... --spring.profiles.active=playground`
run without no-cloud ports, strict env, freshness record, and runtime audit is
not enough for product acceptance.

Do not rely on `screen -ls` alone. Verify process ownership with `ps`/`lsof`,
HTTP content types, HTML script tags, actual JS/CSS status, API status, and
browser evidence. If a JS request returns HTML, or CSS/JS/chunks return 404,
500, or wrong MIME, page HTTP 200 is not accepted.

Freshness evidence must include at least:

- frontend build command and exit code.
- `cmp-app -Pplayground` package command and exit code.
- JAR path and mtime.
- app, ops, K8s API, Connect REST, and metrics ports.
- process PID and command line.
- log path.
- `user.home`.
- HTML route, injected `main-*.js`, and absence of stale main hashes.
- JAR `static/main-*.js` entries.
- browser route audit JSON.

## automqbox/CMP Top-Level Smoke

top-level application smoke does not replace case execution. It proves the packaged app
is not globally broken after domain changes.

Required top-level areas:

- Instances
- Connect Clusters
- Connectors
- Plugins
- Accounts/Access
- Support/Settings

For the affected domain, top-level smoke must go deeper than load:

- list page loads and calls real API client
- create/update route opens
- at least one submit-flow or field-specific validation is triggered
- detail/progress opens with coherent state
- logs/metrics/workers/events paths render when relevant

## Common Failure Modes

| Failure | Why it happens | Required response |
|---|---|---|
| Page opens but create cannot submit | Fixture options are missing, selector is disabled, or route/action wiring is incomplete. | Add fixture graph rows and browser case; do not mark route smoke passed. |
| API succeeds but browser flow fails | Frontend action/form state was not tested. | Add browser click/select/submit evidence and DOM assertions. |
| Affected controller is not real path | New controller was added but not allowlisted in `PlaygroundAcceptanceProperties.realControllerClasses`. | Add it to the allowlist, rerun static audit, and test through real HTTP route/controller/service. |
| Mock-only endpoint works | Business path bypassed real controller/API client. | Remove mock-only path and route through real controller. |
| Detail page crashes | VO shape, fixture state, or mode-specific rendering not aligned. | Add detail fixture/state case and negative mode assertions. |
| Progress page is empty | Change/progress/event fixture not linked to created object. | Add progress/change state to fixture graph and case. |
| K8s fields leak into ASG | Mode leakage not asserted in DOM/payload. | Add negative assertions for inactive mode fields. |
| Old bundle is served | Frontend build copied files but app was not repackaged/restarted, or HTML points to stale main script. | Record freshness evidence and restart packaged playground. |
| Smoke passed with no case id | Evidence cannot be traced to requirements. | Treat as supporting evidence only; add row-level case evidence. |
| Preflight/check API returns empty or wrong body | Real controller/service response contract changed but no-cloud adapter or frontend expectation did not. | Add/lock typed response VO, update the no-cloud adapter/fixture graph, run static audit and packaged API evidence. |
| Ace/CodeEditor works in dev but fails in JAR | Dynamic worker/mode/theme resources are not packaged in the path Ace expects. | Use packaged playground runtime audit and browser network proof; no raw Ace `/static/*.js` request may remain. |
| Global top-level page crashes after unrelated feature | Playground acceptance requires top-level application smoke; old component assumptions can break the packaged app. | Fix or explicitly classify as unrelated only with a locked decision; otherwise product handoff stays blocked. |

## Acceptance Exit Rule

Playground acceptance can pass only when all are true:

- Playground contract audit has no blocking rows for affected controllers; every affected controller is reported as `REAL_CONTROLLER_PATH`.
- `mock-test-dimensions.yaml`, `mock-backend-matrix.yaml`,
  `mock-frontend-action-matrix.yaml`, `mock-acceptance-cases.yaml`,
  `mock-fixture-graph.yaml`, and `mock-acceptance.md` pass validation.
- Every required backend matrix row has command/evidence/result.
- Every backend mutation row names the state owner and proves write plus
  detail/list/query readback.
- Every required frontend action matrix row has command/evidence/result.
- Every blocking case has browser, network, DOM, API, negative, fixture, and
  evidence refs.
- Every packaged mutation case proves real submit plus authoritative state
  write/readback; runtime freshness/controller audits are supporting evidence,
  not the terminal proof.
- Every fixture need is represented in the graph and consumed by at least one
  case.
- Packaged runtime freshness is proven after the last relevant frontend/backend
  change.
- `cmp_packaged_playground_runtime_audit.py` has passed for the exact running
  packaged process or an equivalent report proves the same fields.
- top-level application smoke passes.
- Cloud-only or real-external-runtime-only guarantees are explicitly marked Not Run and
  are not claimed from mock evidence.
