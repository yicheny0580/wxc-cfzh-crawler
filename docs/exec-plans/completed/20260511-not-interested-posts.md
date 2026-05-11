# Not Interested Posts

## Goal

Add a local-first inspector workflow that lets the user mark root posts as not
interested, persist those marks in browser localStorage, and filter result lists
with Focus and Show all modes.

## Context

- Stable workflow docs: `docs/product-specs/crawler-inspector-workflows.md` and
  `inspector/docs/index.md`.
- Frontend entry points: `inspector/frontend/src/App.tsx`,
  `FilterPanel.tsx`, `Results.tsx`, `Reader.tsx`, and localStorage helpers.
- Backend list endpoint: `inspector/backend/app/main.py` and
  `_db_results.py`.
- Tests: `inspector/backend/tests/test_api.py`; frontend has build validation
  only.
- Known unrelated dirty files before implementation: none.
- This active exec-plan was created as the first tracked implementation
  artifact after user approval.

## Plan

- Promote durable product/API behavior to the stable inspector docs.
- Add backend `/api/results` support for repeated `exclude_root_post_id` query
  params so local marks still get accurate Focus-mode pagination.
- Add frontend localStorage helpers for marked root post IDs.
- Add interest filter state and hide/undo controls in the result list and
  reader, with root posts as the marking unit.
- Refactor the result sidebar if needed to keep production files within line
  limits.
- Add backend API coverage and run targeted validation.

## Decisions

- Root post is the unit of interest; marking hides both the post row and reply
  hits from that thread.
- Default filter mode is `Focus` on every fresh page load; the interest filter
  choice is not persisted.
- Marks stay browser-local and are keyed only by source `post_id`.

## Validation

- `just test-backend`
- `just ui-build`
- `just lint-lines`
- Broader `just check` if the final diff grows beyond the planned
  frontend/API/docs scope.

## Progress

- 2026-05-11: Created active exec-plan as first tracked implementation artifact.
- 2026-05-11: Promoted durable workflow/API behavior into stable inspector docs.
- 2026-05-11: Implemented root-post include/exclude filters for `/api/results`
  and added backend coverage.
- 2026-05-11: Implemented localStorage-backed not-interested marks, interest
  filter controls, result-row actions, and reader action.
- 2026-05-11: Refactored inspector header and result sidebar components so
  touched production files stay within the 400-line limit.
- 2026-05-11: Validation: `just test-backend` passed; `just ui-build` passed;
  `just test-root` passed; `git diff --check` passed. `just lint-lines` still
  fails on pre-existing untouched `crawler/src/wxc_cfzh_crawler/spiders/cfzh.py`
  at 411 lines.
- 2026-05-11: Corrected UX terminology and behavior after review: replaced the
  three-way interest filter with Focus/Show all, removed marked-only API support,
  and changed result-row controls to hover/focus Hide/Undo pills.
- 2026-05-11: Re-ran validation after the UX correction: `just test-backend`
  passed; `just ui-build` passed; `just test-root` passed; `git diff --check`
  passed. `just lint-lines` still fails only on the same pre-existing untouched
  crawler spider line count.
- 2026-05-11: Fixed Focus rendering bug by filtering hidden root-post threads
  client-side before rendering and selection, in addition to sending
  `exclude_root_post_id` to the API. Re-ran `just ui-build` and
  `git diff --check`; both passed.
- 2026-05-11: Refined the result-row Hide/Undo affordance so it no longer
  reserves row layout space. The row action now floats over the row on desktop
  hover/focus; selected-post Hide/Undo remains available in the reader.
