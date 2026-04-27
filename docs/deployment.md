# Deployment

This project supports a small personal public deployment in addition to the
local-first workflow. The cloud deployment is intentionally modest: one
DigitalOcean Basic Droplet, Docker Compose, Cloudflare Free, public GitHub
Actions CI, and a manual deploy workflow.

## Operating Model

- Public browser traffic is read-only. The public Refresh action reloads API
  data from SQLite; it must not start or stop crawls.
- Crawling in production is managed by SSH/CLI operations and the scheduler
  container.
- The scheduler runs every 120 seconds with `pages=2` by default.
- Manual and scheduled crawls share one lock under the runtime data directory so
  only one crawler process runs at a time.
- SQLite remains the data store. Do not add a managed database, load balancer,
  object storage, or paid backup service for the default deployment.

## Files And Runtime Paths

- `.env.deploy.example`: tracked template for local SSH operations.
- `.env.deploy`: untracked local deploy target config.
- `Dockerfile`: production image for backend, frontend static assets, crawler,
  admin CLI, and scheduler.
- `docker-compose.yml`: VPS services for web, scheduler, and reverse proxy.
- `docker-compose.local.yml`: local Docker verification path that builds the
  image from the current checkout.
- `/data/crawler.sqlite3`: shared SQLite database inside containers.
- `/data/runtime/`: crawl lock, status, scheduler pause flag, and admin logs.
- `./data/docker-local/`: default host-visible local Docker data directory.
- `/opt/wxc-cfzh/data/`: default VPS data directory when Compose runs from
  `/opt/wxc-cfzh`.

The root `justfile` owns local operator commands. Commands should load
`.env.deploy` by default and allow one-off overrides where useful.

## SQLite Storage

Docker deployments use a bind-mounted data directory, not a Docker named
volume and not a single-file mount. SQLite WAL mode creates sidecar files such
as `crawler.sqlite3-wal` and `crawler.sqlite3-shm`, and the admin CLI writes
runtime locks and logs under the same mounted directory. A directory bind mount
keeps these files together and makes backup, restore, and troubleshooting
straightforward.

Defaults:

```bash
# Local Docker verification
./data/docker-local:/data

# VPS deployment when Compose runs in /opt/wxc-cfzh
./data:/data
```

On the VPS this means the database is normally visible at
`/opt/wxc-cfzh/data/crawler.sqlite3`. Override the host directory by setting
`WXC_DATA_DIR` for Docker Compose.

## Local Docker Verification

Use the local Compose file to test the container before deploying:

```bash
just docker-local-build
just docker-local-up
```

Open `http://127.0.0.1:8765`. If that port is already used, choose another
host port:

```bash
just docker-local-up port=8766
```

The default local Docker data directory is `data/docker-local/`, which is
ignored by git.

Run diagnostics or a one-off crawl:

```bash
just docker-local-status
just docker-local-stop-crawl
just docker-local-refresh pages=1
just docker-local-report
just docker-local-logs service=web tail=100
just docker-local-admin-logs tail=100
```

Local admin commands execute inside the running `scheduler` container when it is
up, otherwise inside the running `web` container. This keeps Docker-local PID
liveness, busy-lock checks, and stop behavior aligned with production.

The local scheduler is opt-in:

```bash
just docker-local-up-scheduler
just docker-local-up-scheduler port=8766
just docker-local-up-scheduler port=8766 pages=1 interval=120
just docker-local-scheduler-status
just docker-local-scheduler-pause
just docker-local-scheduler-resume
```

Stop the local stack with:

```bash
just docker-local-down
```

## Manual Deploy

CI runs automatically on push and pull request. Production deploy is manual in
v1 and uses `workflow_dispatch`; it is not triggered by every push and does not
yet deploy from tags. A future tag-triggered deploy can reuse the same workflow
after the manual path is proven.

The CI workflow sets up Python 3.13 and Node 24 before running the root
validation harness.

The deploy workflow builds and pushes a public GHCR image, connects to the VPS
over SSH, then runs Docker Compose pull/up in the configured deployment
directory. Use workflow concurrency so overlapping manual deploys do not race.
The workflow creates the deployment data directory before starting Compose.

## SSH Operations

Local operations use `.env.deploy`:

```bash
WXC_DEPLOY_HOST=deploy@example.com
WXC_DEPLOY_PATH=/opt/wxc-cfzh
```

Supported root commands:

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

The in-container admin CLI is `wxc-cfzh-admin`. It supports:

```bash
wxc-cfzh-admin refresh --pages 2 --reason manual
wxc-cfzh-admin stop --wait --force-after 30
wxc-cfzh-admin status --json
wxc-cfzh-admin report
wxc-cfzh-admin logs --tail 200 --follow
wxc-cfzh-admin scheduler run --interval 120 --pages 2
wxc-cfzh-admin scheduler pause
wxc-cfzh-admin scheduler resume
wxc-cfzh-admin scheduler status
```

`ops-report` should combine Docker Compose state, Docker disk usage, admin CLI
diagnostics, and recent logs so a failing deployment can be inspected without
guessing which command to run first.

## Race Handling

- Manual refresh while a scheduled crawl is active reports the active crawl and
  exits without starting another process.
- Scheduled ticks skip while any crawl is active, log `skip_busy`, and try
  again on the next interval.
- Stop while a crawl is active sends `SIGTERM` to the crawler process group,
  waits for the configured grace period, then sends `SIGKILL` only if the
  process is still alive.
- Stop while idle reports idle and exits successfully.
- Scheduler pause prevents future scheduled crawls but does not kill an active
  crawl.
- Status and report commands detect stale lock/status files by checking process
  liveness.

## Public Safety

- Public mode disables browser-accessible crawl start/stop/WebSocket routes.
- Public API responses should not expose absolute filesystem paths.
- Search must avoid unbounded `%term%` scans before public exposure. Use the
  crawler-maintained SQLite FTS5 index for public search and keep API limits
  bounded.
- Cloudflare should proxy the site, cache static assets, bypass cache for
  `/api/*`, and apply the single Free-plan rate limiting rule to API paths.
- The VPS firewall should expose SSH, HTTP, and HTTPS only.

## Cost Guardrails

- Use the DigitalOcean $4 Basic Droplet shape by default.
- Do not enable paid managed services by default.
- Configure Docker log rotation and prune old images during deploy.
- Enable a DigitalOcean billing alert around the expected monthly ceiling.
- Monitor Droplet transfer; outbound transfer beyond the included pool can be
  billed separately.

Relevant external references:

- GitHub Actions public repository billing:
  https://docs.github.com/en/billing/managing-billing-for-your-products/about-billing-for-github-actions
- DigitalOcean Droplet pricing:
  https://www.digitalocean.com/pricing/droplets
- DigitalOcean Droplet bandwidth pricing:
  https://docs.digitalocean.com/products/droplets/details/pricing/
- DigitalOcean billing alerts:
  https://docs.digitalocean.com/platform/billing/billing-alerts/
- Cloudflare rate limiting rules:
  https://developers.cloudflare.com/waf/rate-limiting-rules/
