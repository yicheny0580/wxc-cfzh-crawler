# Crawler And Inspector Workflows

This page defines the supported user workflows. Implementation details live in
domain docs; this page records what the workflows should accomplish.

## Crawl

The user can crawl recent `财富智汇` pages from the repository root:

```bash
just crawl
just crawl-smoke
```

The crawl discovers listing rows, schedules detail pages, saves root posts and
replies, and records frontier state so interrupted work can be retried. Progress
should be visible in an interactive terminal and still leave useful logs when
output is redirected.

## Export

The user can export local records in two supported shapes:

```bash
just export-flat
just export-reddit
```

Flat export is for record-oriented processing. Nested export is for root-post
inspection with replies grouped under their thread.

## Inspect

The user can serve the browser inspector from the repository root:

```bash
just inspect
```

The inspector should show database health, summary counts, authors, searchable
results, post details, nested replies, and source links. Query endpoints should
read SQLite in read-only mode.

Forum-published timestamps should display in the browser's local timezone. The
source forum does not expose an offset in listing or detail timestamps, so the
inspector interprets those forum timestamps as `America/Los_Angeles` before
display and date filtering.

On desktop screens, the inspector should let the user resize the split between
filtered results and the reader with a vertical divider. The selected divider
position should be saved in browser local storage and restored on reload while
keeping narrow screens in the stacked layout. The divider should have a
discoverable grip and a generous pointer target so it is easy to grab without
visually overwhelming the inspector.

## Search And Filter

The user can search across posts and replies, filter by author, filter by
published date, and choose whether posts, replies, or both appear in results.
Reply results should expose root-post metadata so the user can open the original
thread context. Published-date filters should match the browser-local dates the
inspector displays.

## Reader

The reader view should preserve body content, source metadata, nested replies,
and source-page links. It should make forum content easier to inspect locally
without pretending to replace the original forum.

The reader should let the user export the selected root post as an image for
sharing or archiving. The exported image includes the root post title, metadata,
source link with a scannable QR code, and post body, including inline post
images, but does not include replies.

## Refresh

The inspector Refresh control can start a crawler run against the inspected
database. Only one refresh run should execute per backend process. Stop requests
should move the UI into a stopping state until the crawler subprocess exits.
Refresh status should separate actionable failed frontier rows from suppressed
persistent failures so a successful refresh is not presented as failed only
because an upstream detail URL has repeatedly returned an unrecoverable error.

In public deployment mode, browser Refresh is read-only: it refetches the latest
SQLite-backed API data and must not start or stop a crawler. Production crawl
refresh is handled by SSH/CLI operations and by the scheduler service.

## Production Operations

The operator can manage the public deployment from the repository root through
`just ops-*` recipes backed by the in-container `wxc-cfzh-admin` CLI. The
operator can manually refresh, stop a running crawl, pause or resume the
scheduler, inspect status, read logs, and generate a diagnostics report.

Manual and scheduled production crawls share one lock. If a scheduled crawl is
running, manual refresh reports the active crawl instead of starting another. If
manual refresh is running, scheduled ticks skip and retry on the next interval.
