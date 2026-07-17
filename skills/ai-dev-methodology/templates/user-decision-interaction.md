# User Decision Interaction

> 未授权的 PRD/AIP 决策默认由用户逐条确认。用户明确要求集中查看时，可通过 `decision-bundles/HDB-xxx.yaml` 一次确认多项；bundle 必须固定完整 prompt、逐项语义和明确 all-listed 响应。本表记录交互、授权和锁定结果，不能替代 `decision-reviews/<stage>-decisions.md`。

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
- [ ] Each Human Decision Prompt asks for one decision, unless a valid HDB receipt seals the full multi-decision prompt and explicit all-listed response. Unreceipted "all agreed" responses never close multiple decisions.
