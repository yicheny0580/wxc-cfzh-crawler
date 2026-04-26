# Execution Plans

Use this directory for durable plans that future agents should be able to resume
without external context. Execution plans are first-class repository knowledge,
not scratch notes, when work is broad enough that progress, decisions, or
handoff state should survive a single turn.

- [active/](active/): plans still being executed.
- [completed/](completed/): plans retained for historical context.
- [template.md](template.md): starting structure for new substantial plans.

Small one-turn changes do not need a checked-in execution plan.

## Lifecycle

- Create a plan in `active/` before substantial multi-step implementation.
- Keep the plan current with progress, decisions, and known follow-up work while
  it is active.
- Move the plan to `completed/` when the implementation and validation are done.
- If a plan discovers a durable invariant, product rule, command behavior,
  runtime path, target-site assumption, or workflow expectation, promote that
  knowledge into the relevant stable doc before completing the plan.

## Stable Docs

Plans may contain temporary task state and decision history. Persistent ideas do
not stay only in plans: use design docs for invariants and engineering rules,
product specs for intended workflows, references for target-site facts,
operations for commands, quality for checks, and package docs for local source
maps and package behavior.
