# Cloud Deployment

## Goal

Add a small, cost-conscious cloud deployment path for a personal public
read-only inspector, with Docker, manual GitHub Actions deployment, SSH/CLI
operations, scheduled crawling, race-safe crawl control, logs, and diagnostics.

## Context

- Stable docs: [../../operations.md](../../operations.md),
  [../../architecture.md](../../architecture.md),
  [../../product-specs/crawler-inspector-workflows.md](../../product-specs/crawler-inspector-workflows.md),
  [../../../inspector/docs/index.md](../../../inspector/docs/index.md),
  and [../../../crawler/docs/index.md](../../../crawler/docs/index.md).
- Current code: `inspector/backend/app/main.py` exposes unauthenticated crawl
  control endpoints; `inspector/frontend/src/CrawlControls.tsx` starts/stops
  crawls; crawler persistence currently serves search through `LIKE` filters.
- No existing `Dockerfile`, `docker-compose.yml`, `.github/` workflows, or
  cloud deployment docs.
- Known unrelated dirty files: none at plan creation.
- This active plan was created as the first tracked implementation artifact
  after approval.

## Plan

- Promote the cloud deployment model into stable docs before code changes.
- Add public-mode backend and frontend behavior so deployed browser access can
  only read SQLite data and refresh local API state.
- Add a crawler admin CLI for manual refresh, stop, scheduler run/pause/resume,
  status, logs, and diagnostics.
- Add lock/status files under the shared data runtime directory so manual and
  scheduled crawls cannot overlap and stop/status handle stale state.
- Add SQLite FTS5 search tables maintained by crawler writes and used by
  inspector search endpoints.
- Add Docker, compose, env examples, GitHub Actions CI/manual deploy workflows,
  and root `just` operations recipes.
- Run focused tests while developing and `just check` before handoff if
  available.

## Decisions

- Deploy workflow is manual-only with `workflow_dispatch`; CI remains automatic.
- Admin refresh after deployment is SSH/CLI only, not a browser admin route.
- Scheduler defaults to `pages=2` every 120 seconds.
- Real deploy target config lives in untracked `.env.deploy`; tracked
  `.env.deploy.example` documents required variables.
- Public repository and public GHCR package are assumed for GitHub free-tier
  Actions usage.

## Validation

- Backend tests for public-mode route blocking and hidden DB paths.
- CLI/scheduler tests for lock contention, stop semantics, pause/resume, status,
  and diagnostics.
- Crawler tests for FTS backfill/upsert maintenance.
- Frontend build for public refresh behavior.
- Docker build/compose config checks if local environment permits.
- Final `just check`.

## Progress

- Created active plan as the first tracked implementation artifact.
- Promoted durable deployment, public-mode, scheduler, SSH operations, and cost
  guardrail behavior into stable docs.
- Implemented public read-only inspector mode, SSH/admin CLI, scheduler
  pause/resume/status, crawl lock/status files, log/report commands, and FTS5
  search indexing.
- Added Dockerfile, Compose/Caddy deployment files, `.env.deploy.example`,
  automatic CI workflow, manual deploy workflow, and `just ops-*` recipes.
- Validation passed: `just check`.
- Docker validation could not run in this local environment because Docker is
  not installed in the WSL distro.
