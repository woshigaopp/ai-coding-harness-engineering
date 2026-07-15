# Launch Readiness Review

This is the final post-PR convergence gate. It starts only after atomic execution, applicable mock/product acceptance, and integration PR creation or equivalent diff publication. Do not sign it with `workflowctl.py pass-stage`; validate it with `workflowctl.py validate-launch-readiness specs/changes/<change-id>`.

## Review Input

| Field | Value |
|---|---|
| Integration PR / diff artifact | <GitHub PR URL/ID, or exact path to an equivalent review artifact that declares Head> |
| Base | <base branch or commit> |
| Head | <current local Git HEAD commit SHA; branch name alone is insufficient> |
| Diff source | <PR compare URL, or equivalent artifact evidence containing current Head SHA and artifact SHA-256> |
| Review date | <YYYY-MM-DD> |
| Reviewer | <main agent / reviewer identity> |

## Production Launch Standard Sources

| Source | Path / URL / ID | How it defines launch standard |
|---|---|---|
| Product requirement | proposal.md / spec.md / REQ-xxx / SCN-xxx | <user-visible behavior, scope, errors, permissions, acceptance> |
| AIP / engineering decision | aip.md / plan.md / ADEC-xxx / DEC-xxx | <architecture, external dependency, compatibility, observability> |
| Contract source | contracts.yaml / C-xxx | <cross-module semantic contract> |
| Verification source | verification.yaml / VER-xxx | <required proof and expected result> |
| Acceptance evidence | mock-acceptance.md / mock-acceptance-execution.yaml / acceptance/product-acceptance-review.md / N/A with risk | <evidence used by this review> |
| Actual implementation | PR diff / changed files | <production behavior being reviewed> |

## Closure Review

| Closure | Review question | Evidence | Verdict | Notes |
|---|---|---|---|---|
| User journey | Key requirement user journeys are end-to-end closed through real entry points or equivalent acceptance runtime. | <PR/API/browser/runtime evidence> | pass/fail | <notes> |
| Domain semantic | Core domain semantics are implemented as behavior, not only fields, DTOs, pages, or fixture shapes. | <code/test/evidence> | pass/fail | <notes> |
| Runtime / external effect | Required provider/API/runtime side effects actually occur and have readback, adapter evidence, or explicit Not Run risk. | <provider/mock/readback evidence> | pass/fail | <notes> |
| State and failure | State, errors, retry, rollback, partial success, unavailable dependency, and permission failures match runtime semantics. | <test/log/event/progress evidence> | pass/fail | <notes> |
| Compatibility and boundary | Existing/new modes, compatibility paths, mutually exclusive fields, permissions, and mode boundaries do not leak. | <API/UI/DB/backward compatibility evidence> | pass/fail | <notes> |
| Acceptance evidence | Evidence covers representative launch scenarios, not only point existence or unit compilation. | <mock/product/packaged/browser/provider evidence> | pass/fail | <notes> |

## Findings

Allowed `Type` values: `implementation_gap`, `atomic_task_gap`, `launch_decision_required`, `acceptance_gap`, `methodology_gap`, `allowed_implementation_variance`.

`launch_decision_required` means the final review found a launch-time decision that implementation cannot make alone. Resolve it by asking the human owner in this final gate and recording the decision, accepted risk, or scope adjustment here. Do not backflow to PRD/AIP/contracts/Atomic Issues from this final gate.

| ID | Type | Severity | Source / evidence | Owner | Required action | Status |
|---|---|---|---|---|---|---|
| LRR-001 | allowed_implementation_variance | non-blocking | <PR and requirement evidence> | <owner> | <record final variance> | closed |

## Resolution Ledger

| Item | Finding ID | Action type | Artifact / code changed | Verification rerun | Result |
|---|---|---|---|---|---|
| LRR-FIX-001 | LRR-001 | none | N/A | N/A | closed |

## Final Verdict

launch_ready: yes/no
open_launch_blockers: 0

Decision: <ready / not ready / ready with accepted non-blocking risks>
