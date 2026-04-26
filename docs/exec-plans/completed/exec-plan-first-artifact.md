# Exec-Plan First Artifact Cleanup

## Goal

Make the repository's agent-workflow notes consistently say that qualifying
work creates an active exec-plan immediately after implementation approval and
before any other tracked stable-doc, code, or test edit.

## Context

- [../../design-docs/agent-workflow.md](../../design-docs/agent-workflow.md)
  is the canonical workflow source of truth.
- [../index.md](../index.md) defines the checked-in exec-plan lifecycle.
- [../../design-docs/project-invariants.md](../../design-docs/project-invariants.md)
  defines doc-first behavior and stable-doc ownership.
- [../../quality.md](../../quality.md) defines docs-structure checks.
- [../../../tests/test_docs_structure.py](../../../tests/test_docs_structure.py)
  enforces workflow documentation guardrails.
- Current unrelated dirty files: none. The active exec-plan was created as the
  first tracked implementation artifact before these content edits.

## Plan

- Update the canonical workflow order in `agent-workflow.md`.
- Clean up related workflow notes in root maps, harness, operations, quality,
  project-invariant, exec-plan, and historical completed-plan docs so they point
  to the same lifecycle.
- Extend docs-structure tests for the first-artifact lifecycle language and
  centralized workflow references.
- Run targeted and full validation.
- Leave this exec-plan active for human review. Complete it after an explicit
  good-to-commit signal and before committing the approved changes.

## Decisions

- Keep this pass docs-only plus tests; no helper behavior or command surface
  changes.
- Treat the checked-in exec-plan as lifecycle state. Stable docs still carry
  durable project rules after the active plan exists.
- Preserve completed exec-plans as historical records, but add supersession
  notes where their old wording could be mistaken for current policy.

## Validation

- `just test-root`
- `just lint-just`
- `just lint`
- `git diff --check`
- `just check`

## Progress

- Active exec-plan created with `just exec-plan-new` as the first tracked
  implementation artifact after approval.
- Canonical first-artifact lifecycle added to the agent workflow and related
  workflow notes.
- Completed historical workflow plans updated with supersession notes so they
  do not read as current policy.
- Docs-structure tests now assert the canonical order and first-artifact
  lifecycle wording.
- `just test-root` passed after rerunning outside the sandbox for `uv` cache
  access.
- `just lint-just` passed.
- `just lint` passed outside the sandbox for `uv` cache access.
- `git diff --check` passed.
- `just check` passed outside the sandbox for `uv` and `npm` cache access.
- Active plan remains in `docs/exec-plans/active/` pending human review and an
  explicit good-to-commit signal.
