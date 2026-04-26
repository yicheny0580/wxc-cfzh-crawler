# Architecture

The repository is organized around three domains:

- `crawler/`: Scrapy spider, parser, SQLite persistence, export code, and crawler tests.
- `inspector/`: SQLite inspector with FastAPI backend, React frontend, and a controlled
  crawler refresh trigger.
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
- Inspector query endpoints read the SQLite database in read-only mode. The only inspector
  write path is the crawl refresh control, which starts the crawler package as a subprocess.
- Shared local data paths should resolve to root `data/` unless explicitly overridden.
- User-facing workflows should be added to the root `justfile` before adding README-only command recipes.
