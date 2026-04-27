set shell := ["bash", "-uc"]
set tempdir := "/tmp"
set positional-arguments

# List canonical root workflows.
default:
    @just --list

# List canonical root workflows.
list:
    @just --list

# Verify required local tools are available.
doctor:
    @command -v just
    @command -v uv
    @command -v npm
    @just --version
    @uv --version
    @npm --version

# Install Python workspace dependencies and frontend dependencies.
setup:
    uv sync
    npm --prefix inspector/frontend ci

# Crawl recent CFZH pages; options: pages=3 max_requests= database_url= log_level=.
crawl *options:
    #!/usr/bin/env bash
    set -euo pipefail
    pages=3
    max_requests=
    start_url=https://bbs.wenxuecity.com/cfzh/
    database_url=
    log_level=

    for option in "$@"; do
      case "$option" in
        pages=*|--pages=*) pages="${option#*=}" ;;
        max_requests=*|max-requests=*|--max-requests=*) max_requests="${option#*=}" ;;
        start_url=*|start-url=*|--start-url=*) start_url="${option#*=}" ;;
        database_url=*|database-url=*|--database-url=*) database_url="${option#*=}" ;;
        log_level=*|log-level=*|--log-level=*) log_level="${option#*=}" ;;
        *)
          echo "Unknown crawl option: $option" >&2
          echo "Use key=value options: pages=, max_requests=, start_url=, database_url=, log_level=." >&2
          exit 2
          ;;
      esac
    done

    args=(-a "pages=$pages" -a "start_url=$start_url")
    if [[ -n "$max_requests" ]]; then
      args+=(-a "max_requests=$max_requests")
    fi
    if [[ -n "$database_url" ]]; then
      args+=(-a "database_url=$database_url")
    fi
    if [[ -n "$log_level" ]]; then
      args+=(-s "LOG_LEVEL=$log_level")
    fi
    SCRAPY_SETTINGS_MODULE=wxc_cfzh_crawler.settings \
      uv run --package wxc-cfzh-crawler scrapy crawl cfzh "${args[@]}"

# Run a small crawl suitable for smoke testing.
crawl-smoke:
    just crawl pages=1 max_requests=3

# Export flat post and reply records as JSONL; options: out= database_url=.
export-flat *options:
    #!/usr/bin/env bash
    set -euo pipefail
    out=data/exports/cfzh.jsonl
    database_url=

    for option in "$@"; do
      case "$option" in
        out=*|--out=*) out="${option#*=}" ;;
        database_url=*|database-url=*|--database-url=*) database_url="${option#*=}" ;;
        *)
          echo "Unknown export-flat option: $option" >&2
          echo "Use key=value options: out=, database_url=." >&2
          exit 2
          ;;
      esac
    done

    cmd=(
      uv run --package wxc-cfzh-crawler python -m wxc_cfzh_crawler.export
      --shape flat
      --format jsonl
      --out "$out"
    )
    if [[ -n "$database_url" ]]; then
      cmd+=(--database-url "$database_url")
    fi
    "${cmd[@]}"

# Export root posts with nested replies as JSON; options: out= database_url=.
export-reddit *options:
    #!/usr/bin/env bash
    set -euo pipefail
    out=data/exports/cfzh-posts.json
    database_url=

    for option in "$@"; do
      case "$option" in
        out=*|--out=*) out="${option#*=}" ;;
        database_url=*|database-url=*|--database-url=*) database_url="${option#*=}" ;;
        *)
          echo "Unknown export-reddit option: $option" >&2
          echo "Use key=value options: out=, database_url=." >&2
          exit 2
          ;;
      esac
    done

    cmd=(
      uv run --package wxc-cfzh-crawler python -m wxc_cfzh_crawler.export
      --shape reddit
      --format json
      --out "$out"
    )
    if [[ -n "$database_url" ]]; then
      cmd+=(--database-url "$database_url")
    fi
    "${cmd[@]}"

# Build the inspector frontend.
ui-build:
    npm --prefix inspector/frontend run build

# Run the inspector frontend dev server.
ui-dev:
    npm --prefix inspector/frontend run dev

