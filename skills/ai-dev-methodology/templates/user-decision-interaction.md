# User Decision Interaction

> 未授权的 PRD/AIP 决策必须由用户逐条确认。进入 `human-decision-participation` 模式后，所有阶段产生或修改的阶段决策都必须逐条确认。本表记录交互、授权和锁定结果，不能替代 `decision-reviews/<stage>-decisions.md`。

## Decision Authority

| Scope | Authority | Evidence | Limits |
|---|---|---|---|
| product decisions | user-confirmed / ai-authorized / not-authorized | user message / doc / meeting note | PRD PDEC default user-confirmed unless explicitly ai-authorized |
| architecture decisions | user-confirmed / ai-authorized / not-authorized | user message / doc / meeting note | AIP/AIP readiness ADEC default user-confirmed unless explicitly ai-authorized |
| all-stage decisions | human-decision-participation / ai-authorized-by-scope / not-enabled | user message / doc / meeting note | when enabled, every stage decision needs one-by-one prompt before lock |

## Decision Interaction Ledger

| Stage | Decision ID | Decision key | Question | Prompt ID | Prompt summary | Recommended option | Alternatives | Why recommended | User impact | Affected artifacts | Verification | User response | Final status | Decided at |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| prd | PDEC-001 |  |  | HDP-001 |  |  |  |  |  |  |  | confirmed / needs-change / no-response / ai-authorized-by-scope | locked/open/superseded | YYYY-MM-DDTHH:MM:SSZ |

Exit gate:

- [ ] No product decision is locked by AI unless `Authority=ai-authorized`.
- [ ] No AIP/AIP readiness engineering decision is locked by AI unless `Authority=ai-authorized`.
- [ ] When `human-decision-participation` is enabled, every stage decision has exactly one ledger row with prompt ID, prompt summary, user response, final status, affected artifacts, verification, and decided-at timestamp.
- [ ] User responses are written back to the matching decision details in `decision-reviews/<stage>-decisions.md`.
- [ ] Ambiguous or no-response decisions remain `open` and block PRD completion.
- [ ] Each Human Decision Prompt asks for one decision only. Do not batch multiple decisions or close several decisions with one "all agreed" response.
