# Agent Workflow Invariant Alignment

Align the repository's agent workflow notes with three durable documentation
invariants: thin index maps, exec-plans as mandatory execution records, and
focused docs split by domain, responsibility, or layer.

## Goal

Make the workflow docs and structural tests consistently enforce that maps stay
thin, exec-plans preserve resumable execution state without replacing stable
docs, and oversized or overloaded docs are split by responsibility.

## Context

- [../../design-docs/agent-workflow.md](../../design-docs/agent-workflow.md)
  defines the canonical agent lifecycle.
- [../../design-docs/project-invariants.md](../../design-docs/project-invariants.md)
  owns durable doc-first and repository-wide invariants.
- [../index.md](../index.md) defines exec-plan lifecycle expectations.
- [../../quality.md](../../quality.md) and
  [../../../tests/test_docs_structure.py](../../../tests/test_docs_structure.py)
  document and enforce the lightweight docs checks.
- Known unrelated dirty files: none.
- This active plan was created with `just exec-plan-new` as the first tracked
  implementation artifact after implementation approval.

## Plan

- Promote the three invariants into the stable workflow, invariant, exec-plan,
  quality, and map docs without turning map files into manuals.
- Clarify that exec-plans are required for qualifying long-running or resumable
  work, but durable ideas, design choices, rules, and operating assumptions live
  in stable docs before plan completion.
- Add soft docs-structure tests that check map thinness, exec-plan role wording,
  and focused-doc splitting guidance.
- Run targeted root tests, lint, whitespace checks, and the full validation
  harness.

## Decisions

- Use a soft docs-size gate for this pass. Do not add a hard markdown line cap.
- Keep exec-plans mandatory for qualifying work; narrowing their role to
  execution records must not make them feel skippable.
- Keep indexes as navigation surfaces that link to source-of-truth docs instead
  of duplicating the underlying workflow or design rules.

## Validation

- `just test-root`
- `just lint`
- `git diff --check`
- `just check`

## Progress

- Active exec-plan created as the first tracked implementation artifact.
- Stable docs updated so maps stay thin, exec-plans are framed as mandatory
  execution/resume records, and focused docs split by domain, responsibility, or
  layer.
- Soft docs-structure tests added for the three invariants.
- Validation passed: `just test-root`, `just lint`, `git diff --check`, and
  `just check`.
