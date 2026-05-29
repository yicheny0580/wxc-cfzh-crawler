# Frontend Preference Actions In Place

## Goal

Keep inspector result lists stable when the user favorites or hides a post from
the list or reader. Favorite toggles should only update favorite UI state. Hide
actions in Focus view should remove the affected root thread rows from the
current list locally without resetting pagination, scroll, or selection.

## Context

- Source behavior lives in `inspector/frontend/src/App.tsx`,
  `inspector/frontend/src/Results.tsx`, and
  `inspector/frontend/src/usePostPreferences.ts`.
- Durable product behavior is documented in
  `docs/product-specs/crawler-inspector-workflows.md` and
  `inspector/docs/index.md`.
- Known unrelated dirty files before this work:
  `docs/product-specs/crawler-inspector-workflows.md`,
  `inspector/docs/index.md`, `inspector/frontend/src/bodyHtml.ts`,
  `inspector/frontend/src/index.css`, and
  `docs/exec-plans/active/20260511-post-body-export-cleanup.md`.
- This active plan was created as the first tracked implementation artifact
  after implementation approval.

## Plan

- Promote the in-place preference-action behavior into the stable inspector and
  product docs.
- Keep backend result fetching tied to explicit list filters, pagination,
  search, crawl refresh, and result type/date/author changes.
- Derive the displayed current page locally from the last backend result
  snapshot plus browser-local favorite/not-interested state.
- Preserve selected result/detail state when local preference filtering removes
  the selected row from the sidebar.
- Run the focused frontend build validation and inspect the resulting diff.

## Decisions

- User chose hide behavior as "remove row locally" rather than keeping the row
  visibly marked in Focus view.
- Do not auto-fill removed current-page rows from later backend pages; the next
  explicit query/page/filter change will fetch with the latest stored
  preferences.
- Keep existing localStorage keys and cross-clearing behavior: hiding clears a
  favorite mark and favoriting clears a not-interested mark for the same post.

## Validation

- Run `just ui-build`.
- Manual acceptance targets: favorite toggle has no loading/reset; hide in
  Focus removes visible rows for the root thread locally; Show all toggles the
  hidden state in place; Favorites removes an unfavorited row locally; later
  explicit list queries use latest preference filters.

## Progress

- 2026-05-29: Created active exec-plan after implementation approval.
- 2026-05-29: Promoted in-place preference-action behavior to stable docs.
- 2026-05-29: Implemented local current-page preference filtering and removed
  preference ID list changes from backend result reload triggers.
- 2026-05-29: `just ui-build` passed.
- 2026-05-29: Reviewed diff and left unrelated pre-existing dirty files
  untouched.
- 2026-05-29: Received explicit good-to-commit approval.
