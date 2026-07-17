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
| Base source mode | fetched-remote / pinned-commit / local-only |
| Remote ref |  |
| Remote OID |  |
| Remote fetched at |  |
| Fetch command evidence |  |
| Git top level |  |
| Created at |  |
| Created by command evidence |  |

## Resume Verification

Run `workflowctl.py verify-resume <change-dir>` after a context compaction, new session, or uncertain cwd. The command verifies identity and appends a hash-chained workflow event without modifying this receipt-bearing file. If any value is missing or mismatched, stop or switch back to the recorded worktree; do not create a new branch, worktree, change-id, `purpose.md`, or downstream artifact.

| Check | Expected | Actual | Status | Evidence |
|---|---|---|---|---|
| Current worktree path equals Worktree path |  |  | pending |  |
| Current change dir equals Change dir absolute path |  |  | pending |  |
| Current branch equals Branch name |  |  | pending |  |
| Current HEAD descends from or equals Base commit |  |  | pending |  |
| `specs/changes/<change-id>` exists in Worktree path |  |  | pending |  |

## Hard Rules

- `workflow-workdir.md` is the immutable workdir identity anchor. It must be committed to the workflow artifact set and sealed by every stage receipt; resume checks belong in `workflow-events.yaml`.
- A base branch under `origin/*` must use `fetched-remote` and record a matching remote OID, fetch time, and `git fetch` command before source/current-code construction starts.
- The recorded `Worktree path`, `Change dir absolute path`, and `Change id` must not be inferred from the current cwd after resume. The file is the source of truth.
- If the current cwd has no `specs/` directory, that is a resume mismatch, not permission to start over.
- A new worktree/change-id is allowed only when the user explicitly says to restart or abandon the old execution.
