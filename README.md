# wxc-cfzh

Local-first crawler and SQLite inspector for the Wenxuecity `财富智汇` forum.

## Quick Start

```bash
uv sync
uv run wxc crawl --pages 3
uv run wxc inspect
```

Useful smoke crawl:

```bash
uv run wxc crawl --pages 1 --max-requests 3
```

Export flat root/reply records:

```bash
uv run wxc export --shape flat --format jsonl --out data/exports/cfzh.jsonl
```

Export root posts with nested replies:

```bash
uv run wxc export --shape reddit --format json --out data/exports/cfzh-posts.json
```

## Repository Map

- [AGENTS.md](AGENTS.md): short agent entry point and source-of-truth map.
- [docs/index.md](docs/index.md): root documentation index.
- [crawler/](crawler/): Scrapy crawler, SQLite persistence, export logic, and crawler tests.
- [crawler/docs/index.md](crawler/docs/index.md): crawler behavior, parameters, and data notes.
- [inspector/](inspector/): FastAPI backend and React frontend for read-only SQLite inspection.
- [inspector/docs/index.md](inspector/docs/index.md): inspector startup, API, frontend, and troubleshooting.
- `data/`: ignored local SQLite databases and exports.

## Common Commands

```bash
uv run wxc --help
uv run wxc crawl --help
uv run wxc export --help
uv run wxc inspect --help
```

`wxc inspect` serves the built frontend through FastAPI. If `inspector/frontend/dist` is missing, it runs the frontend build first.

Low-level Scrapy usage is still available from the crawler project:

```bash
cd crawler
uv run scrapy crawl cfzh -a pages=1 -a max_requests=3
```
