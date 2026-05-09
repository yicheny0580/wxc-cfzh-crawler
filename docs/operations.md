# Operations

## Setup

```bash
uv tool install rust-just
just setup
```

Use any supported `just` installation method from the
[Just Programmer's Manual](https://just.systems/man/en/packages.html). Run
`just setup` after cloning or when frontend dependency manifests change.

Useful discovery and environment checks:

```bash
just list
just doctor
```

The command harness source of truth is [design-docs/harness.md](design-docs/harness.md).
Update that doc when setup, command discovery, or validation behavior changes.

## Exec Plans

For qualifying agent work, create the active exec-plan as the first tracked
implementation artifact after approval, before stable docs, code, or tests.
Create and complete checked-in execution records through the root harness:

```bash
just exec-plan-new slug=short-name title='Human Title'
just exec-plan-complete slug=YYYYMMDD-short-name
```

Use [exec-plans/index.md](exec-plans/index.md) and
[design-docs/agent-workflow.md](design-docs/agent-workflow.md) for the lifecycle
rules. `exec-plan-new` adds the current UTC date to the filename; complete plans
with the full timestamped slug. Durable ideas, design choices, and operating
assumptions belong in the relevant stable docs before the exec-plan is
completed.

## Crawl

```bash
just crawl
just crawl-smoke
```

Useful options:

- `pages`: recent forum listing pages to scan for frontier discovery.
- `max_requests`: optional detail-page request cap for smoke runs.
- `database_url`: SQLite database URL override.
- `log_level`: Scrapy log level override.

Interactive crawls show CFZH progress as one live-updating terminal line. The
line reports saved post/reply counts, pending work, active detail requests,
actionable failures, suppressed persistent failures, and scheduled detail
requests. Redirected or non-interactive output suppresses the live line and
keeps actionable failures plus the final summary as normal log lines. Use
`WXC_PROGRESS=off` to disable live progress explicitly.

Counts are "known so far" because root posts and nested replies can discover
more reply links while the crawl is running.

Recipes that accept options use `key=value` tokens after the recipe name.

Example:

```bash
just crawl pages=5 max_requests=25 log_level=INFO
```

## Export

```bash
just export-flat
just export-reddit
```

## Inspect

```bash
just inspect
just inspect db=data/crawler.sqlite3 host=127.0.0.1 port=8765
```

`just inspect` rebuilds `inspector/frontend`, then serves the UI and API from
FastAPI.

The inspector Refresh control starts a real crawler run against the same SQLite
database that the UI is inspecting. It defaults to 5 listing pages and accepts
1-600 pages. The UI connects to crawl status over WebSocket, so opening or
reloading the page while a crawl is active shows the current run. Only one crawl
can run per inspector backend process; a running crawl can be asked to stop, and
the UI remains in a stopping state until the crawler process exits.

Backend-only startup is available for troubleshooting and skips the frontend build:

```bash
just inspect-api
```

## Deploy And Remote Operations

The personal public deployment uses Docker Compose on a VPS. The durable
deployment source of truth is [deployment.md](deployment.md).

Production deploy is manual in v1 through GitHub Actions `workflow_dispatch`.
CI stays automatic on push and pull request. Deployment config is managed by
GitHub variables and secrets; the workflow writes the VPS Compose `.env` during
deploy.

Local SSH operations load the untracked `.env.deploy` file by default:

```bash
WXC_DEPLOY_HOST=deploy@example.com
WXC_DEPLOY_PATH=/opt/wxc-cfzh
```

Remote operations are exposed through root recipes:

```bash
just ops-status
just ops-refresh pages=2
just ops-stop-crawl
just ops-scheduler-pause
just ops-scheduler-resume
just ops-logs service=scheduler tail=200
just ops-admin-logs tail=200
just ops-report
```

In production, browser refresh is read-only. Crawling is controlled by the
in-container `wxc-cfzh-admin` CLI and the scheduler service. Manual and
scheduled refreshes share one lock, so a scheduled tick skips while a manual
crawl is active and manual refresh reports the active crawl when the scheduler
already owns the lock.

## Local Docker Verification

Use local Docker recipes to verify the image and public read-only mode before a
cloud deploy:

```bash
just docker-local-build
just docker-local-up
just docker-local-up port=8766
just docker-local-up-scheduler port=8766 pages=1 interval=120
just docker-local-status
just docker-local-stop-crawl
just docker-local-refresh pages=1
just docker-local-scheduler-status
just docker-local-scheduler-pause
just docker-local-scheduler-resume
just docker-local-report
just docker-local-admin-logs tail=100
just docker-local-down
```

Local Docker data lives under ignored `data/docker-local/` by default and is
bind-mounted into containers as `/data`. The local scheduler does not start
unless explicitly requested with `just docker-local-up-scheduler`. Use the same
`port=` option with `docker-local-up-scheduler` if the default `8765` port is
already occupied. Local admin commands run inside the scheduler container when
it is available, or the web container during web-only verification, so status
and stop checks use a meaningful Docker PID namespace.

## Verification

```bash
just check
just test-crawler
just test-backend
just ui-build
```

`just check` is the full local validation harness. See
[quality.md](quality.md) for quality gates and
[design-docs/project-invariants.md](design-docs/project-invariants.md) for the
doc-first update rule.
