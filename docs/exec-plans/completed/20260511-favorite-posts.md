# Favorite Posts

## Goal

Add a browser-local inspector workflow that lets users favorite root posts,
persist those marks in localStorage, and view favorite posts with a dedicated
filter without writing to SQLite.

## Context

- Stable docs: `docs/product-specs/crawler-inspector-workflows.md` and
  `inspector/docs/index.md`.
- Frontend entry points: `inspector/frontend/src/App.tsx`,
  `FilterPanel.tsx`, `Results.tsx`, `Reader.tsx`, and localStorage helpers.
- Backend list endpoint: `inspector/backend/app/main.py`,
  `_db_results.py`, and `_db_helpers.py`.
- Tests: `inspector/backend/tests/test_api.py`; frontend has build validation
  only.
- Known unrelated dirty files before implementation: none.
- This active exec-plan was created as the first tracked implementation
  artifact after user approval.

## Plan

- Promote durable product/API behavior to the stable inspector docs.
- Add backend `/api/results` support for repeated `include_root_post_id` query
  params so local favorite marks get accurate pagination.
- Add frontend localStorage helpers for favorite root post IDs.
- Add favorite filter state, star controls in root post result rows, and a
  reader action for the selected root post.
- Remove any hidden mark when favoriting a post, and remove any favorite mark
  when hiding a post.
- Extract local post preference state from `App.tsx` so touched production
  frontend files stay within the 400-line limit.
- Add backend API coverage and run targeted validation.

## Decisions

- Favorite marks stay browser-local and are keyed by source root `post_id`.
- Favorites apply to root post rows only. Reply rows are not favorite results.
- Favorite view uses the existing result ordering rather than favorite time.
- No SQLite schema changes or writable favorite API routes are included.

## Validation

- `just test-backend`
- `just ui-build`
- `just lint-lines`
- `git diff --check`

## Progress

- 2026-05-11: Created active exec-plan as first tracked implementation artifact.
- 2026-05-11: Promoted durable favorite behavior and `include_root_post_id`
  API behavior into stable docs.
- 2026-05-11: Implemented backend include-root filtering for `/api/results`
  and added API coverage.
- 2026-05-11: Implemented localStorage-backed favorites, favorite filter UI,
  root-post row star controls, and reader favorite action.
- 2026-05-11: Extracted local post preference state and selected-post loading
  from `App.tsx`; touched frontend production files are under 400 lines.
- 2026-05-11: Validation: `just test-backend` passed; `just ui-build`
  passed; `just test-root` passed; `git diff --check` passed. `just
  lint-lines` fails only on pre-existing untouched
  `crawler/src/wxc_cfzh_crawler/spiders/cfzh.py` at 411 lines.
- 2026-05-11: Revised filtering after review so result membership and totals
  are backend-authoritative. Removed client-side result post-filtering and the
  temporary favorite render guard.
- 2026-05-11: Re-ran validation after backend-authoritative filtering change:
  `just test-backend` passed; `just ui-build` passed; `just test-root` passed;
  `git diff --check` passed. `just lint-lines` still fails only on pre-existing
  untouched `crawler/src/wxc_cfzh_crawler/spiders/cfzh.py` at 411 lines.
