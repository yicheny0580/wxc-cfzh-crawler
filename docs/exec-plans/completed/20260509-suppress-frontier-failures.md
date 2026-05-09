# Suppress Persistent Frontier Failures

## Goal

Stop one permanently failing upstream detail URL from making every successful
refresh look like it still has an actionable failure, while preserving retries
for transient target-site failures.

## Context

- Stable docs read: [agent-workflow.md](../../design-docs/agent-workflow.md),
  [exec-plans/index.md](../index.md),
  [crawler/docs/index.md](../../../crawler/docs/index.md),
  [operations.md](../../operations.md), and
  [crawler-inspector-workflows.md](../../product-specs/crawler-inspector-workflows.md).
- Live diagnosis: refresh job succeeds, but `post_id=31998` remains failed
  because `https://bbs.wenxuecity.com/cfzh/31998.html` returns HTTP 500.
- Source files in scope: crawler frontier/progress storage, crawler spider
  scheduling, inspector crawl status API schema, and crawl status UI.
- Tests in scope: crawler DB/spider/progress tests, inspector backend crawl
  status tests, and frontend build.
- Known unrelated dirty files before tracked edits: none.
- This active plan was created as the first tracked implementation artifact
  after approval.

## Plan

1. Update stable docs for suppressed frontier failures and progress display.
2. Add nullable `frontier.suppressed_at` migration/init support.
3. Change failed-frontier reset to retry only unsuppressed rows below the
   configured suppression threshold.
4. Preserve failed attempts across refreshes; clear attempts and suppression on
   successful detail fetches or reopened listing-discovered work.
5. Expose separate suppressed counts through crawler progress and inspector
   status, and show a `Suppressed` metric in the refresh popover.
6. Add/update crawler, inspector, and frontend validation coverage.

## Decisions

- Suppress after 5 failed refresh attempts.
- Keep suppressed rows in `status='failed'` with `suppressed_at` set instead of
  adding a new status value.
- Do not manually suppress the current `31998` row; let it reach the threshold
  under the new counted-attempt policy.
- Show suppressed counts separately in the inspector so normal failure count is
  actionable without hiding historical failures from operators.

## Validation

- `just test-crawler`
- `just test-backend`
- `just ui-build`
- `just check`

## Progress

- Created active exec-plan as the first tracked implementation artifact.
- Promoted suppression behavior to crawler, operations, product, and inspector
  stable docs.
- Added crawler frontier suppression storage/policy and surfaced suppressed
  progress counts through the inspector status API and UI.
- Added regression coverage for suppression, retry counting, listing-metadata
  reopening, progress formatting, and inspector status compatibility.
- Validation passed: `just test-crawler`, `just test-backend` outside the
  sandbox after the sandboxed backend run hung in an existing threadpool image
  proxy test, `just ui-build`, and full `just check` outside the sandbox.
