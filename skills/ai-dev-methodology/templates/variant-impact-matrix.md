# Variant Impact Matrix

Use this after code archaeology discovers that a requirement changes an existing
object/action by adding or altering an implementation variant. Do not depend on
the word "mode"; variants can be called deployment type, runtime backend,
provider, runner, execution environment, placement, adapter, or any equivalent
structure in code.

## Variant Detection Matrix

| Variant row | Requirement/source | New variant candidate | Object/entity | Existing action / mutation | Existing variant(s) | Shared entry/API/page | Shared state/readback | Detection evidence | Variant decision |
|---|---|---|---|---|---|---|---|---|---|
| VIM-001 | REQ-xxx | asg | ConnectCluster | create | k8s | `POST /connect/clusters` | detail/progress/change | same object and create API, different runtime provider | supported / locked N/A |

## Old Consumer Parity Matrix

| Parity row | New variant | Object/action | Existing consumer surface | Old variant assumption | Must new variant satisfy? | New producer/behavior | If not supported decision | Contract candidate | Verification |
|---|---|---|---|---|---|---|---|---|---|
| VPAR-001 | asg | ConnectCluster/create | progress/change | K8s create writes change/task steps readable from `/last-change` | yes | create equivalent change producer | N/A only with locked DEC | C-xxx | VER-xxx |

## Variant Gap Backflow Matrix

| Gap row | Variant row / parity row | Gap | Backflow target | Blocks contract? | Blocks task planning? | Resolution |
|---|---|---|---|---:|---:|---|
| VGAP-001 | VPAR-xxx | missing producer chain | cross-module-contract | yes | yes | locked producer contract |
