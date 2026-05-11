# Add Hide Confirmation

## Goal

Add an in-app confirmation step before the inspector marks a post as hidden/not
interested. Undo remains immediate.

## Context

- Current hide state is managed in `inspector/frontend/src/App.tsx` and
  persisted by `inspector/frontend/src/notInterestedPosts.ts`.
- Hide controls are exposed through `inspector/frontend/src/Results.tsx`,
  `inspector/frontend/src/ResultSidebar.tsx`, and
  `inspector/frontend/src/Reader.tsx`.
- `git status --short` was clean before implementation.
- This active plan was created as the first tracked implementation artifact.

## Plan

- Replace the blind hide toggle callback with an explicit hide-state request
  from the row and reader controls.
- Add a small app-level confirmation dialog shown only before applying a hide.
- Keep undo as a one-click state change.
- Persist confirmed hide and undo changes through the existing localStorage
  helper.

## Decisions

- The user chose an app dialog rather than a browser confirm.
- The user chose confirmation for Hide only, not Undo.
- No stable docs need promotion because this is a narrow UI behavior correction
  with no public API or command surface change.

## Validation

- Run `just ui-build`.
- Run `git diff --check`.
- Manually inspect the diff for the hide/undo behavior contract.

## Progress

- 2026-05-11: Active plan created before code or test changes.
- 2026-05-11: Added the app-level hide confirmation dialog and explicit
  hide-state callbacks for result rows and reader header actions.
- 2026-05-11: Validation passed with `just ui-build` and `git diff --check`.
  Checked untracked new files for trailing whitespace with `rg`.
