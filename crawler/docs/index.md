# Crawler Index

The crawler package owns Scrapy crawling, HTML parsing, SQLite persistence, and export shapes.

This file is the crawler package map. Durable cross-domain rules live in root
docs; crawler docs should stay focused on crawler source layout, package-local
configuration, crawler behavior notes, and crawler checks.

## Root Source Of Truth

- [../../docs/design-docs/project-invariants.md](../../docs/design-docs/project-invariants.md): doc-first workflow, data ownership, and crawler/inspector boundaries.
- [../../docs/design-docs/code-unit-design.md](../../docs/design-docs/code-unit-design.md): module and interface expectations.
- [../../docs/product-specs/crawler-inspector-workflows.md](../../docs/product-specs/crawler-inspector-workflows.md): supported crawl and export workflows.
- [../../docs/references/wenxuecity-cfzh.md](../../docs/references/wenxuecity-cfzh.md): target-site reference URLs and page-shape notes.

## Source Map

- [../src/wxc_cfzh_crawler/spiders/cfzh.py](../src/wxc_cfzh_crawler/spiders/cfzh.py): Scrapy spider and persistent frontier scheduling.
- [../src/wxc_cfzh_crawler/admin_cli.py](../src/wxc_cfzh_crawler/admin_cli.py): production
  SSH/admin CLI for manual refresh, scheduler management, status, logs, and diagnostics.
- [../src/wxc_cfzh_crawler/parsing.py](../src/wxc_cfzh_crawler/parsing.py): HTML parsing for forum indexes, root posts, and replies.
- [../src/wxc_cfzh_crawler/listing_records.py](../src/wxc_cfzh_crawler/listing_records.py): conversion from listing rows to frontier and listing-only records.
- [../src/wxc_cfzh_crawler/db.py](../src/wxc_cfzh_crawler/db.py): SQLite schema, upserts, frontier state, and fetch helpers.
- [../src/wxc_cfzh_crawler/export.py](../src/wxc_cfzh_crawler/export.py): flat and nested export shapes.
- [../pyproject.toml](../pyproject.toml): crawler dependencies, test paths, and lint settings.

## User-Facing Commands

```bash
just crawl
just crawl-smoke
just export-flat
```

Production deployments use `wxc-cfzh-admin` inside the Docker image and
repo-level `just ops-*` SSH wrappers. See
[../../docs/deployment.md](../../docs/deployment.md).

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
- `WXC_PROGRESS`: live terminal progress mode. Use `off` to disable.
- `WXC_ADMIN_DATA_DIR`: production admin CLI data directory override. Defaults
  to the crawler data directory.
- `WXC_ADMIN_LOG`: production admin CLI log file override.

By default, recipe-driven data writes go to root `data/crawler.sqlite3`.

## Behavior Notes

Listing pages are discovery feeds only. Stored data is organized by post/reply identity, not by listing page number. Already-crawled URLs are skipped unless a root listing shows a higher reply count than the database has seen. When that happens, the root post and known replies under that root are reopened so nested reply links can be rediscovered.

Listing rows expose byte counts and nesting. When a discovered post or reply is
listed as `0 bytes` and the listing/comment tree shows no nested replies, the
crawler stores the visible metadata and marks the frontier row done without
opening the detail page. Listing-only records must preserve visible author
metadata from both current `a.nickname` member-profile links and older
`a.username`/`profile.php` links.

Interactive crawler progress is shown as one live-updating `CFZH` terminal line.
Redirected or non-interactive output suppresses the live line and leaves
actionable failures plus the final summary as normal log lines. Frontier totals
are known-so-far counts because parsing detail pages can discover additional
nested replies.
Detail-page persistence is transactionally grouped: a fetched root post or reply
is saved together with child frontier rows discovered from that response before
the parent frontier row is marked done. If the process stops mid-detail, startup
resets that in-progress frontier row to pending so it can be retried.
Detail responses that return HTTP 200 but expose no parseable title, author,
published time, body, byte count, or read count are treated as failed frontier
attempts instead of being saved as blank post or reply records. Failed frontier
rows are retried on later refreshes even when the requested listing pages would
not rediscover those posts or replies. After 5 failed refresh attempts, a row is
marked suppressed: it is preserved for auditability, excluded from normal failed
counts, and no longer retried until a future listing update reopens it.

Production manual refresh and scheduled refresh share a lock under the runtime
data directory. A scheduled tick skips while any crawl is active; a manual
refresh reports the active crawl instead of starting a second writer.

## Checks

```bash
just test-crawler
```
