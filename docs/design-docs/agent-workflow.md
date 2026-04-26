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
- The plan must make an explicit exec-plan gate decision: either name the
  intended active exec-plan slug for qualifying work, or state why the change is
  small enough to skip a checked-in plan.
- Do not implement the plan until the user approves implementation.
- Approval to implement is not approval to commit. Phrases such as `implement
  the plan`, `apply the plan`, or `go ahead` authorize implementation and
  validation only unless they explicitly include good-to-commit.
- Purely read-only investigation and validation may happen before approval when
  needed to make the plan accurate.

## Required Order

For qualifying work, follow this order:

1. Plan conversation.
2. User implementation approval.
3. Create or update the active exec-plan as the first tracked implementation
   artifact.
4. Update stable docs, code, or tests.
5. Run validation.
6. Stop for human review.
7. Receive an explicit good-to-commit signal.
8. Complete the exec-plan and commit the approved changes.

The active exec-plan is mandatory execution and resume state for qualifying
work, not a stable-doc replacement. For qualifying work, creating it after
stable docs, code, or tests have changed is noncompliant even if the plan is
completed before commit.

## Implementation Flow

- Follow the doc-first workflow after the active exec-plan exists: update
  affected source-of-truth docs before code, then revise docs again if
  implementation changes the final design.
- Prefer root `just` recipes for validation and user-facing workflows. Start
  with `just list` when command shape is unclear.
- Use the smallest validation command that covers the change while developing.
  Use `just check` before handing off broad or cross-domain work.
- Keep local runtime outputs under ignored `data/` unless a task explicitly
  requires another path.
- After implementation and validation, stop for human review. Report changed
  files, validation results, and any known unrelated dirty files.

## Execution Plans

- Create an active plan under `docs/exec-plans/active/` before substantial,
  multi-step, corrective, handoff-prone, or workflow-policy work that needs
  checked-in, resumable task state.
- For qualifying work, the active exec-plan must be the first tracked
  implementation artifact after implementation approval, before stable docs,
  code, or tests.
- Prefer the harness helper when creating the active plan:
  `just exec-plan-new slug=short-name title='Human Title'`.
- If a task starts small but grows into that shape, stop and create or update
  the active exec-plan before continuing implementation.
- Use [../exec-plans/index.md](../exec-plans/index.md) for the exec-plan
  lifecycle and template.
- Keep active plans current with progress, decisions, validation, and known
  follow-up work.
- Plans may hold temporary task state and execution decisions, but durable
  discoveries must move into persistent docs before the plan is completed.
- Promote long-term ideas, design choices, durable invariants, product rules,
  command behavior, runtime paths, target-site assumptions, workflow
  expectations, and quality policy into the relevant stable doc.
- Move completed plans from `docs/exec-plans/active/` to
  `docs/exec-plans/completed/` only after implementation, validation, and stable
  doc promotion are done.
- Prefer `just exec-plan-complete slug=short-name` for the move so the helper
  refuses missing active plans or completed-plan overwrites.

## Commit Flow

- Do not stage or commit implementation changes until the user has reviewed the
  completed work and given an explicit good-to-commit signal.
- A good-to-commit signal must happen after implementation review. It authorizes
  staging agent-owned files, verifying the staged diff, and committing.
- Stage only files changed for the approved plan. Leave pre-existing unrelated
  dirty files unstaged.
- Inspect staged changes before committing so the commit contains only the
  approved scope.
- If validation cannot run or fails for reasons outside the approved change,
  report the blocker instead of committing.
