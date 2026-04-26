# Crawler Index

The crawler package owns Scrapy crawling, HTML parsing, SQLite persistence, and export shapes.

## Source Map

- [../src/wxc_cfzh_crawler/spiders/cfzh.py](../src/wxc_cfzh_crawler/spiders/cfzh.py): Scrapy spider and persistent frontier scheduling.
- [../src/wxc_cfzh_crawler/parsing.py](../src/wxc_cfzh_crawler/parsing.py): HTML parsing for forum indexes, root posts, and replies.
- [../src/wxc_cfzh_crawler/db.py](../src/wxc_cfzh_crawler/db.py): SQLite schema, upserts, frontier state, and fetch helpers.
- [../src/wxc_cfzh_crawler/export.py](../src/wxc_cfzh_crawler/export.py): flat and nested export shapes.
- [../src/wxc_cfzh_crawler/cli.py](../src/wxc_cfzh_crawler/cli.py): `wxc crawl`, `wxc export`, and inspector orchestration.
- [../pyproject.toml](../pyproject.toml): crawler dependencies, scripts, test paths, and lint settings.

## User-Facing Commands

```bash
uv run wxc crawl --pages 3
uv run wxc crawl --pages 1 --max-requests 3
uv run wxc export --shape flat --format jsonl --out data/exports/cfzh.jsonl
```

CLI options are discoverable through:

```bash
uv run wxc crawl --help
uv run wxc export --help
```

## Configuration

- `DATABASE_URL`: SQLite URL override.
- `WXC_DATA_DIR`: data directory override.
- `WXC_REPO_ROOT`: repo root override for unusual launch contexts.
- `WXC_CRAWLER_USER_AGENT`: crawler user agent override.
- `WXC_LOG_LEVEL`: default Scrapy log level.

By default, CLI-driven data writes go to root `data/crawler.sqlite3`.

## Behavior Notes

Listing pages are discovery feeds only. Stored data is organized by post/reply identity, not by listing page number. Already-crawled URLs are skipped unless a root listing shows a higher reply count than the database has seen.

`ROBOTSTXT_OBEY` is intentionally disabled because this crawler is admin-authorized for the target site. The spider still uses conservative concurrency, delay, retry, timeout, and AutoThrottle settings.

## Checks

```bash
uv run --project crawler pytest crawler/tests
```
