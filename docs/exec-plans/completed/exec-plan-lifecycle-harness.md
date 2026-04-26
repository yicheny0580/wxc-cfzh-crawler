# Exec-Plan Lifecycle Harness

## Goal

Make exec-plan handling explicit enough that agents cannot treat it as optional
guidance for substantial, corrective, handoff-prone, or workflow-policy work.

## Context

- [../../design-docs/agent-workflow.md](../../design-docs/agent-workflow.md)
  is the centralized agent workflow source of truth.
- [../index.md](../index.md) defines the checked-in exec-plan lifecycle.
- [../../design-docs/harness.md](../../design-docs/harness.md) defines root
  command harness expectations.
- [../../quality.md](../../quality.md) defines docs and root validation checks.
- [../../../tests/test_docs_structure.py](../../../tests/test_docs_structure.py)
  enforces docs map and workflow guardrails.
- Current unrelated dirty files: none.

## Plan

- Create this active exec-plan before implementation edits.
- Add `just exec-plan-new slug=... title=...` and
  `just exec-plan-complete slug=...` as lightweight harness commands.
- Back the commands with a root script that validates slugs, creates active
  plans from the template, and moves active plans to completed without
  overwriting existing files.
- Strengthen agent workflow, exec-plan, harness, quality, and agent map docs so
  qualifying work has an explicit exec-plan gate and lifecycle.
- Add tests for the helper and expanded docs-structure assertions.
- Run targeted validation and update this plan before handoff.

## Decisions

- Use docs plus a helper command rather than a heuristic validation failure for
  missing exec-plans.
- Keep command names in the root `justfile` so agents discover them through
  `just list`.
- Keep the helper local to root quality tooling; crawler and inspector runtime
  behavior stays unchanged.

## Validation

- `just test-root`
- `just lint-just`
- `just lint`
- `git diff --check`

## Progress

- Active exec-plan created before implementation edits.
- Added the exec-plan helper script, root `just` recipes, and root tests.
- Updated agent workflow, exec-plan, harness, operations, quality, template, and
  agent map docs with the explicit exec-plan gate and helper lifecycle.
- `just test-root` passed after rerunning outside the sandbox for `uv` cache
  access.
- `just lint-just` passed.
- `just lint` passed after rerunning outside the sandbox for `uv` cache access.
- `git diff --check` passed.
- `just check` passed outside the sandbox for `uv` and `npm` cache access.
