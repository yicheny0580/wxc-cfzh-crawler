# Inspector Two-Character Search Fallback

## Goal

Inspector search accepts exactly two-character terms such as `PE` by using a
literal substring fallback, while one-character terms remain rejected and
three-or-more-character terms continue using the existing SQLite FTS trigram
path.

## Context

- Stable docs: [../../product-specs/crawler-inspector-workflows.md](../../product-specs/crawler-inspector-workflows.md)
  and [../../../inspector/docs/index.md](../../../inspector/docs/index.md).
- Backend search helpers: [../../../inspector/backend/app/_db_helpers.py](../../../inspector/backend/app/_db_helpers.py).
- API tests: [../../../inspector/backend/tests/test_api.py](../../../inspector/backend/tests/test_api.py).
- `git status --short` before implementation approval showed no unrelated dirty
  files.
- This active plan was created as the first tracked implementation artifact
  after approval.

## Plan

- Update inspector docs to describe the two-character fallback.
- Refactor backend search term parsing and filter generation so 1-character
  terms reject, 2-character terms use escaped `LIKE` substring clauses, and
  longer terms use FTS.
- Update API tests for accepted two-character search, rejected one-character
  search, mixed FTS/substr search, and result-type composition.
- Run targeted backend validation.

## Decisions

- Keep the fallback backend-only because the existing search input already
  accepts two-character values.
- Keep one-character search rejected to avoid broad table scans.
- AND-compose terms to preserve current multi-term semantics.

## Validation

- `just test-backend`
- `uv run ruff check inspector/backend/app/_db_helpers.py inspector/backend/app/main.py inspector/backend/tests/test_api.py`

## Progress

- 2026-05-10: Active plan created with
  `just exec-plan-new slug=short-search-fallback title='Inspector Two-Character Search Fallback'`
  as the first tracked implementation artifact.
- 2026-05-10: Inspector docs updated with the two-character substring fallback
  behavior.
- 2026-05-10: Backend helper and API tests updated for two-character search,
  one-character rejection, mixed-term composition, and literal wildcard
  handling.
- 2026-05-10: Validation passed: `just test-backend` (34 passed) and touched-file
  `ruff check`.
