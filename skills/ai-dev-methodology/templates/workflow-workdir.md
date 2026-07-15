# Workflow Workdir Identity

This file is the first artifact of an AutoMQ AI workflow. Create it immediately after the workflow skill starts and before writing `purpose.md`, `source-intake-ledger.md`, `proposal.md`, or any other canonical artifact.

## Canonical Workdir

| Item | Value |
|---|---|
| Target repo |  |
| Worktree path |  |
| Change dir absolute path |  |
| Change id |  |
| Branch name |  |
| Base branch |  |
| Base commit |  |
| Git top level |  |
| Created at |  |
| Created by command evidence |  |

## Resume Verification

Every context compaction, resume, or uncertain cwd must start by reading this file and verifying the current location against the canonical paths below. If any value is missing or mismatched, stop and ask the user or switch back to the recorded worktree; do not create a new branch, worktree, change-id, `purpose.md`, or downstream artifact.

| Check | Expected | Actual | Status | Evidence |
|---|---|---|---|---|
| Current worktree path equals Worktree path |  |  | pending |  |
| Current change dir equals Change dir absolute path |  |  | pending |  |
| Current branch equals Branch name |  |  | pending |  |
| Current HEAD descends from or equals Base commit |  |  | pending |  |
| `specs/changes/<change-id>` exists in Worktree path |  |  | pending |  |

## Hard Rules

- `workflow-workdir.md` is the workdir identity anchor. It must be committed to the workflow artifact set and sealed by every stage receipt.
- The recorded `Worktree path`, `Change dir absolute path`, and `Change id` must not be inferred from the current cwd after resume. The file is the source of truth.
- If the current cwd has no `specs/` directory, that is a resume mismatch, not permission to start over.
- A new worktree/change-id is allowed only when the user explicitly says to restart or abandon the old execution.
