# Reader Text Selection

Use this template for substantial work that may need to resume without external
context. Exec-plans are checked-in execution records for qualifying work, not
the long-term home for durable design choices. Delete sections that do not
apply, but keep the plan specific enough to execute without external context.
For qualifying work, create the active plan after implementation approval and
before changing stable docs, code, or tests.

## Goal

Selecting text in the inspector reader's main post body remains stable while
the page receives unrelated crawl-status updates.

## Context

- [../../product-specs/crawler-inspector-workflows.md](../../product-specs/crawler-inspector-workflows.md)
  defines the reader workflow.
- [../../../inspector/frontend/src/Reader.tsx](../../../inspector/frontend/src/Reader.tsx)
  renders the selected post and passes the main body to `BodyContent`.
- [../../../inspector/frontend/src/BodyContent.tsx](../../../inspector/frontend/src/BodyContent.tsx)
  sanitizes and injects post body HTML.
- [../../../inspector/frontend/src/useCrawlStatus.ts](../../../inspector/frontend/src/useCrawlStatus.ts)
  receives status updates that can cause unrelated app re-renders.

Known unrelated dirty files from `git status --short`: none before plan
creation. This active plan was created with `just exec-plan-new` as the first
tracked implementation artifact after user approval.

## Plan

- Keep stable docs unchanged unless implementation reveals a durable reader
  rule beyond the bug fix.
- Update `BodyContent` so unchanged sanitized body HTML is not reinjected into
  the DOM during unrelated React renders.
- Run the frontend build.
- Reproduce the browser selection check against the running inspector.

## Decisions

- The bug was reproduced in the main post body: a programmatic selection inside
  `.reader-body-html` was cleared after a crawl-status websocket tick, and the
  original text node became disconnected while the containing body element
  remained the same.
- The first reply-collapse hypothesis was rejected after the user clarified
  the issue affects the main post body.
- The fix should stay in `BodyContent`, where sanitized HTML is injected, rather
  than changing crawl status behavior or reader layout.

## Validation

- `just ui-build`
- Browser check: create a selection inside the main post body, wait for a
  status tick, and confirm the selected text remains.

## Progress

- Active plan created: 2026-05-09.
- Investigation found the selection-clearing reproduction in the main post body.
- Updated `BodyContent` to memoize the component and its injected HTML payload.
- Validation passed: `just ui-build`.
- Browser validation passed: main post body selection remained after a status
  tick, with the selected text node still connected.
- Stable-doc promotion: none needed; this is an implementation-level rendering
  fix for the existing reader workflow.