# Preview the built inspector frontend.
ui-preview:
    npm --prefix inspector/frontend run preview

# Build the UI, then serve the inspector API and static frontend; options: host= port= db= reload=.
inspect *options:
    #!/usr/bin/env bash
    set -euo pipefail
    host=127.0.0.1
    port=8765
    db=
    reload=false

    for option in "$@"; do
      case "$option" in
        host=*|--host=*) host="${option#*=}" ;;
        port=*|--port=*) port="${option#*=}" ;;
        db=*|--db=*) db="${option#*=}" ;;
        reload=*|--reload=*) reload="${option#*=}" ;;
        --reload) reload=true ;;
        *)
          echo "Unknown inspect option: $option" >&2
          echo "Use key=value options: host=, port=, db=, reload=." >&2
          exit 2
          ;;
      esac
    done

    npm --prefix inspector/frontend run build
    args=(app.main:app --host "$host" --port "$port")
    if [[ "$reload" == "true" ]]; then
      args+=(--reload)
    fi
    if [[ -n "$db" ]]; then
      export WXC_INSPECT_DB="$db"
    fi
    uv run --package wxc-cfzh-inspector-backend uvicorn "${args[@]}"

# Serve the inspector API without rebuilding the frontend; options: host= port= db= reload=.
inspect-api *options:
    #!/usr/bin/env bash
    set -euo pipefail
    host=127.0.0.1
    port=8765
    db=
    reload=false

    for option in "$@"; do
      case "$option" in
        host=*|--host=*) host="${option#*=}" ;;
        port=*|--port=*) port="${option#*=}" ;;
        db=*|--db=*) db="${option#*=}" ;;
        reload=*|--reload=*) reload="${option#*=}" ;;
        --reload) reload=true ;;
        *)
          echo "Unknown inspect-api option: $option" >&2
          echo "Use key=value options: host=, port=, db=, reload=." >&2
          exit 2
          ;;
      esac
    done

    args=(app.main:app --host "$host" --port "$port")
    if [[ "$reload" == "true" ]]; then
      args+=(--reload)
    fi
    if [[ -n "$db" ]]; then
      export WXC_INSPECT_DB="$db"
    fi
    uv run --package wxc-cfzh-inspector-backend uvicorn "${args[@]}"

# Show production crawl/scheduler status over SSH; options: host= path=.
ops-status *options:
    #!/usr/bin/env bash
    set -euo pipefail
    bash scripts/ops_remote.sh "$@" -- \
      docker compose exec -T scheduler wxc-cfzh-admin status --json

# Start a manual production crawl over SSH; options: pages=2 host= path=.
ops-refresh *options:
    #!/usr/bin/env bash
    set -euo pipefail
    pages=2
    pass=()
    for option in "$@"; do
      case "$option" in
        pages=*|--pages=*) pages="${option#*=}" ;;
        host=*|--host=*|path=*|--path=*) pass+=("$option") ;;
        *)
          echo "Unknown ops-refresh option: $option" >&2
          echo "Use key=value options: pages=, host=, path=." >&2
          exit 2
          ;;
      esac
    done
    bash scripts/ops_remote.sh "${pass[@]}" -- \
      docker compose exec -T scheduler wxc-cfzh-admin refresh --pages "$pages" --reason manual

# Stop a production crawl over SSH; options: host= path=.
ops-stop-crawl *options:
    #!/usr/bin/env bash
    set -euo pipefail
    bash scripts/ops_remote.sh "$@" -- \
      docker compose exec -T scheduler wxc-cfzh-admin stop --wait --force-after 30

# Pause production scheduled crawls over SSH; options: host= path=.
ops-scheduler-pause *options:
    #!/usr/bin/env bash
    set -euo pipefail
    bash scripts/ops_remote.sh "$@" -- \
      docker compose exec -T scheduler wxc-cfzh-admin scheduler pause

# Resume production scheduled crawls over SSH; options: host= path=.
ops-scheduler-resume *options:
    #!/usr/bin/env bash
    set -euo pipefail
    bash scripts/ops_remote.sh "$@" -- \
      docker compose exec -T scheduler wxc-cfzh-admin scheduler resume

