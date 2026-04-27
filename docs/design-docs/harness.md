# Harness Design

The root `justfile` is the public command harness. It wraps lower-level Python,
Scrapy, npm, and FastAPI commands so common workflows stay discoverable through
one interface.

## Required Tools

- `just`: root command runner.
- `uv`: Python workspace and package runner.
- `npm`: inspector frontend dependency and build runner.

Run the environment checks from the repository root:

```bash
just doctor
```

## Setup

Use the root setup recipe after cloning and whenever frontend dependency
manifests change:

```bash
just setup
```

`just setup` installs Python workspace dependencies with `uv sync` and frontend
dependencies with `npm --prefix inspector/frontend ci`.

## Command Surface

- Start command discovery with `just list`.
- Use named `key=value` recipe options for user-facing workflows.
- Keep low-level framework commands available for troubleshooting, but advertise
  root recipes for normal use.
- Before adding or changing user-facing commands, update
  [../operations.md](../operations.md) and this harness doc with the intended
  command behavior. Then implement the `justfile` change and revise docs if the
  final command shape changes.

## Exec-Plan Helpers

Agents use the root harness for checked-in execution-record lifecycle steps.
For qualifying work, create the active exec-plan as the first tracked
implementation artifact after approval, before stable docs, code, or tests:

```bash
just exec-plan-new slug=short-name title='Human Title'
just exec-plan-complete slug=short-name
```

The helper creates active plans from `docs/exec-plans/template.md`, validates
slug shape, and refuses to overwrite existing active or completed plans.
The lifecycle source of truth is [agent-workflow.md](agent-workflow.md).
Exec-plans preserve execution and resume state; durable design choices and
operating rules belong in stable docs.

## Validation

Use the smallest check that covers the change while developing:

```bash
just test-root
just test-crawler
just test-backend
just ui-build
```

Use the full harness before handing off broad or cross-domain work:

```bash
just check
```

The full harness checks justfile formatting, Python lint, production file length,
Python tests, and the frontend build.

## Long-Running Workflows

- `just crawl` writes to the crawler SQLite database and should default to root
  `data/`.
- `just inspect` rebuilds the frontend, then serves the FastAPI backend and
  static UI.
- `just inspect-api` skips the frontend build for backend-only troubleshooting.
- The inspector refresh control starts a crawler subprocess; it is the only
  inspector workflow allowed to write crawler data in local-development mode.
- Production SSH operations use `just ops-*` recipes. These recipes load
  `.env.deploy` by default and call Docker Compose plus the in-container
  `wxc-cfzh-admin` CLI on the VPS.
