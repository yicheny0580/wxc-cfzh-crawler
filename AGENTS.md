# Agent Map

This file is a table of contents, not the repository manual. Start here, then open the linked source of truth that matches the task.

## First Reads

- [README.md](README.md): current human-facing quick start and command surface.
- [justfile](justfile): canonical root command harness for humans and Codex.
- [docs/index.md](docs/index.md): root documentation map.
- [docs/architecture.md](docs/architecture.md): workspace layout and package boundaries.
- [docs/operations.md](docs/operations.md): commands for crawl, export, inspect, and local checks.
- [docs/quality.md](docs/quality.md): verification expectations and structural docs checks.

## Domain Docs

- [crawler/docs/index.md](crawler/docs/index.md): crawler behavior, Scrapy settings, root recipe parameters, SQLite output, and tests.
- [inspector/docs/index.md](inspector/docs/index.md): inspector backend/frontend startup, API behavior, and UI build notes.
- [docs/exec-plans/index.md](docs/exec-plans/index.md): durable plans for larger changes.

## Repo Rules

- Keep domain code in `crawler/` or `inspector/`; keep local runtime outputs in ignored `data/`.
- Prefer `just ...` for root workflows. Start with `just list`; use targeted recipes such as `just test-crawler`, `just ui-build`, and `just check` before dropping to raw low-level commands.
- Update the relevant docs index when adding a new subsystem, command, or operational assumption.
