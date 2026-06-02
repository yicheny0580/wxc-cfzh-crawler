# Post Body Export Cleanup

## Goal

Fix post image export artifacts for table-heavy post bodies, especially post
`79519`, and remove copied hidden application chrome from rendered post bodies.
The exported image should keep real post text and tables while avoiding captured
scrollbars or copied hidden modal/tool UI.

## Context

- Stable workflow docs:
  [../../product-specs/crawler-inspector-workflows.md](../../product-specs/crawler-inspector-workflows.md)
  and [../../../inspector/docs/index.md](../../../inspector/docs/index.md).
- Relevant frontend files:
  [../../../inspector/frontend/src/bodyHtml.ts](../../../inspector/frontend/src/bodyHtml.ts),
  [../../../inspector/frontend/src/index.css](../../../inspector/frontend/src/index.css),
  and [../../../inspector/frontend/src/PostImageExport.tsx](../../../inspector/frontend/src/PostImageExport.tsx).
- `git status --short` before this plan was created: clean.
- This active plan was created as the first tracked implementation artifact
  after implementation approval.

## Plan

- Promote the reader/export cleanup behavior into stable docs.
- Update body HTML sanitization to drop explicitly hidden copied UI fragments
  before hidden attributes/classes/styles are stripped.
- Add export-card-only table styling so static image exports wrap table cells
  and do not capture table scrollbars.
- Validate with the frontend build, line-length checks, and a browser spot check
  against post `79519`.

## Decisions

- Keep live reader table scrolling unchanged; the scrollbar bug is in static
  image export.
- Apply hidden copied UI cleanup to normal reader rendering and export rendering,
  because both paths share the same sanitized post body.
- Do not remove nodes only because they have zero height or overflow clipping;
  post `79519` contains real copied content in zero-height wrappers.

## Validation

- `just ui-build`
- `just lint-lines`
- Browser check on local inspector:
  - Open post `79519`.
  - Confirm copied hidden modal/app chrome is absent.
  - Confirm real text and both tables remain.
  - Trigger post image export and confirm no table scrollbar appears.
- `just check` if targeted validation passes and runtime permits.

## Progress

- 2026-05-11: Created active plan as the first tracked implementation artifact.
- 2026-05-11: Promoted hidden copied chrome cleanup and export table behavior
  into stable docs.
- 2026-05-11: Updated frontend sanitization to drop explicitly hidden copied
  fragments and added export-only static table styles.
- 2026-05-11: Validation passed: `just ui-build` and `git diff --check`.
- 2026-05-11: `just lint-lines` was blocked in the sandbox by uv cache access;
  rerunning with escalation reached the lint and failed on pre-existing
  `crawler/src/wxc_cfzh_crawler/spiders/cfzh.py` at 411 lines. Changed frontend
  files are below the 400-line cap.
- 2026-05-11: Browser validation on the local inspector for post `79519`
  confirmed copied hidden chrome is absent, real text and two tables remain,
  export-card tables have no horizontal overflow, and Download reports
  `Downloaded.`.
