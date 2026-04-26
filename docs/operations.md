# Operations

## Setup

```bash
uv tool install rust-just
just setup
```

Use any supported `just` installation method from the
[Just Programmer's Manual](https://just.systems/man/en/packages.html). Run
`just setup` after cloning or when frontend dependency manifests change.

Useful discovery and environment checks:

```bash
just list
just doctor
```

## Crawl

```bash
just crawl
just crawl-smoke
```

Useful options:

- `pages`: recent forum listing pages to scan for frontier discovery.
- `max_requests`: optional detail-page request cap for smoke runs.
- `database_url`: SQLite database URL override.
- `log_level`: Scrapy log level override.

Interactive crawls show CFZH progress as one live-updating terminal line. The
line reports saved post/reply counts, pending work, active detail requests,
failures, and scheduled detail requests. Redirected or non-interactive output
suppresses the live line and keeps failures plus the final summary as normal log
lines. Use `WXC_PROGRESS=off` to disable live progress explicitly.

Counts are "known so far" because root posts and nested replies can discover
more reply links while the crawl is running.

Recipes that accept options use `key=value` tokens after the recipe name.

Example:

```bash
just crawl pages=5 max_requests=25 log_level=INFO
```

## Export

```bash
just export-flat
just export-reddit
```

## Inspect

```bash
just inspect
just inspect db=data/crawler.sqlite3 host=127.0.0.1 port=8765
```

`just inspect` rebuilds `inspector/frontend`, then serves the UI and API from
FastAPI.

Backend-only startup is available for troubleshooting and skips the frontend build:

```bash
just inspect-api
```

## Verification

```bash
just check
just test-crawler
just test-backend
just ui-build
```