# Show production Docker logs over SSH; options: service=scheduler tail=200 follow=false host= path=.
ops-logs *options:
    #!/usr/bin/env bash
    set -euo pipefail
    service=scheduler
    tail=200
    follow=false
    pass=()
    for option in "$@"; do
      case "$option" in
        service=*|--service=*) service="${option#*=}" ;;
        tail=*|--tail=*) tail="${option#*=}" ;;
        follow=*|--follow=*) follow="${option#*=}" ;;
        --follow) follow=true ;;
        host=*|--host=*|path=*|--path=*) pass+=("$option") ;;
        *)
          echo "Unknown ops-logs option: $option" >&2
          echo "Use key=value options: service=, tail=, follow=, host=, path=." >&2
          exit 2
          ;;
      esac
    done
    args=(docker compose logs --tail "$tail")
    if [[ "$follow" == "true" ]]; then
      args+=(--follow)
    fi
    args+=("$service")
    bash scripts/ops_remote.sh "${pass[@]}" -- "${args[@]}"

# Show production admin/crawler event logs over SSH; options: tail=200 follow=false host= path=.
ops-admin-logs *options:
    #!/usr/bin/env bash
    set -euo pipefail
    tail=200
    follow=false
    pass=()
    for option in "$@"; do
      case "$option" in
        tail=*|--tail=*) tail="${option#*=}" ;;
        follow=*|--follow=*) follow="${option#*=}" ;;
        --follow) follow=true ;;
        host=*|--host=*|path=*|--path=*) pass+=("$option") ;;
        *)
          echo "Unknown ops-admin-logs option: $option" >&2
          echo "Use key=value options: tail=, follow=, host=, path=." >&2
          exit 2
          ;;
      esac
    done
    args=(docker compose exec -T scheduler wxc-cfzh-admin logs --tail "$tail")
    if [[ "$follow" == "true" ]]; then
      args+=(--follow)
    fi
    bash scripts/ops_remote.sh "${pass[@]}" -- "${args[@]}"

# Print production diagnostics over SSH; options: host= path=.
ops-report *options:
    #!/usr/bin/env bash
    set -euo pipefail
    bash scripts/ops_remote.sh "$@" -- bash -lc \
      "docker compose ps && docker system df && docker compose exec -T scheduler wxc-cfzh-admin report && docker compose logs --tail 80 web scheduler"

# Build the local Docker verification image.
docker-local-build:
    docker compose -f docker-compose.local.yml build web admin scheduler

# Start the local Docker web service; options: port=8765.
docker-local-up *options:
    #!/usr/bin/env bash
    set -euo pipefail
    port=8765
    for option in "$@"; do
      case "$option" in
        port=*|--port=*) port="${option#*=}" ;;
        *)
          echo "Unknown docker-local-up option: $option" >&2
          echo "Use key=value options: port=." >&2
          exit 2
          ;;
      esac
    done
    WXC_LOCAL_PORT="$port" docker compose -f docker-compose.local.yml up -d web

# Start local Docker web and scheduler services; options: port=8765 interval=120 pages=2.
docker-local-up-scheduler *options:
    #!/usr/bin/env bash
    set -euo pipefail
    port=8765
    interval=120
    pages=2
    for option in "$@"; do
      case "$option" in
        port=*|--port=*) port="${option#*=}" ;;
        interval=*|--interval=*) interval="${option#*=}" ;;
        pages=*|--pages=*) pages="${option#*=}" ;;
        *)
          echo "Unknown docker-local-up-scheduler option: $option" >&2
          echo "Use key=value options: port=, interval=, pages=." >&2
          exit 2
          ;;
      esac
    done
    WXC_LOCAL_PORT="$port" WXC_SCHEDULER_INTERVAL="$interval" WXC_SCHEDULER_PAGES="$pages" \
      docker compose -f docker-compose.local.yml --profile scheduler up -d web scheduler

# Stop the local Docker verification stack.
docker-local-down:
    docker compose -f docker-compose.local.yml --profile scheduler down

# Show local Docker crawl/scheduler status.
docker-local-status:
    bash scripts/docker_local_admin.sh wxc-cfzh-admin status --json

