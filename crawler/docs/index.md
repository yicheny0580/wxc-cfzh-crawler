# Crawler Index

The crawler package owns Scrapy crawling, HTML parsing, SQLite persistence, and export shapes.

## Source Map

- [../src/wxc_cfzh_crawler/spiders/cfzh.py](../src/wxc_cfzh_crawler/spiders/cfzh.py): Scrapy spider and persistent frontier scheduling.
- [../src/wxc_cfzh_crawler/parsing.py](../src/wxc_cfzh_crawler/parsing.py): HTML parsing for forum indexes, root posts, and replies.
- [../src/wxc_cfzh_crawler/db.py](../src/wxc_cfzh_crawler/db.py): SQLite schema, upserts, frontier state, and fetch helpers.
- [../src/wxc_cfzh_crawler/export.py](../src/wxc_cfzh_crawler/export.py): flat and nested export shapes.
- [../pyproject.toml](../pyproject.toml): crawler dependencies, test paths, and lint settings.

## User-Facing Commands

```bash
just crawl
just crawl-smoke
just export-flat
```

Root recipe options are discoverable through:

```bash
just list
```

## Configuration

- `DATABASE_URL`: SQLite URL override.
- `WXC_DATA_DIR`: data directory override.
- `WXC_REPO_ROOT`: repo root override for unusual launch contexts.
- `WXC_CRAWLER_USER_AGENT`: crawler user agent override.
- `WXC_LOG_LEVEL`: default Scrapy log level.

By default, recipe-driven data writes go to root `data/crawler.sqlite3`.

## Behavior Notes

Listing pages are discovery feeds only. Stored data is organized by post/reply identity, not by listing page number. Already-crawled URLs are skipped unless a root listing shows a higher reply count than the database has seen.

`ROBOTSTXT_OBEY` is intentionally disabled because this crawler is admin-authorized for the target site. The spider still uses conservative concurrency, delay, retry, timeout, and AutoThrottle settings.

## Checks

```bash
just test-crawler
```
