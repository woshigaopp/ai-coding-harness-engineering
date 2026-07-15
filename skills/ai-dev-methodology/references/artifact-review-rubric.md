# Artifact Review Rubric

Use this rubric when reviewing whether workflow artifacts meet AutoMQ AI coding standards. Scores are 0/1/2. Any 0 blocks the next stage. A stage may proceed only when every required dimension scores 2 or has an explicit approved risk.

## Contents

- [Common Scale](#common-scale)
- [Source Intake Rubric](#source-intake-rubric)
- [Decision Consistency Rubric](#decision-consistency-rubric)
- [PRD Rubric](#prd-rubric)
- [Engineering Propose Rubric](#engineering-propose-rubric)
- [Verification Feasibility Rubric](#verification-feasibility-rubric)
- [Decision Surface Discovery Rubric](#decision-surface-discovery-rubric)
- [Atomic Issue Rubric](#atomic-issue-rubric)
- [Module Boundary Rubric](#module-boundary-rubric)
- [Contract Rubric](#contract-rubric)
- [Verification Rubric](#verification-rubric)
- [Task DAG Rubric](#task-dag-rubric)
- [Backflow Invalidation Rubric](#backflow-invalidation-rubric)

## Common Scale

| Score | Meaning |
|---:|---|
| 0 | Missing, only natural language, or requires implementation-stage guessing |
| 1 | Present but partial; important detail remains in global docs or implicit context |
| 2 | Self-contained, precise, traceable, and directly consumable by downstream stages |

## Source Intake Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Source inventory | user-provided inputs missing | major sources listed, discovered sources omitted | every user-provided and workflow-discovered behavior source listed |
| Read status | absent or unverifiable | status present but reason/method missing | read/unread/blocked/irrelevant/superseded with method and reason |
| Semantic mapping | absent | broad artifact mapping only | each source maps to REQ/SCN/DEC/C/MIG/VER/T or explicit ignored reason |
| Conflict handling | conflicts implicit | conflict noted without DEC | conflict has locked DEC or blocks next stage |
| Downstream use | unread source used | unclear whether source used | unread/blocked source cannot affect locked artifact |

## Decision Consistency Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Decision key | absent | inconsistent key naming | every active decision has stable key |
| Conflict detection | absent | manual note only | Decision Consistency Matrix compares active decisions by key |
| Supersession | old and new both active | supersession noted but affected artifacts unknown | old decision closed, new decision active, affected DEC/C/T/VER listed |
| Atomic impact | not checked | issue IDs listed only | no active issue references superseded DEC/C/VER |

## PRD Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Propose handling | external doc/conversation treated as PRD | source trace exists but propose/fact/unknown not separated | every source has propose statement, explicit fact, inferred fact, unknown decision, target PRD dimension |
| Code scope discovery | absent | broad file search | discovery seeds, required areas, evidence paths/commands, and stop conditions complete |
| User decision interaction | AI locks product choices without authority | questions listed but responses not written back | authority, recommendation, alternatives, user response, and final PDEC status recorded |
| Current product/code understanding | absent | broad current-state summary | related pages/API/config/state/error/permission/runtime behavior with exact evidence path/command and product implication |
| User/scenario | absent | one generic user story | user, goal, current pain, desired outcome and acceptance scenario explicit |
| Product object model | absent | code objects listed | user-facing objects, properties, lifecycle/state explicit |
| Scope/non-goals | vague | in/out listed but hidden decisions remain | in/out with reason; non-goals do not hide unresolved decisions |
| Config/resource ownership | absent | fields listed only | ownership, default/derivation, missing behavior, visible location, error shown explicit |
| State/error/permission | absent | partial tables | user-visible state, error/recovery, API/UI permission behavior complete |
| Runtime lifecycle | ignored when relevant | create-only | create/update/delete/failure/retry/logs/metrics/auto-adjust acceptance defined or explicit N/A |
| Product decisions | open or implicit | IDs listed only | every PDEC has alternatives, reason, user confirmation or AI authorization, verification |
| Completeness gate | absent | checklist only | each dimension has complete/evidence/open decision/blocks-next-stage and no blocking incomplete row |

## Engineering Propose Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Propose normalization | AIP/draft accepted as final | propose extracted partially | engineering propose, explicit fact, inferred fact, unknown DEC, affected interface/module all mapped |
| Current architecture | absent | broad summary | exact evidence path/command and engineering implication |
| Alternatives | absent | alternatives named | rejected alternatives with reasons and impact |
| Completeness gate | absent | incomplete checklist | architecture/interface/data/deployment/compat/observability/verification all complete or blocked |

## Verification Feasibility Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Environment | absent | environment named only | environment/fixture/account/browser/cloud availability confirmed |
| Setup | absent | owner only | setup command or owner/action recorded |
| Fallback | absent for unavailable required verification | fallback vague | fallback proof has source, expected result, proves, and risk |
| Blocking | unavailable required verification ignored | Not Run noted | Blocks done enforced for required/P0/P1 verification |

## Version Branch Alignment Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Components | missing | some repos listed | every relevant repo/component/version/template listed |
| Evidence | absent | branch names only | existence/alignment evidence recorded |
| Routing | mismatch ignored | mismatch noted | owning repo/action/blocker identified before tasks |

## Artifact Rubric Scorecard Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Coverage | absent | some artifacts scored | every required artifact/dimension scored |
| Evidence | scores without evidence | broad section reference | exact artifact section/path evidence |
| Blocking | score 0 allowed | score 1 unclear | score 0 blocks, score 1 has approved risk or fix action |

## Semantic Consumption Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Upstream inventory | missing | partial IDs listed | every REQ/SCN/PDEC/DEC/C/MIG/VER relevant to the stage listed |
| Consumption | absent or ID-only | broad statement like "covered by design" | how consumed is explicit: copied/transformed/verified/N/A/blocked |
| Derived object | absent | artifact name only | exact DESIGN-DEC/C/VER/Txxx or other downstream object |
| Copied semantics | IDs only | short summary | execution-relevant behavior/decision/contract/verification semantics copied |
| Dropped semantics | dropped silently | reason without decision | dropped only with locked decision or explicit N/A |
| Status gate | blocked ignored | blocked noted only | blocked rows stop next stage; consumed/dropped-with-decision rows can proceed |
| Atomic handoff | issue references PRD/plan | issue has partial excerpts | Atomic Issue contains copied source/decision/contract/verification semantics |

## Decision Surface Discovery Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Experience-shaped triggers | obvious trigger surfaces missing | triggers listed but broad | mode consumer, frontend action, post-create consumer, persistent mutation, operation mutability, managed resource ownership, runtime lifecycle, mock acceptance, observability, permission and compatibility surfaces covered or locked N/A |
| Generative stress tests | absent when applicable, or only says "checked" | stress rows exist but no path trace / broken assumption, or non-applicable tests are omitted without reason | applicable consumer-enumeration, mutation-chain, invariant-breakage, lifecycle-completeness and reverse-acceptance rows include path trace, broken/uncertain assumption, provider owner, consumer owner, mock/acceptance owner or locked N/A, negative assertion and verification; non-applicable test types have locked N/A with reason |
| Path trace quality | no code/product anchors | only page/API or module names | route/component/API/controller/service/task/provider/entity/runtime/mock fixture anchors are concrete enough to be checked |
| Provider vs consumer split | consumer closes provider responsibility | provider/consumer named but broad | production provider owner, consumer owner and mock/acceptance owner are distinct or explicitly locked N/A |
| Candidate handling | candidate surfaces stay in stress table | candidate surfaces copied to inventory only | every candidate surface enters Decision Surface Inventory and Surface Obligation Projection Matrix, then DEC/C/VER/Txxx or locked N/A |
| Negative assertions | absent | generic "no wrong mode" | exact forbidden inherited behavior, internal exception, fake state, wrong provider context, mock/real route drift or overclaim is asserted |
| Closure status | covered/done/handled | mixed statuses | only allowed statuses are used and blocked rows stop next stage |

## Atomic Issue Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Goal | vague task title | states local change | states outcome and source value |
| Module Contract Closure | absent | primary module only | primary module, consumed contracts, provided contracts, internal invariants all explicit |
| Scope | not bounded | files listed only | in-scope and out-of-scope explicit |
| Source Context | IDs only | partial summary | exact necessary excerpts copied |
| Locked Decisions | absent | IDs or summaries | exact decision + why it matters |
| Contract Excerpts | absent | links to plan only | trigger/normal/failure/consistency/timing included |
| Execution Preconditions | absent | upstream task IDs only | already-true facts, evidence, and if-false backflow copied |
| Consumed Contract Snapshot | absent | contract IDs or one-line summaries | provider, consumer-usable facts, field/state/error/timing details, forbidden interpretations copied |
| Provided Contract Obligation | absent | local change only | downstream consumer, required guarantee, observable output/state, and proving verification copied |
| Invariant Carryover | absent | generic compatibility note | source invariant, must-remain-true behavior, and regression check explicit |
| Preconditions Failure Handling | absent | generic "ask user" | stop/backflow classification and forbidden local workaround explicit |
| Code References | absent | general module name | exact file/class/page/test and what to follow |
| Files To Change | absent or vague | module/folder only | exact repo-relative path or precise new-file rule |
| Behavior Details | absent | partial input/output only | input/output/error/state/compat/boundary conditions explicit |
| Implementation Steps | vague | partially actionable | file-level ordered steps |
| Verification | command only or absent | command + expected | command/step + expected + proves + failure meaning |
| Prohibited Changes | absent | generic | task-specific scope and decision prohibitions |
| Done Criteria | absent | generic | concrete completion checks |
| Language | English narrative by default | mixed but unclear | Chinese narrative; code/API identifiers remain original |

## Stage Decision Document Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Per-decision details | range/grouped decisions | some details grouped | every summary ID has one detail section |
| Decision key | absent | present on some decisions | every decision has a stable key and conflict status |
| Alternatives | absent | alternatives listed only | rejected alternatives have reasons |
| Product alignment | absent | broad PRD reference | exact PDEC/REQ/SCN alignment |
| Downstream impact | absent | affected area only | Atomic Issue impact and copied excerpt identified |
| Verification | absent | test type only | exact verification or matrix row with expected result |

## Module Boundary Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Writer ownership | no writer evidence | broad owner named | exact data/resource writer, reader, mutation rule, and evidence |
| State-machine self-containment | not checked | lifecycle summarized | transition-level guard/precondition checked; external preconditions become contracts |
| Change independence | absent | intuition only | git co-change evidence or future independent-change reason with risk |
| Contract enumerability | dependencies are call graph only | some contracts listed | every external dependency is consumed contract; every promise is provided contract |
| Granularity | arbitrary directory/class split | risk mentioned | class/resource count, interface count, interaction count, state-machine count, and single-caller risk checked with keep/split/merge decision |
| Downstream issue fit | not considered | likely can create tasks | module can produce contract-closed Atomic Issues without cross-module implementation |

## Contract Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Source | absent | broad source | exact REQ/SCN/DEC/MIG/hidden constraint |
| Provider/consumer | absent | modules named only | provider module and consumer module(s) with assumptions |
| Trigger | absent | vague event | precise condition |
| Normal path | absent | one-sided behavior | both sides state/data changes |
| Failure path | absent | generic error | unavailable/failure/timeout behavior |
| Consistency | absent | generic consistency | exact invariant and mechanism |
| Timing | absent | vague order | order/concurrency/idempotency/retry semantics |
| Verification | absent | test type only | exact proof and expected result |
| Atomic mapping | absent | issue ID only | excerpt and verification copied into issue |
| Materialization source | absent | provider/consumer summary only | provider facts, consumer facts, field/state/error/timing details, preconditions, obligations, and forbidden interpretations copyable into Atomic Issues |

## Contract Discovery Coverage Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Source areas | only obvious API paths | some areas covered | REQ/SCN, module edges, shared data, async/event, frontend/API, cloud/runtime, observability, migration diff covered |
| Evidence reviewed | absent | source names only | exact file/path/doc/runtime evidence reviewed |
| Candidate handling | missing candidates | candidates listed without disposition | every candidate becomes locked contract, explicit N/A, or residual risk |
| Residual risk | hidden | risk noted only | residual risk enters Verification Matrix or Not Run table with owner |

## Verification Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Source coverage | source missing | partial source | every REQ/SCN/DEC/Contract/Migration covered |
| Command/step | absent | generic | exact command or repeatable manual step |
| Expected result | absent | vague pass/fail | concrete status/body/DB/UI/grep/plan/log result |
| Proves | absent | implicit | maps to exact source and behavior |
| Module boundary validation | absent | module-local inspection only | boundary risk has proof or approved Not Run risk |
| Module composition verification | absent | separate module tests only | provider output satisfies consumer assumption and REQ/SCN holds |
| Runtime realism | mocks only for runtime behavior | partial fixture | representative fixture or runtime smoke |
| Not Run risk | absent | reason only | source + severity + risk + owner/approval + blocks-done status |
| Blocking semantics | P0/P1 Not Run ignored | blocking noted but done still ambiguous | P0/P1 or Blocks done=yes prevents done unless user/owner accepts risk |

## Task DAG Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Nodes | missing tasks | tasks listed without module/contracts | every task has module, layer, provides, consumes, files, verification gate |
| Edges | absent | dependency names only | every edge has type, reason, and skipped-failure propagation |
| Topological order | absent or natural-language order | order present but unproven | provider/consumer, migration/schema, verification gate order valid |
| Parallel groups | `[P]` by intuition | disjointness partially checked | files, contracts, verification and failure propagation all disjoint |

## Backflow Invalidation Rubric

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Trigger | missing | symptom only | found-in, category, earliest missing stage, required backflow recorded |
| Invalidation | local fix only | affected files listed | invalidated artifacts, decisions, contracts, issues, verification listed |
| Supersession | old refs remain | supersession noted | old DEC/C/T/VER closed and no active issue references them |
| Rerun | not planned | rerun type listed | exact verification rerun or Not Run with blocking status |
