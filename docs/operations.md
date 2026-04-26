# Operations

## Setup

```bash
uv sync
npm --prefix inspector/frontend install
```

`npm install` is only needed when frontend dependencies are not already present.

## Crawl

```bash
uv run wxc crawl --pages 3
uv run wxc crawl --pages 1 --max-requests 3
```

Useful options:

- `--pages`: recent forum listing pages to scan for frontier discovery.
- `--max-requests`: optional detail-page request cap for smoke runs.
- `--database-url`: SQLite database URL override.
- `--log-level`: Scrapy log level override.

## Export

```bash
uv run wxc export --shape flat --format jsonl --out data/exports/cfzh.jsonl
uv run wxc export --shape reddit --format json --out data/exports/cfzh-posts.json
```

## Inspect

```bash
uv run wxc inspect
uv run wxc inspect --db data/crawler.sqlite3 --host 127.0.0.1 --port 8765
```

`wxc inspect` builds `inspector/frontend` if the built UI is missing, then serves the UI and API from FastAPI.

Backend-only startup is available for troubleshooting:

```bash
uv run wxc inspect --skip-ui-build
```

## Verification

```bash
uv run --project crawler pytest crawler/tests
uv run --project inspector/backend pytest inspector/backend/tests
npm --prefix inspector/frontend run build
```
