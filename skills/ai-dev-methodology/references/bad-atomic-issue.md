# Bad Atomic Issue Example

```markdown
- [ ] T012 [REQ-005,C-002] Add ConnectorTemplateController and service APIs.
  Context:
  - Use @ActionPermission.
  - Add list/detail/upload/state/match/preview.
  - Verification: controller/service tests.
```

Why this is not an Atomic Issue:

| Problem | Why it fails |
|---|---|
| Source IDs only | It references REQ/C but does not copy required behavior. |
| No exact API route | A worker can accidentally implement `/templates/:match`. |
| No handler/path semantics | Does not mention Spring base path + method path risk. |
| Verification vague | “controller/service tests” has no command, expected result, or proves. |
| Too broad | Controller, permissions, service APIs, and all actions are mixed. |
| No prohibited changes | Worker may adjust service semantics or frontend path opportunistically. |
| Not independently executable | Requires reading full `spec.md` and `plan.md` to know what to do. |

Corrective action:

- Split broad task into separate Atomic Issues.
- Copy required source/decision/contract excerpts into each issue.
- Add exact files, implementation steps, and verification expected result.
- Write persistent issue artifacts in Chinese by default; keep only code/API identifiers in original form.
- Add Behavior Details and Failure meaning / Not Run risk.
