# Agent Workflow Review Gate

## Goal

Clarify the repository agent workflow so meaningful implementation starts with a
draft plan, substantial or corrective multi-step work gets an active exec-plan,
implementation approval stays separate from commit approval, and commits happen
only after human review plus an explicit good-to-commit signal.

## Context

- [../../design-docs/agent-workflow.md](../../design-docs/agent-workflow.md)
  is the centralized agent workflow source of truth.
- [../index.md](../index.md) defines when checked-in execution plans are used.
- [../../design-docs/project-invariants.md](../../design-docs/project-invariants.md)
  defines the repo doc-first workflow.
- [../../../tests/test_docs_structure.py](../../../tests/test_docs_structure.py)
  enforces docs map, link, and workflow guardrails.
- Commit `b884b21` already centralized the agent workflow and remains in
  history. This plan records the follow-up correction after the commit gate was
  applied too broadly.
- Existing unrelated dirty files are out of scope:
  `docs/product-specs/crawler-inspector-workflows.md`,
  `inspector/frontend/src/App.tsx`, and
  `inspector/frontend/src/ResizableInspectorLayout.tsx`.

## Plan

- Create this active exec-plan before further workflow repair.
- Update the agent workflow doc so implementation approval is not commit
  approval and human review is required before good-to-commit.
- Make exec-plan consideration explicit for substantial, multi-step,
  corrective, or handoff-prone work, including tasks that grow after they start.
- Add docs-structure tests for the review-before-commit gate and active
  exec-plan trigger.
- Run `just test-root` and `git diff --check`.
- Stop with changes unstaged for human review.

## Decisions

- Keep `b884b21` in history instead of reverting it.
- Treat `implement the plan`, `apply the plan`, and `go ahead` as
  implementation-only approval unless the user explicitly says
  good-to-commit.
- Keep unrelated dirty files untouched and unstaged.

## Validation

- `just test-root`
- `git diff --check`
- `git status --short` confirms only intended workflow files plus pre-existing
  unrelated dirty files are present.

## Progress

- Created active exec-plan draft.
- Review-before-commit workflow wording was implemented and reviewed.
- Exec-plan trigger wording and docs test coverage are implemented locally.
- `just test-root` passed after rerunning outside the sandbox for `uv` cache
  access.
- `git diff --check` passed.
- Human review completed and explicit good-to-commit was received.
- Plan moved to `docs/exec-plans/completed/` before commit.
