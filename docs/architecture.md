# Architecture

The repository is organized around three domains:

- `crawler/`: Scrapy spider, parser, SQLite persistence, export code, and crawler tests.
- `inspector/`: read-only database inspector with FastAPI backend and React frontend.
- `data/`: ignored local runtime data, including SQLite databases and exports.

The root is the workspace control plane. It contains thin docs, the root `pyproject.toml`, the shared `uv.lock`, and no domain implementation code.

## Workspace

The root `pyproject.toml` defines a `uv` workspace with these members:

- `crawler`
- `inspector/backend`

The root environment depends on both members so `uv run wxc ...` works from the repository root. The `wxc` command is owned by the crawler package because it wraps crawler/export behavior and orchestrates inspector startup.

## Boundaries

- Crawler code must not import inspector code.
- Inspector backend reads the SQLite database in read-only mode and must not mutate crawler data.
- Shared local data paths should resolve to root `data/` unless explicitly overridden.
- User-facing commands should be added to `wxc` before adding README-only command recipes.
