# Execution Plans

Use this directory for checked-in execution records that should be resumable
without external context. Execution plans are important lifecycle artifacts, not
scratch notes and not optional for qualifying work. They record task intent,
progress, implementation decisions, validation, and handoff state for work that
should survive a single turn.

Exec-plans are not the long-term home for durable design choices, ideas,
invariants, product rules, or operating assumptions. Promote those into the
relevant stable doc before completing the plan.

- [active/](active/): plans still being executed.
- [completed/](completed/): plans retained for historical context.
- [template.md](template.md): starting structure for new substantial plans.

Small one-turn changes do not need a checked-in execution plan.

## Lifecycle

- For qualifying work, create or update a plan in `active/` after user
  implementation approval and before stable docs, code, or tests. The active
  plan is the first tracked implementation artifact.
- Use `just exec-plan-new slug=short-name title='Human Title'` to create the
  active plan from [template.md](template.md).
- Keep the plan current with progress, decisions, and known follow-up work while
  it is active.
- Move the plan to `completed/` after implementation, validation, human review,
  and an explicit good-to-commit signal.
- Use `just exec-plan-complete slug=short-name` to move the active plan without
  overwriting an existing completed plan.
- Follow [../design-docs/agent-workflow.md](../design-docs/agent-workflow.md)
  for stable-doc promotion before completing a plan.
- A completed-only plan or a plan created after stable docs, code, or tests were
  already edited is not compliant with the current lifecycle.

## Stable Docs

Plans may contain temporary execution state and decision history. Stable
document placement and promotion rules live in
[../design-docs/agent-workflow.md](../design-docs/agent-workflow.md).

## Slugs

Exec-plan slugs use lowercase letters, numbers, and single hyphens. The slug is
the filename without `.md` and must be unique across both lifecycle directories.
