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

Update the relevant docs index when adding:

- a new top-level command
- a new subproject or subsystem
- a new runtime path or environment variable
- a new durable operating assumption
- a product workflow or product design assumption
- a target-site reference or parsing assumption

Meaningful implementation starts by opening the relevant source-of-truth doc. If
the change affects behavior, commands, APIs, runtime paths, workflows, product
intent, target-site assumptions, or durable invariants, update docs first,
implement second, then revise docs if implementation changes the final design.
Purely mechanical changes may leave docs untouched only after confirming the
existing docs already describe the intended behavior.

## Code Expectations

- Keep public behavior discoverable through `just list`.
- Prefer named `just` recipe parameters over framework-specific argument syntax for user workflows.
- Keep data writes inside root `data/` by default.
- Keep inspector database access read-only.
- Keep production code files at or below 400 physical lines. Split oversized files by
  responsibility instead of raising the cap.
