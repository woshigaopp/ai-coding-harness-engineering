# Version / Branch Alignment

> 多仓、多版本、Terraform/IAC/测试编排/control-plane/kernel 变更前的版本一致性门禁。

## Version Branch Alignment Matrix

| Component | Repo | Branch/version | Required by | Evidence | Aligned? | Risk / action |
|---|---|---|---|---|---:|---|
| control-plane | control-plane repo |  |  |  | yes/no/N/A |  |
| data-plane | data-plane repo |  |  |  | yes/no/N/A |  |
| Terraform | IAC repo / playground |  | TERRAFORM_BRANCH |  | yes/no/N/A |  |
| IAC templates | IAC repo |  | IAC_BRANCH / template |  | yes/no/N/A |  |
| test orchestration | test-orchestration repo |  | suite/task/config |  | yes/no/N/A |  |

Exit gate:

- [ ] Every referenced branch/version/template exists or is explicitly N/A.
- [ ] Cross-repo branch mismatch is routed to owning repo before implementation.
- [ ] Atomic Issues mention exact branch/version assumptions when relevant.