# Start a manual local Docker crawl; options: pages=2.
docker-local-refresh *options:
    #!/usr/bin/env bash
    set -euo pipefail
    pages=2
    for option in "$@"; do
      case "$option" in
        pages=*|--pages=*) pages="${option#*=}" ;;
        *)
          echo "Unknown docker-local-refresh option: $option" >&2
          echo "Use key=value options: pages=." >&2
          exit 2
          ;;
      esac
    done
    bash scripts/docker_local_admin.sh wxc-cfzh-admin refresh --pages "$pages" --reason local-docker

# Stop a local Docker crawl.
docker-local-stop-crawl:
    bash scripts/docker_local_admin.sh wxc-cfzh-admin stop --wait --force-after 30

# Pause local Docker scheduled crawls.
docker-local-scheduler-pause:
    bash scripts/docker_local_admin.sh wxc-cfzh-admin scheduler pause

# Resume local Docker scheduled crawls.
docker-local-scheduler-resume:
    bash scripts/docker_local_admin.sh wxc-cfzh-admin scheduler resume

# Show local Docker scheduler pause status.
docker-local-scheduler-status:
    bash scripts/docker_local_admin.sh wxc-cfzh-admin scheduler status --json

# Show local Docker logs; options: service=web tail=100 follow=false.
docker-local-logs *options:
    #!/usr/bin/env bash
    set -euo pipefail
    service=web
    tail=100
    follow=false
    for option in "$@"; do
      case "$option" in
        service=*|--service=*) service="${option#*=}" ;;
        tail=*|--tail=*) tail="${option#*=}" ;;
        follow=*|--follow=*) follow="${option#*=}" ;;
        --follow) follow=true ;;
        *)
          echo "Unknown docker-local-logs option: $option" >&2
          echo "Use key=value options: service=, tail=, follow=." >&2
          exit 2
          ;;
      esac
    done
    args=(docker compose -f docker-compose.local.yml logs --tail "$tail")
    if [[ "$follow" == "true" ]]; then
      args+=(--follow)
    fi
    args+=("$service")
    "${args[@]}"

# Show local Docker admin/crawler event logs; options: tail=200 follow=false.
docker-local-admin-logs *options:
    #!/usr/bin/env bash
    set -euo pipefail
    tail=200
    follow=false
    for option in "$@"; do
      case "$option" in
        tail=*|--tail=*) tail="${option#*=}" ;;
        follow=*|--follow=*) follow="${option#*=}" ;;
        --follow) follow=true ;;
        *)
          echo "Unknown docker-local-admin-logs option: $option" >&2
          echo "Use key=value options: tail=, follow=." >&2
          exit 2
          ;;
      esac
    done
    args=(wxc-cfzh-admin logs --tail "$tail")
    if [[ "$follow" == "true" ]]; then
      args+=(--follow)
    fi
    bash scripts/docker_local_admin.sh "${args[@]}"

# Print local Docker diagnostics.
docker-local-report:
    bash scripts/docker_local_admin.sh wxc-cfzh-admin report

# Run root quality-tool tests.
test-root:
    uv run pytest tests

# Run crawler tests.
test-crawler:
    uv run --project crawler pytest crawler/tests

# Run inspector backend tests.
test-backend:
    uv run --project inspector/backend pytest inspector/backend/tests

# Run all Python tests.
test-python: test-root test-crawler test-backend

# Run all tests and the frontend build.
test: test-python ui-build

# Run Python lint checks.
lint:
    uv run ruff check .

# Check justfile formatting.
lint-just:
    just --fmt --check

# Enforce production file length limits.
lint-lines:
    uv run python scripts/check_file_lines.py

# Create an active exec-plan; options: slug=short-name title=.
exec-plan-new *options:
    #!/usr/bin/env bash
    set -euo pipefail
    uv run python scripts/manage_exec_plan.py new "$@"

# Move an active exec-plan to completed; options: slug=YYYYMMDD-short-name.
exec-plan-complete *options:
    #!/usr/bin/env bash
    set -euo pipefail
    uv run python scripts/manage_exec_plan.py complete "$@"

# Run the full local validation harness.
check: lint-just lint lint-lines test
