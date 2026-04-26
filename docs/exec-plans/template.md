# Execution Plan Template

Use this template for substantial work that may need to resume without external
context. Delete sections that do not apply, but keep the plan specific enough to
execute without external context. For qualifying work, create the active plan
after implementation approval and before changing stable docs, code, or tests.

## Goal

Describe the user-visible or repository-visible outcome.

## Context

Link the stable docs, source files, and tests that define the current behavior.
Record known unrelated dirty files from `git status --short`, or state `none`.
State whether this active plan was created as the first tracked implementation
artifact.

## Plan

- Record the implementation steps in execution order.
- Keep durable rules out of this section; follow
  [../design-docs/agent-workflow.md](../design-docs/agent-workflow.md) for
  stable-doc promotion.

## Decisions

- Record decisions that explain why the active plan chose one path over another.

## Validation

- List the targeted checks and acceptance scenarios.

## Progress

- Keep this section current while the plan is active.
- Record active-plan creation as the first tracked implementation artifact,
  major implementation milestones, validation results, stable-doc promotion, and
  completion.
