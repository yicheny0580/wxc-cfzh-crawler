# Local Docker Scheduler Ops

## Goal

Make local Docker manual refresh and scheduler management exercise the same
container/process-namespace behavior as production operations.

## Context

- A local `docker-local-refresh pages=1` completed successfully.
- During that foreground refresh, `docker-local-status` reported the active PID
  as stale because it ran in a separate one-off admin container.
- Production SSH operations use `docker compose exec -T scheduler ...`, so PID
  liveness, stop, and busy-lock checks run inside the scheduler container.
- Local recipes need to use the running `scheduler` container when present, or
  the running `web` container for web-only local verification.

## Plan

- Add a small host-side helper for local Docker admin commands.
- Route local status, refresh, report, stop, pause/resume, and scheduler status
  through a running local service instead of a separate admin container when
  possible.
- Let local scheduler startup accept `interval=` and `pages=` for faster
  verification while preserving the 120-second/pages=2 defaults.
- Update docs and validate manual refresh plus scheduler behavior.

## Validation

- `just --fmt --check`
- `uv run pytest tests/test_docs_structure.py`
- `just docker-local-status`
- `just docker-local-refresh pages=1`
- `just docker-local-up-scheduler port=8766 pages=1 interval=120`
- `just docker-local-scheduler-status`
- `just docker-local-scheduler-pause`
- `just docker-local-scheduler-resume`
- `just docker-local-admin-logs tail=80`

## Progress

- Added `scripts/docker_local_admin.sh` to execute local admin commands inside
  `scheduler` when running, then `web`, then a one-off admin container as a
  fallback.
- Updated local recipes for status, refresh, report, stop, scheduler
  pause/resume/status, and admin log access.
- Added local scheduler `interval=` and `pages=` startup options while keeping
  defaults at 120 seconds and 2 pages.
- Added production `ops-admin-logs` for remote access to `wxc-cfzh-admin logs`.
- Manual local refresh succeeded before the fix, but status from a separate
  admin container incorrectly reported the active lock as stale; this drove the
  local recipe change.
- After the fix, local scheduler startup succeeded with
  `just docker-local-up-scheduler port=8766 pages=1 interval=120`.
- Scheduled and manual refreshes both succeeded while the scheduler service was
  present, and final status reported `lock=null` and `lock_stale=false`.
- Scheduler pause/resume and admin log recipes were verified.
- The scheduler container was stopped after validation to avoid continued local
  background crawls.
- Final validation passed with `just check`.

Use this template for substantial work that may need to resume without external
context. Exec-plans are checked-in execution records for qualifying work, not
the long-term home for durable design choices. Delete sections that do not
apply, but keep the plan specific enough to execute without external context.
For qualifying work, create the active plan after implementation approval and
before changing stable docs, code, or tests.

## Goal

Describe the user-visible or repository-visible outcome.

## Context

Link the stable docs, source files, and tests that define the current behavior.
Record known unrelated dirty files from `git status --short`, or state `none`.
State whether this active plan was created as the first tracked implementation
artifact.

## Plan

- Record the implementation steps in execution order.
- Keep durable rules out of this section; follow
  [../design-docs/agent-workflow.md](../design-docs/agent-workflow.md) for
  stable-doc promotion.

## Decisions

- Record execution decisions that explain why the active plan chose one path
  over another. Promote durable design choices into stable docs before
  completing the plan.

## Validation

- List the targeted checks and acceptance scenarios.

## Progress

- Keep this section current while the plan is active.
- Record active-plan creation as the first tracked implementation artifact,
  major implementation milestones, validation results, stable-doc promotion, and
  completion.
