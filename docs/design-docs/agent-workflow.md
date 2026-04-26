# Agent Workflow

This document is the source of truth for Codex and other repository agents.
Keep `AGENTS.md` as a map and keep durable project rules in the stable docs
linked from here.

## Source-First Start

- Start by opening the relevant source-of-truth docs from
  [../index.md](../index.md) and package docs before changing tracked files.
- Use [project-invariants.md](project-invariants.md) for repo-wide rules,
  [harness.md](harness.md) for command and validation flows, and
  [code-unit-design.md](code-unit-design.md) for implementation boundaries.
- Check the worktree before editing. Existing unrelated changes belong to the
  user or another task and must remain untouched.

## Draft Plan Gate

- For every meaningful implementation, draft a plan before modifying
  repo-tracked files.
- The plan must identify intended docs, code, tests, validation, commit scope,
  and known unrelated dirty files.
- Do not implement the plan until the user gives an explicit good-to-commit
  signal.
- Purely read-only investigation and validation may happen before approval when
  needed to make the plan accurate.

## Implementation Flow

- Follow the doc-first workflow: update affected source-of-truth docs first,
  implement second, and revise docs again if implementation changes the final
  design.
- Prefer root `just` recipes for validation and user-facing workflows. Start
  with `just list` when command shape is unclear.
- Use the smallest validation command that covers the change while developing.
  Use `just check` before handing off broad or cross-domain work.
- Keep local runtime outputs under ignored `data/` unless a task explicitly
  requires another path.

## Execution Plans

- Use [../exec-plans/index.md](../exec-plans/index.md) for substantial work that
  needs checked-in, resumable task state.
- Keep active plans current with progress, decisions, validation, and known
  follow-up work.
- Plans may hold temporary task state, but durable discoveries must move into
  persistent docs before the plan is completed.
- Promote durable invariants, product rules, command behavior, runtime paths,
  target-site assumptions, workflow expectations, and quality policy into the
  relevant stable doc.
- Move completed plans from `docs/exec-plans/active/` to
  `docs/exec-plans/completed/` only after implementation, validation, and stable
  doc promotion are done.

## Commit Flow

- After a good-to-commit signal, finish the approved plan in the same run when
  feasible: implement, validate, stage, and commit.
- Stage only files changed for the approved plan. Leave pre-existing unrelated
  dirty files unstaged.
- Inspect staged changes before committing so the commit contains only the
  approved scope.
- If validation cannot run or fails for reasons outside the approved change,
  report the blocker instead of committing.
