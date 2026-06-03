# Context Pack

Context packs are built by rereading canonical artifacts before a downstream
phase. They are not summaries of chat history.

## Source Rehydration Ledger

| Artifact | Path | Read Time | Status | Used By Downstream? |
|---|---|---|---|---|
| proposal |  |  | read / blocked | yes / no |

## Semantic Index

| Object ID | Type | Required Semantics | Downstream Consumer |
|---|---|---|---|
| REQ-001 | requirement |  | T001 |

## Decision and Constraint Pack

| Decision / Constraint | Locked Meaning | Forbidden Reinterpretation | Downstream Owner |
|---|---|---|---|
| DEC-001 |  |  | T001 |

## Boundary-Specific Pack

| Topic | Required Facts |
|---|---|
| modules |  |
| contracts |  |
| frontend actions |  |
| runtime lifecycle |  |
| mock behavior |  |
| verification |  |

## Downstream Coverage Map

| Upstream Object | Downstream Artifact | Section / Task | Status |
|---|---|---|---|
| REQ-001 | atomic issue | T001 | covered / blocked |

