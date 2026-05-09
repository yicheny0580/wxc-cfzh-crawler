# Post Image Export

## Goal

Add an inspector reader action that exports the selected root post as an image.
The exported image includes the post title, source metadata, source link, and
post body, including inline post images, while excluding replies.

## Context

- Stable workflow docs:
  [../../product-specs/crawler-inspector-workflows.md](../../product-specs/crawler-inspector-workflows.md)
  and [../../../inspector/docs/index.md](../../../inspector/docs/index.md).
- Relevant frontend files:
  [../../../inspector/frontend/src/Reader.tsx](../../../inspector/frontend/src/Reader.tsx),
  [../../../inspector/frontend/src/BodyContent.tsx](../../../inspector/frontend/src/BodyContent.tsx),
  and [../../../inspector/frontend/src/bodyHtml.ts](../../../inspector/frontend/src/bodyHtml.ts).
- Relevant backend files:
  [../../../inspector/backend/app/main.py](../../../inspector/backend/app/main.py),
  [../../../inspector/backend/app/_db_detail.py](../../../inspector/backend/app/_db_detail.py),
  and [../../../inspector/backend/tests/test_api.py](../../../inspector/backend/tests/test_api.py).
- `git status --short` before this plan was created: clean.
- This active plan was created as the first tracked implementation artifact
  after implementation approval.

## Plan

- Update stable docs with the post-image export workflow and post-scoped image
  proxy API note.
- Add backend helpers and a FastAPI route for post-scoped image proxying.
- Add backend tests for accepted stored images and rejected invalid/unsafe image
  requests.
- Add the frontend `html-to-image` dependency.
- Add a focused frontend export component with download and copy actions.
- Wire the export component into the reader header without including replies.
- Run targeted backend tests, frontend build, line-length validation, and then
  the broader harness if local dependencies permit.

## Decisions

- Use a reader-level action because the selected post detail already contains
  the needed data and matches the user's current inspection workflow.
- Use a hidden fixed-width export card rather than capturing the live reader DOM
  so reply content is excluded and the exported layout is stable.
- Use a post-scoped image proxy because DOM-to-PNG capture needs same-origin
  images to reliably include inline post images.
- Proxy only image URLs found in the selected post's stored body HTML, and block
  local/private targets, so the endpoint does not become a general open proxy.

## Validation

- `just test-backend`
- `just ui-build`
- `just lint-lines`
- `just check` if feasible after targeted checks
- Manual acceptance: download produces a PNG for the selected post, copy works
  where the browser Clipboard API supports image writes, source URL is visible,
  replies are absent, and post inline images render through the proxy.

## Progress

- 2026-05-09: Created active plan as the first tracked implementation artifact.
- 2026-05-09: Promoted workflow/API behavior into stable docs.
- 2026-05-09: Added post-scoped backend image proxy, route tests, and image
  fetch guard tests.
- 2026-05-09: Added reader copy/download image export UI using `html-to-image`
  and a hidden export-only post card.
- 2026-05-09: Ran validation: `just test-backend`, `just ui-build`,
  `just lint-lines`, `just lint`, and `just check` all passed.
- 2026-05-09: Started the final inspector on `http://127.0.0.1:8766` and
  verified in-browser that the export controls render, idle export card count is
  zero, and Download/Copy export a post image through the proxy.
- 2026-05-09: Fixed blank post image exports by overriding the cloned export
  card position during `html-to-image` capture. Verified post `79180` produced
  `/home/yichenyue/Downloads/cfzh-post-79180 (1).png` with non-background
  pixels, then reran `just check` successfully.
- 2026-05-09: Moved the exported post source URL from the card footer into a
  compact source row in the export card header. Reran `just ui-build`
  successfully.
- 2026-05-09: Added a source-link QR code to the export card header using the
  frontend `qrcode` package, verified a new post `79180` PNG export, and reran
  `just check` successfully.
