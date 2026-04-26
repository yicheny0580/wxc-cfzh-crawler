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

# Create an active exec-plan; options: slug= title=.
exec-plan-new *options:
    #!/usr/bin/env bash
    set -euo pipefail
    uv run python scripts/manage_exec_plan.py new "$@"

# Move an active exec-plan to completed; options: slug=.
exec-plan-complete *options:
    #!/usr/bin/env bash
    set -euo pipefail
    uv run python scripts/manage_exec_plan.py complete "$@"

# Run the full local validation harness.
check: lint-just lint lint-lines test
