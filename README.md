# AI Coding Harness Engineering

This repository contains the executable AutoMQ context-pack workflow for large
AI coding changes. It is the version-controlled source bundle for
`automq-ai-dev-workflow-contextpack`, not only a methodology document.

The workflow turns product requirements and AIP input into gate-locked
artifacts, explicit module contracts, self-contained Atomic Issues, verified
execution, mock/product acceptance, and launch convergence.

## Repository Layout

```text
skills/
  automq-ai-dev-workflow-contextpack/  # workflow entry and orchestration rules
  automq-ai-dev-workflow/              # standard workflow drift baseline
  ai-dev-methodology/                  # runtime, validators, templates, references
  product-requirement-design/          # stage owner skills
  ...                                  # remaining pinned owners and dependencies
```

The complete bundle contains the entry skill, the runtime methodology, all
runtime-manifest-pinned stage owner skills, the standard workflow validation
baseline, and the writing/decision interaction dependencies required by those
owners.

## Install

Install all sibling skill directories into the Codex skill home:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
rsync -a skills/ "${CODEX_HOME:-$HOME/.codex}/skills/"
```

The entry point is:

```text
${CODEX_HOME:-$HOME/.codex}/skills/automq-ai-dev-workflow-contextpack/SKILL.md
```

This snapshot preserves the exact tested AutoMQ engineering configuration and
runtime component hashes. Do not edit a copied runtime component independently;
publish a new runtime manifest and migrate active workflows explicitly.

## Validate

```bash
python3 skills/ai-dev-methodology/scripts/validate_skill_suite.py
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/ai-dev-methodology
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/automq-ai-dev-workflow-contextpack
```

The current runtime is `contextpack-runtime-2026.07.14.4`.

## License

MIT. See [LICENSE](LICENSE).
