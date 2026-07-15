# Decision Registry

## Decision Document Index

| Stage | Decision document | Lark URL | Status | Notes |
|---|---|---|---|---|
| PRD | `decision-reviews/prd-decisions.md` |  | open/locked/synced/not-created |  |
| AIP | `decision-reviews/aip-decisions.md` |  | open/locked/synced/not-created |  |
| New Feature Design | `decision-reviews/design-decisions.md` |  | open/locked/synced/not-created |  |
| Code Archaeology | `decision-reviews/archaeology-decisions.md` |  | open/locked/synced/not-created |  |
| Migration Diff | `decision-reviews/migration-decisions.md` |  | open/locked/synced/not-created |  |
| Frontend Contract | `decision-reviews/frontend-decisions.md` |  | open/locked/synced/not-created |  |
| Cross-Module Contract | `decision-reviews/contract-decisions.md` |  | open/locked/synced/not-created |  |
| Verification Matrix | `decision-reviews/verification-decisions.md` |  | open/locked/synced/not-created |  |

Rules:

- Every stage that introduces decisions must produce or update its stage decision document.
- PRD-stage product decisions must be confirmed by the user or explicitly delegated to AI before being locked.
- Later engineering decisions may be made by AI when they do not change product semantics, but they still must be recorded with alternatives, reason, impact, and verification.
- If Lark write permission is available, sync each stage decision document to Feishu/Lark and record the URL here.
- Implementation consumes locked decisions only; it must not make new product or engineering decisions.

| ID | Type | Decision key | Decision | Alternatives | Source | Affected modules | Supersedes | Superseded by | Status | Verification |
|---|---|---|---|---|---|---|---|---|---|---|
| DEC-xxx | product/architecture/interface/migration/contract/pattern/validation | stable semantic key |  |  | requirement/AIP/user/archaeology |  | DEC-yyy/N/A | DEC-zzz/N/A | locked/open/superseded |  |

Rules:

- `open` blocks implementation.
- Do not silently modify a locked decision. Mark it `superseded` and add a new row.
- `Decision key` is the stable question/semantic area, used for contradiction detection.
- Two active `locked` decisions with the same `Decision key` are forbidden unless one explicitly narrows the other without conflict.
- Every decision must have alternatives unless it is a direct user/product constraint.
- Every decision must have verification or explain why it is not directly verifiable.

## Decision Consistency Matrix

| Decision key | Active decision | Potentially conflicting decisions | Conflict? | Resolution | Status |
|---|---|---|---:|---|---|
|  | DEC-xxx | DEC-yyy | yes/no | supersede / split key / clarify scope / no conflict because... | locked/open |
