# GitHub SQLite Snapshot Publishing And Download

## Goal

Publish `data/crawler.sqlite3` as a GitHub Release snapshot without committing
SQLite data to Git, and give clone users a documented command path to download
the latest snapshot instead of crawling from scratch. Published metadata must
include the release publication time and the latest crawler timestamp from the
database.

## Context

- Stable docs: `README.md`, `docs/operations.md`,
  `docs/design-docs/harness.md`, and
  `docs/product-specs/crawler-inspector-workflows.md`.
- Current repo rules keep `data/`, `*.sqlite3`, and `*.db` ignored.
- Existing code already computes the latest crawl timestamp from
  `MAX(crawled_at)` across `posts` and `replies` in inspector summary and admin
  status logic.
- Known unrelated dirty files before implementation: none.
- This active plan was created as the first tracked implementation artifact
  after user approval.

## Plan

1. Promote the supported snapshot publish/download workflow into stable docs.
2. Add a root `scripts/data_snapshot.py` helper for snapshot creation,
   publishing through local `gh`, and verified download/install from GitHub
   Releases.
3. Add root `just` recipes for `data-snapshot`, `data-publish`,
   `data-download`, and `setup-data`.
4. Add focused root tests for metadata, overwrite protection, checksum
   validation, and SQLite integrity checks.
5. Run targeted validation, then full `just check`.

## Decisions

- Use GitHub Releases, not tracked Git files or Git LFS, because the local DB is
  large binary runtime output.
- Keep `just setup` dependency-only; add `just setup-data` as the clone
  bootstrap path that downloads the latest snapshot when no local DB exists.
- Publish from a maintainer machine with the local GitHub CLI because the
  authoritative SQLite file lives in ignored local runtime data, not in CI.

## Validation

- `just test-root`
- `just lint-just`
- `just lint`
- `just check`

## Progress

- 2026-05-09: Created active plan as the first tracked implementation artifact.
- 2026-05-09: Promoted snapshot publish/download workflow into stable docs.
- 2026-05-09: Added the root data snapshot helper, just recipes, and focused
  root tests for metadata, checksum, overwrite, and integrity behavior.
- 2026-05-09: Validation passed: `just test-root`, `just lint-just`,
  `just lint`, `just lint-lines`, and full `just check`.
- 2026-05-09: Smoke-tested `just data-snapshot` against the local
  `data/crawler.sqlite3` with output under `/tmp`.
