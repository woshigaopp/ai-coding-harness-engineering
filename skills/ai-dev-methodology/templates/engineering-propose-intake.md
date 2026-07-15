# Engineering Propose Intake

> AIP、工程设计、接口草案、Terraform/API 设计都先当 Engineering Propose，不直接当 locked engineering design。

## Engineering Propose Extraction

| Source ID | Engineering propose | Explicit engineering fact | Inferred engineering fact | Unknown / decision needed | Affected interface/module |
|---|---|---|---|---|---|

## Current Architecture Understanding

| Area | Current architecture / behavior | Evidence path / command | Engineering implication | Gap / DEC |
|---|---|---|---|---|

## Engineering Decision Completeness Gate

| Dimension | Complete? | Evidence section | Open DEC | Blocks next stage |
|---|---:|---|---|---:|
| Architecture option | yes/no |  | DEC-xxx/N/A | yes/no |
| Alternatives rejected | yes/no |  | DEC-xxx/N/A | yes/no |
| Interfaces | yes/no |  | DEC-xxx/N/A | yes/no |
| Data/state/task/event | yes/no |  | DEC-xxx/N/A | yes/no |
| Deployment/IAM/cloud | yes/no/N/A |  | DEC-xxx/N/A | yes/no |
| Compatibility/rollback | yes/no |  | DEC-xxx/N/A | yes/no |
| Observability | yes/no/N/A |  | DEC-xxx/N/A | yes/no |
| Verification strategy | yes/no |  | DEC-xxx/N/A | yes/no |

Exit gate:

- [ ] External engineering docs are normalized into locked DEC/ADEC; they are not accepted as final design by title.
- [ ] Current Architecture Understanding has evidence paths.
- [ ] No `Complete?=no` row with `Blocks next stage=yes`.
- [ ] Any decision changing product semantics is returned to PRD.
