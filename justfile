set shell := ["bash", "-uc"]

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

# Crawl recent CFZH pages into the default SQLite database.
crawl pages="3" max_requests="" start_url="https://bbs.wenxuecity.com/cfzh/" database_url="" log_level="":
    #!/usr/bin/env bash
    set -euo pipefail
    args=(-a "pages={{ pages }}" -a "start_url={{ start_url }}")
    if [[ -n "{{ max_requests }}" ]]; then
      args+=(-a "max_requests={{ max_requests }}")
    fi
    if [[ -n "{{ database_url }}" ]]; then
      args+=(-a "database_url={{ database_url }}")
    fi
    if [[ -n "{{ log_level }}" ]]; then
      args+=(-s "LOG_LEVEL={{ log_level }}")
    fi
    SCRAPY_SETTINGS_MODULE=wxc_cfzh_crawler.settings \
      uv run --package wxc-cfzh-crawler scrapy crawl cfzh "${args[@]}"

# Run a small crawl suitable for smoke testing.
crawl-smoke:
    just crawl pages=1 max_requests=3

# Export flat post and reply records as JSONL.
export-flat out="data/exports/cfzh.jsonl" database_url="":
    #!/usr/bin/env bash
    set -euo pipefail
    cmd=(
      uv run --package wxc-cfzh-crawler python -m wxc_cfzh_crawler.export
      --shape flat
      --format jsonl
      --out "{{ out }}"
    )
    if [[ -n "{{ database_url }}" ]]; then
      cmd+=(--database-url "{{ database_url }}")
    fi
    "${cmd[@]}"

# Export root posts with nested replies as JSON.
export-reddit out="data/exports/cfzh-posts.json" database_url="":
    #!/usr/bin/env bash
    set -euo pipefail
    cmd=(
      uv run --package wxc-cfzh-crawler python -m wxc_cfzh_crawler.export
      --shape reddit
      --format json
      --out "{{ out }}"
    )
    if [[ -n "{{ database_url }}" ]]; then
      cmd+=(--database-url "{{ database_url }}")
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

# Build the UI, then serve the inspector API and static frontend.
inspect host="127.0.0.1" port="8765" db="" reload="false": ui-build
    #!/usr/bin/env bash
    set -euo pipefail
    args=(app.main:app --host "{{ host }}" --port "{{ port }}")
    if [[ "{{ reload }}" == "true" ]]; then
      args+=(--reload)
    fi
    if [[ -n "{{ db }}" ]]; then
      export WXC_INSPECT_DB="{{ db }}"
    fi
    uv run --package wxc-cfzh-inspector-backend uvicorn "${args[@]}"

# Serve the inspector API without rebuilding the frontend.
inspect-api host="127.0.0.1" port="8765" db="" reload="false":
    #!/usr/bin/env bash
    set -euo pipefail
    args=(app.main:app --host "{{ host }}" --port "{{ port }}")
    if [[ "{{ reload }}" == "true" ]]; then
      args+=(--reload)
    fi
    if [[ -n "{{ db }}" ]]; then
      export WXC_INSPECT_DB="{{ db }}"
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

# Enforce production file length limits.
lint-lines:
    uv run python scripts/check_file_lines.py

# Run the full local validation harness.
check: lint lint-lines test
