# Verification Feasibility Gate

> 在 Atomic Task Planning 前确认验证是否真的能执行，避免实现后才发现环境、数据、账号或云资源不可用。

## Verification Feasibility Matrix

| Verification | Source | Required? | Environment / fixture needed | Available? | Setup owner/command | Fallback | Blocks done | Risk |
|---|---|---:|---|---:|---|---|---:|---|
| VER-001 | REQ/C/MIG | yes/no | local / CI / EC2 / cloud account / browser / fixture | yes/no |  | Not Run / manual / alternative proof | yes/no |  |

Exit gate:

- [ ] Every required verification has environment/fixture availability confirmed.
- [ ] `Available?=no` and `Blocks done=yes` prevents done and must enter Not Run risk.
- [ ] Fallback proof is itself mapped to source and expected result.
- [ ] Verification setup commands/owners are copied into tasks/Atomic Issues.
