# Quality

## Required Checks

- Full local harness: `just check`
- Crawler tests: `just test-crawler`
- Inspector backend tests: `just test-backend`
- Quality tool tests: `just test-root`
- Frontend build: `just ui-build`
- Python lint: `just lint`
- Justfile formatting: `just lint-just`
- Production file length lint: `just lint-lines`

## Documentation Checks

Root tests include a lightweight docs-structure check. It verifies that the root
and subproject map files exist, source-of-truth docs are present, and relative
links in those docs point to real files.

The docs checks follow an almost-strict harness style: they enforce the core map
files, exec-plan lifecycle directories, exec-plan helper documentation, and link
integrity without turning docs into a heavy template system.

Root tests also cover the exec-plan helper script so active-plan creation and
completion reject unsafe slugs, missing active plans, and accidental overwrites.
Workflow docs checks require the active exec-plan to be documented as the first
tracked implementation artifact for qualifying work.

Update the relevant docs index when adding:

- a new top-level command
- a new subproject or subsystem
- a new runtime path or environment variable
- a new durable operating assumption
- a product workflow or product design assumption
- a target-site reference or parsing assumption

Agent planning, checked-in execution-plan lifecycle, stable-doc promotion, and
commit rules live in [design-docs/agent-workflow.md](design-docs/agent-workflow.md).
Doc-first implementation rules live in
[design-docs/project-invariants.md](design-docs/project-invariants.md).

## Code Expectations

- Keep public behavior discoverable through `just list`.
- Prefer named `just` recipe parameters over framework-specific argument syntax for user workflows.
- Keep data writes inside root `data/` by default.
- Keep inspector database access read-only.
- Keep production code files at or below 400 physical lines. Split oversized files by
  responsibility instead of raising the cap.
