---
name: aip-template
description: Steering knowledge for AIP（AutoMQ Improvement Proposal）模板 in automq-kafka-enterprise; use when related questions or implementation decisions appear.
---
# AIP（AutoMQ Improvement Proposal）模板

Use when the user asks about this project steering topic or adjacent decisions.

## Source
- Original file: .kiro/steering/aip-template.md

## How to Use
- Read references/steering.md for the full project memory content.
- Treat this as project-specific guidance and constraints.
- When writing or rewriting `specs/changes/<change-id>/aip.md`, also load `/Users/keqing/.codex/skills/writing-style/SKILL.md` and apply its reference only to the AIP narrative text. Do not apply `writing-style` to review reports, planning artifacts, YAML sidecars, Atomic Issues, code comments, or final answers.
- When generating `specs/changes/<change-id>/aip.md`, preserve the standard headings from `references/steering.md` exactly enough for validators to recognize them:
  `AIP 元信息`, `评审记录`, `AIP 正文结构`, `1. 背景`, `2. 问题定义`, `3. 调研论证`, `4. 解决方案`, `5. 原型设计`, `6. 接口设计`, `7. 依赖选型`, `8. 方案详情`, `9. 兼容性问题`, `10. 被拒绝的其他方案`, `11. 落地计划`, `AIP 验收`, `发布验收`, `上线验收`.
- Do not replace the standard template with an engineering-completeness outline. Extra engineering matrices such as architecture decisions, API/data/state, deployment/IAM, observability, compatibility, and verification must be inserted under the matching standard sections.
- AIP is a human-readable engineering design document, not only a checklist. It must materialize the locked design objects from AIP readiness: ADEC/DEC, external MECH/FACT/CONSTRAINT, current architecture evidence, interface/data/state/runtime decisions, compatibility, rejected alternatives, and verification strategy.

## Section Completeness Standard

Use the standard headings, but write each section to the following depth:

- `1. 背景`: explain user/customer context, current system behavior, why this is needed now, and the evidence that proves the current behavior. It should let a reviewer understand the motivation without reading sidecars.
- `2. 问题定义`: define goals, non-goals, affected concepts, boundaries, supported modes, unsupported modes, and user-visible success/failure states.
- `3. 调研论证`: summarize current architecture facts and external mechanism facts. For cloud/K8s/ASG/HPA/metrics/runtime/IAM/logs/storage dependencies, consume `MECH-*`, `FACT-*`, and `CONSTRAINT-*` rather than saying only “参考官方文档”.
- `4. 解决方案`: present the deductive design chain: selected mechanism, why it satisfies the product semantics, rejected alternatives, interface/state/runtime effects, and how failures are expressed.
- `5. 原型设计`: for UI work, describe user flow, fields, actions, loading/empty/error/warning states, and mode-specific display rules. If no UI is involved, state locked N/A and why.
- `6. 接口设计`: define canonical request/response/readback shape, DTO/VO/OpenAPI/Terraform/CLI/internal API impact, compatibility with old fields, and invalid/missing field behavior.
- `7. 依赖选型`: name selected external/internal mechanisms, rejected mechanisms, version or environment constraints, permissions, and unsupported semantics.
- `8. 方案详情`: describe data ownership, state machine, runtime materialization, external side effects, progress/events, resource ownership, observability, failure recovery, and verification hooks.
- `9. 兼容性问题`: cover new install, existing data, upgrade, rollback, old API/field/config, old UI consumer, and mode leakage prevention.
- `10. 被拒绝的其他方案`: include meaningful alternatives with tradeoffs and concrete rejection reasons, not a generic “复杂度高”.
- `11. 落地计划`: outline phases and readiness gates at engineering-plan level. Do not turn this section into Atomic Issues; task-planning owns Txxx decomposition.

## Required AIP Design Tables

Place these tables under the matching standard sections, usually `4. 解决方案` or `8. 方案详情`:

```markdown
### Mechanism-Level Design Closure Matrix

| Design question | Selected mechanism | Rejected alternatives | Current code evidence | External fact / constraint | Interface impact | State/runtime impact | Failure behavior | Verification | Downstream C/VER |
|---|---|---|---|---|---|---|---|---|---|

### AIP Narrative Materialization Gate

| Source design object | Must appear in AIP section | Narrative requirement | Status |
|---|---|---|---|
```

Rules:

- Each design question must be an operation/surface-level question, not a broad capability label.
- The selected mechanism must be concrete enough that archaeology/contract/task-planning do not need to invent provider API, runtime shape, state owner, field semantics, or failure behavior.
- Every AIP-owned locked ADEC/DEC and every AIP-time design-affecting MECH/FACT/CONSTRAINT must appear in the AIP narrative or the materialization gate with `materialized`, `locked N/A`, or `blocked`.
- Do not retroactively require readiness/design/archaeology/migration/frontend/verification/task-planning decisions to appear in AIP. Backflow only when downstream evidence proves an AIP-owned decision or mechanism was missing or wrong.
- `blocked` means the AIP is not ready for downstream stages.
