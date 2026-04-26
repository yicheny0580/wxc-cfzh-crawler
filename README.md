# wxc-cfzh-crawler

Local-first persistent frontier crawler for the Wenxuecity `财富智汇` forum.

The crawler uses the first few `https://bbs.wenxuecity.com/cfzh/` listing pages as a discovery feed for recent post URLs, stores crawl state in a persistent SQLite frontier, writes root posts and replies into normalized tables, and exports posts with recursive `replies` arrays when you want a Reddit-style shape.

## Quick Start

```bash
uv sync
uv run scrapy crawl cfzh -a pages=3
```

Useful local smoke run:

```bash
uv run scrapy crawl cfzh -a pages=1 -a max_requests=3
```

Export flat root/reply records:

```bash
uv run python -m wxc_cfzh_crawler.export --shape flat --format jsonl --out data/exports/cfzh.jsonl
```

Export root posts with nested replies:

```bash
uv run python -m wxc_cfzh_crawler.export --shape reddit --format json --out data/exports/cfzh-posts.json
```

## Local Inspector

The SQLite inspector is isolated under `inspector/` and reads the crawler database without
writing to it.

Backend:

```bash
uv run --project inspector/backend uvicorn app.main:app --reload --host 127.0.0.1 --port 8765
```

Frontend:

```bash
npm --prefix inspector/frontend run dev
```

By default the backend reads `data/crawler.sqlite3`. Set `WXC_INSPECT_DB=/path/to/crawler.sqlite3`
to inspect another database. After building the frontend with
`npm --prefix inspector/frontend run build`, the FastAPI server will serve the built app directly.

## Configuration

Environment variables:

- `DATABASE_URL`: defaults to `sqlite:///data/crawler.sqlite3`.
- `WXC_DATA_DIR`: defaults to `data` and is used only to build the default SQLite path.
- `WXC_CRAWLER_USER_AGENT`: defaults to a standard desktop Chrome user agent.

Spider arguments:

- `pages`: number of recent forum listing pages to use for frontier discovery. Default: `3`.
- `start_url`: forum URL to crawl. Default: `https://bbs.wenxuecity.com/cfzh/`.
- `max_requests`: optional cap on detail-page frontier requests for small smoke runs.
- `max_posts`: backward-compatible alias for `max_requests`.

The crawler does not organize stored data by listing page. Listing pages move as new posts arrive, so they are only used to discover recent root/reply URLs. Already-crawled URLs are skipped unless a root listing shows a higher reply count than the database has seen.

## Notes

`ROBOTSTXT_OBEY` is intentionally disabled because this crawler is admin-authorized for the target site. The spider still uses conservative defaults: low concurrency, download delay, retries, and AutoThrottle.
