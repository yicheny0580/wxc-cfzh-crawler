# Local Docker Verification

## Goal

Add a local Docker Compose verification path and switch Docker SQLite
persistence from a named volume to a bind-mounted host data directory.

## Context

- Current production Compose mounts `/data` from the `wxc-data` Docker named
  volume.
- Deployment docs describe `/data/crawler.sqlite3` inside containers but do not
  explain host-visible storage or local Compose verification.
- Known unrelated dirty files at plan creation: `AGENTS.md`,
  `docs/design-docs/agent-workflow.md`, `docs/design-docs/harness.md`,
  `docs/exec-plans/index.md`, `docs/operations.md`, `justfile`,
  `scripts/manage_exec_plan.py`, `tests/test_manage_exec_plan.py`, and
  `docs/exec-plans/active/20260427-exec-plan-timestamp-names.md`.
- This active plan was created as the first tracked implementation artifact for
  the local Docker verification change after approval.

## Plan

- Update stable deployment docs to make bind-mounted SQLite directories the
  default Docker storage model.
- Change production Compose so `/data` comes from `${WXC_DATA_DIR:-./data}`.
- Add `docker-compose.local.yml` for local build/run/admin/scheduler
  verification with `./data/docker-local:/data`.
- Add root `just docker-local-*` recipes without disturbing existing remote
  ops recipes.
- Validate docs, justfile formatting, and Compose syntax where available.

## Decisions

- Use a directory bind mount instead of a named volume because SQLite WAL/SHM
  sidecar files, runtime locks, logs, backups, and manual inspection all work
  cleanly when the data directory is host-visible.
- Do not mount only `crawler.sqlite3`; SQLite sidecar files must live beside the
  database.
- Local scheduler is opt-in through an explicit recipe/profile.

## Validation

- `just --fmt --check`
- `uv run pytest tests/test_docs_structure.py`
- `docker compose -f docker-compose.local.yml config` if Docker Compose is
  available.
- `docker compose config` if Docker Compose is available.
- `just list`
- `just docker-local-build` after Docker is available.
- `just docker-local-up port=8766` when the default `8765` host port is busy.
- `just docker-local-status`, `just docker-local-report`, and
  `just docker-local-logs service=web tail=20`.

## Progress

- Created active plan as the first tracked implementation artifact for this
  change.
- Documented bind-mounted SQLite storage and local Docker verification in
  stable deployment/operations docs.
- Added `docker-compose.local.yml`, switched production `/data` to a bind
  mount, updated manual deploy setup to create the host data directory, and
  added root `docker-local-*` recipes.
- Validation passed: `just --fmt --check`, `uv run pytest
  tests/test_docs_structure.py`, and `just check`.
- After Docker was started, Compose config validation passed for both
  `docker-compose.local.yml` and `docker-compose.yml`.
- `just docker-local-build` completed successfully.
- `just docker-local-up` found the default `8765` host port already occupied by
  a local `uvicorn`; local Docker startup now accepts `port=`, and
  `just docker-local-up port=8766` started the web service.
- `curl http://127.0.0.1:8766/api/health` returned the expected public read-only
  health response with `db_exists=false` before any local crawl.
- Local Docker admin diagnostics passed through `just docker-local-status`,
  `just docker-local-report`, and `just docker-local-logs service=web tail=20`.
