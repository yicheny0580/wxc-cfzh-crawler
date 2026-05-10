# Manual All-Pages Refresh

## Goal

Add a manual-only refresh mode that fetches every current CFZH listing page by
auto-detecting the forum page count from the first listing response. Existing
numeric refresh remains the default, scheduled refresh stays bounded by its
configured page count, and public browser refresh remains read-only.

## Context

- Stable docs: `docs/product-specs/crawler-inspector-workflows.md`,
  `docs/operations.md`, `docs/deployment.md`, `crawler/docs/index.md`, and
  `inspector/docs/index.md`.
- Code paths: `crawler/src/wxc_cfzh_crawler/spiders/cfzh.py`,
  `crawler/src/wxc_cfzh_crawler/parsing.py`,
  `crawler/src/wxc_cfzh_crawler/admin_cli.py`, inspector crawl API/backend, and
  `inspector/frontend/src/CrawlControls.tsx`.
- Tests: crawler parser/spider/admin tests and inspector backend API tests.
- `git status --short` before implementation: none.
- This active plan was created as the first tracked implementation artifact
  after user approval.

## Plan

- Update stable docs with the all-pages manual refresh contract.
- Add parser support for total-page detection and spider support for
  `pages=all`.
- Extend manual admin/ops refresh commands and local inspector API/UI payloads.
- Add targeted parser, spider, CLI, backend, and frontend build coverage.
- Run targeted validation before handoff.

## Decisions

- All-pages mode is manual-only. Scheduler commands keep requiring numeric
  `--pages`.
- Detection should fail the crawl clearly if the first listing page does not
  expose a total page count, instead of presenting a partial crawl as complete.

## Validation

- `just test-crawler`
- `just test-backend`
- `just ui-build`

## Progress

- 2026-05-10: Created active plan before stable docs, code, or tests.
- 2026-05-10: Updated stable docs for manual all-pages refresh behavior.
- 2026-05-10: Implemented crawler `pages=all`, manual admin/ops support,
  inspector API payloads, and frontend controls.
- 2026-05-10: Added parser, spider, admin CLI, and inspector backend tests.
- 2026-05-10: Validation passed: `just test-crawler`, `just test-backend`
  outside the sandbox after the sandbox hung on an existing image-proxy
  threadpool test, `just ui-build`, `just lint`, and `just lint-just`.
