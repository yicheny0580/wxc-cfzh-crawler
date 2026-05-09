# Empty Detail Post Handling

## Goal

Fix the `45217` empty-post symptom so malformed/sparse detail responses do not
produce null post records that sort above real forum posts, and repair the local
SQLite row for the reported post after validation.

## Context

- Stable docs read: [README.md](../../../README.md),
  [agent-workflow.md](../../design-docs/agent-workflow.md),
  [crawler/docs/index.md](../../../crawler/docs/index.md), and
  [inspector/docs/index.md](../../../inspector/docs/index.md).
- Source files in scope:
  [cfzh.py](../../../crawler/src/wxc_cfzh_crawler/spiders/cfzh.py),
  [parsing.py](../../../crawler/src/wxc_cfzh_crawler/parsing.py), and
  [_db_results.py](../../../inspector/backend/app/_db_results.py).
- Tests in scope:
  [crawler/tests/test_spider.py](../../../crawler/tests/test_spider.py) and
  [inspector/backend/tests/test_api.py](../../../inspector/backend/tests/test_api.py).
- Local diagnosis: `data/crawler.sqlite3` has one sparse post row for
  `45217` with null title, author, published date, body text/html, byte count,
  and reply count. Its frontier row is marked done with HTTP 200 and the
  listing title preserved. The inspector orders posts/results by
  `COALESCE(published_at, crawled_at, '')`, which lets this sparse row appear
  near the top by crawl time.
- Live page check: `https://bbs.wenxuecity.com/cfzh/45217.html` currently
  contains normal detail content, including title, author, published time,
  body HTML, and byte count.
- Known unrelated dirty files before tracked edits: none.
- This active plan was created as the first tracked implementation artifact.

## Plan

1. Add crawler coverage for a post-detail URL that returns HTTP 200 but no
   parseable detail fields, expecting the frontier row to be failed and no
   empty post row to be saved.
2. Add inspector backend coverage showing undated/sparse rows sort after dated
   forum records instead of by crawl time.
3. Update crawler parsing/handling to reject detail responses that have no
   title, author, published time, body HTML/text, byte count, or read count.
4. Update inspector post/result ordering to sort by source published time first
   and place null published times last.
5. Run targeted crawler and backend tests.
6. Repair `data/crawler.sqlite3` for post `45217` by re-parsing the live page
   into the existing local database.
7. Requeue failed frontier rows at crawl startup so each refresh retries prior
   failures even when the requested listing pages do not rediscover them.

## Decisions

- Treat a completely sparse detail parse as a failed crawl attempt, not a valid
  empty post. Legitimate image-only posts still have body HTML, and legitimate
  listing-only zero-byte records are still saved through the listing path.
- Do not use crawler time as a primary recency fallback in the inspector.
  Source publication time should determine list order; undated records belong
  after dated records.
- Requeue failed frontier rows at the start of every crawl by resetting their
  attempts to zero. This gives each refresh a fresh retry budget while keeping
  intra-refresh retries bounded by `MAX_FRONTIER_ATTEMPTS`.

## Validation

- `env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python just test-crawler`
- `env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python just test-backend`
- SQLite spot check for `post_id='45217'` after local repair.

## Progress

- Created active exec-plan as first tracked implementation artifact.
- Updated crawler and inspector stable docs with sparse-detail and undated-sort
  behavior notes.
- Added crawler and inspector backend regression tests.
- Patched crawler detail parsing to reject all-null detail records and patched
  inspector ordering to place null `published_at` records after dated records.
- Validation passed: `just test-crawler` with writable uv cache, then
  `just test-backend` with writable uv cache after updating an existing
  old-order assertion.
- Repaired ignored local `data/crawler.sqlite3` row for `45217`: title,
  author, published time, body text/html, and byte count now populate from the
  live page; it no longer appears in the latest-post slice.
- Full validation passed with writable uv cache: `just check`.
- User requested failed frontier rows be retried on every refresh regardless of
  requested listing pages; implementation resumed under this active plan.
- Added failed-frontier reset at crawl startup, exported the DB helper, and
  covered both direct DB reset behavior and spider scheduling without listing
  rediscovery.
- Validation passed: `just test-crawler` with writable uv cache.
- Full validation passed with writable uv cache after import-order fix:
  `just check`.
