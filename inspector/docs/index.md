# Inspector Index

The inspector provides a browser UI over the crawler SQLite database. Query
endpoints are read-only; the Refresh control can start and stop a crawler
subprocess against the inspected database in local-development mode. Public
deployment mode disables browser crawl start/stop routes and makes Refresh
reload SQLite-backed read APIs only.

This file is the inspector package map. Durable cross-domain rules live in root
docs; inspector docs should stay focused on inspector source layout,
package-local behavior, API notes, startup, and checks.

## Root Source Of Truth

- [../../docs/design-docs/project-invariants.md](../../docs/design-docs/project-invariants.md): doc-first workflow, data ownership, and crawler/inspector boundaries.
- [../../docs/design-docs/code-unit-design.md](../../docs/design-docs/code-unit-design.md): API, frontend, and module unit expectations.
- [../../docs/product-specs/product-principles.md](../../docs/product-specs/product-principles.md): product goals and UX principles.
- [../../docs/product-specs/crawler-inspector-workflows.md](../../docs/product-specs/crawler-inspector-workflows.md): supported inspect, search, reader, and refresh workflows.

## Source Map

- [../backend/app/main.py](../backend/app/main.py): FastAPI routes and static frontend serving.
- [../backend/app/crawl.py](../backend/app/crawl.py): crawl subprocess control and status.
- [../backend/app/db.py](../backend/app/db.py): read-only SQLite connection and query helpers.
- [../backend/app/schemas.py](../backend/app/schemas.py): API response schemas.
- [../frontend/src/App.tsx](../frontend/src/App.tsx): primary React UI.
- [../frontend/src/api.ts](../frontend/src/api.ts): frontend API client.
- [../backend/pyproject.toml](../backend/pyproject.toml): backend dependencies and tests.
- [../frontend/package.json](../frontend/package.json): frontend scripts and dependencies.

## Startup

From the repository root:

```bash
just inspect
```

Useful options:

```bash
just inspect db=data/crawler.sqlite3
just inspect host=127.0.0.1 port=8765
just inspect-api
```

`just inspect` rebuilds `../frontend`, then serves the UI and API through
FastAPI. Run `just setup` when frontend dependency manifests change.

Set `WXC_INSPECT_PUBLIC=1` for public deployment mode. In that mode, the UI
uses read-only data refresh and the backend disables browser-accessible crawl
start/stop routes.

## Crawl Refresh

Refresh starts a crawler run from the inspector backend with a default of 5
listing pages and a maximum of 600, or with an explicit manual all-pages mode
that detects the current forum page count from the first listing page. The
frontend subscribes to crawl status over WebSocket, so new browser sessions
reflect an already-running backend crawl. Only one crawl runs at a time; Stop
requests graceful process termination and shows `Stopping` until the process
exits. Crawl status reports actionable failed frontier rows separately from
suppressed persistent failures, so repeated upstream 500s do not make an
otherwise successful refresh look failed.

## API

- `GET /api/health`
- `GET /api/crawl/status`
- `POST /api/crawl`
- `POST /api/crawl/stop`
- `WS /api/crawl/ws`
- `GET /api/summary`
- `GET /api/authors`
- `GET /api/results`
- `GET /api/posts`
- `GET /api/posts/{post_id}`
- `GET /api/posts/{post_id}/image`

`GET /api/results` is the primary inspector list endpoint. It supports `search`,
`author`, `published_from`, `published_to`, `published_timezone`,
`include_posts`, `include_replies`, repeated `exclude_root_post_id`, `limit`,
and `offset`. Reply results include root post metadata so the frontend can open
the original post and focus the matching reply in context. The root-post ID
filter exists for the frontend's localStorage-backed not-interested workflow: it
does not persist anything server-side, but it lets the read-only API paginate
accurately in Focus mode after the browser applies local thread preferences.
`published_from` and `published_to` are inclusive `YYYY-MM-DD` filters over
browser-local published dates; the frontend sends the browser IANA timezone in
`published_timezone`. If omitted, the backend defaults to `America/Los_Angeles`.
Undated records are excluded while either bound is active.

Search accepts two-or-more-character terms. Terms of three or more characters
use the SQLite trigram FTS index; exactly two-character terms use a slower
literal substring fallback across title, author, and body text. One-character
terms are rejected to avoid overly broad scans.

`GET /api/posts` supports the same `search`, `author`, `published_from`,
`published_to`, `published_timezone`, `limit`, and `offset` query parameters for
post-only lists.

List endpoints order dated records by source `published_at` descending. Records
without a source publish time sort after dated records instead of using crawl
time as a primary recency fallback.

The source forum publishes timestamps without an offset. Inspector API responses
interpret post and reply `published_at`/`edited_at` values as
`America/Los_Angeles` and return offset-aware ISO strings so the browser can
render them in local time.

Read-only data endpoints open SQLite with `mode=ro` and `PRAGMA query_only = ON`.

Not-interested post marks are browser-local UI preferences saved in
localStorage. The inspector treats the root post as the unit of interest, so a
marked root post and reply hits from that root post are hidden in the default
Focus view. Users can switch the interest filter to Show all to review and undo
hidden threads.

Browser-facing `db_path` values are display labels, not filesystem access
contracts. Local repo databases are shown relative to the repository root, such
as `data/crawler.sqlite3`; external local paths are reduced to their filename;
public mode uses the generic `SQLite database` label.

`GET /api/posts/{post_id}/image?src=...` is a post-scoped image proxy for the
reader's post-image export workflow. It only returns HTTP(S) images whose URL is
present in that post's stored body HTML after normal forum-relative URL
resolution, and it rejects local/private network targets so the route cannot act
as a general open proxy.

In public deployment mode, crawl mutation and WebSocket endpoints are disabled.
Production crawl refresh is managed by SSH/CLI operations documented in
[../../docs/deployment.md](../../docs/deployment.md). Public responses should
not expose absolute local filesystem database paths.

## Checks

```bash
just test-backend
just ui-build
```
