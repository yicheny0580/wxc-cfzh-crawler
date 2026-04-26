# Architecture

The repository is organized around three domains:

- `crawler/`: Scrapy spider, parser, SQLite persistence, export code, and crawler tests.
- `inspector/`: read-only database inspector with FastAPI backend and React frontend.
- `data/`: ignored local runtime data, including SQLite databases and exports.

The root is the workspace control plane. It contains thin docs, the root
`pyproject.toml`, the shared `uv.lock`, the canonical `justfile`, and no domain
implementation code.

## Workspace

The root `pyproject.toml` defines a `uv` workspace with these members:

- `crawler`
- `inspector/backend`

The root `justfile` is the public command harness for humans and Codex. It
orchestrates workspace setup, crawl, export, inspection, tests, linting, and
frontend builds by calling the underlying package tools directly.

## Boundaries

- Crawler code must not import inspector code.
- Inspector backend reads the SQLite database in read-only mode and must not mutate crawler data.
- Shared local data paths should resolve to root `data/` unless explicitly overridden.
- User-facing workflows should be added to the root `justfile` before adding README-only command recipes.
