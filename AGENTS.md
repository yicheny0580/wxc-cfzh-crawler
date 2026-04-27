# Agent Map

This file is a thin table-of-contents map, not the repository manual. Start
here, then open the linked source of truth that matches the task.

## First Reads

- [README.md](README.md): current human-facing quick start and command surface.
- [justfile](justfile): canonical root command harness.
- [docs/index.md](docs/index.md): root documentation map.
- [docs/design-docs/agent-workflow.md](docs/design-docs/agent-workflow.md): agent planning, exec-plan lifecycle, validation, review, and commit workflow.
- [docs/design-docs/project-invariants.md](docs/design-docs/project-invariants.md): doc-first workflow and durable project invariants.
- [docs/design-docs/harness.md](docs/design-docs/harness.md): setup, command harness, and validation flow.
- [docs/design-docs/code-unit-design.md](docs/design-docs/code-unit-design.md): code unit boundaries and interface expectations.
- [docs/product-specs/index.md](docs/product-specs/index.md): product intent and supported workflows.
- [docs/references/index.md](docs/references/index.md): external references and target-site examples.
- [docs/architecture.md](docs/architecture.md): workspace layout and package boundaries.
- [docs/operations.md](docs/operations.md): commands for crawl, export, inspect, and local checks.
- [docs/deployment.md](docs/deployment.md): Docker, manual deploy, VPS operations, and cost guardrails.
- [docs/quality.md](docs/quality.md): verification expectations and structural docs checks.

## Domain Docs

- [crawler/docs/index.md](crawler/docs/index.md): crawler behavior, Scrapy settings, root recipe parameters, SQLite output, and tests.
- [inspector/docs/index.md](inspector/docs/index.md): inspector backend/frontend startup, API behavior, and UI build notes.
- [docs/exec-plans/index.md](docs/exec-plans/index.md): checked-in execution records for larger changes.

## Repo Rules

- Follow [docs/design-docs/agent-workflow.md](docs/design-docs/agent-workflow.md) for draft plans, approval, implementation, validation, and commits.
- For substantial, corrective, handoff-prone, or workflow-policy work, create or
  update the active exec-plan with
  `just exec-plan-new slug=short-name title='...'` as the first tracked
  implementation artifact after approval, before stable docs, code, or tests.
  The helper prefixes new plan filenames with the UTC date.
- Keep maps and indexes thin. Put durable ideas, design choices, and operating
  rules in the relevant stable doc, not in `AGENTS.md` or an exec-plan.
- Keep domain code in `crawler/` or `inspector/`; keep local runtime outputs in ignored `data/`.
- Prefer `just ...` for root workflows. Start with `just list`; use targeted recipes such as `just test-crawler`, `just ui-build`, and `just check` before dropping to raw low-level commands.
- Update the relevant docs index when adding a new subsystem, command, or operational assumption.
