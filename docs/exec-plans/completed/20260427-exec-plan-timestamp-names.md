# Exec-Plan Timestamp Names

Active execution record for changing exec-plan filenames to include a UTC date
prefix.

## Goal

Require new exec-plan filenames to carry a UTC date prefix while keeping the
daily command concise. New plans should be created from a short slug and written
as `YYYYMMDD-short-name.md`; completing a plan should require that full
timestamped slug.

## Context

- Source docs: [../index.md](../index.md),
  [../../design-docs/agent-workflow.md](../../design-docs/agent-workflow.md),
  [../../design-docs/harness.md](../../design-docs/harness.md), and
  [../../operations.md](../../operations.md).
- Helper and tests: `scripts/manage_exec_plan.py` and
  `tests/test_manage_exec_plan.py`.
- Known unrelated dirty files before implementation: none.
- This active plan was created as the first tracked implementation artifact
  after approval, using the pre-change helper with the full timestamped slug.

## Plan

- Update stable docs to say `exec-plan-new` accepts a short slug and prefixes
  the current UTC date, while `exec-plan-complete` accepts the full timestamped
  slug.
- Update the helper to validate short slugs for creation, generate
  `YYYYMMDD-short-name`, validate full timestamped slugs for completion, and
  preserve overwrite protections.
- Update root tests for frozen-date creation, invalid short slugs, strict
  completion, missing active plans, and overwrite protection.

## Decisions

- Timestamp format is UTC date only: `YYYYMMDD`.
- Existing completed plans are historical records and will not be renamed.
- `exec-plan-new` rejects already timestamped input to avoid double-prefixing.
- `exec-plan-complete` requires the exact full timestamped slug rather than
  resolving short names.

## Validation

- Run `uv run pytest tests/test_manage_exec_plan.py tests/test_docs_structure.py`.
- Run `just check` before handoff if targeted validation passes.

## Progress

- Created active exec-plan `20260427-exec-plan-timestamp-names.md` as the first
  tracked implementation artifact.
- Updated helper implementation and root tests.
- Updated workflow, harness, exec-plan, operations, and agent-map docs.
- Targeted validation passed:
  `uv run pytest tests/test_manage_exec_plan.py tests/test_docs_structure.py`.
- Full validation passed: `just check`.
