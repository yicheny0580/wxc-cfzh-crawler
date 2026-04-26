# Quality

## Required Checks

- Crawler tests: `uv run --project crawler pytest crawler/tests`
- Inspector backend tests: `uv run --project inspector/backend pytest inspector/backend/tests`
- Frontend build: `npm --prefix inspector/frontend run build`
- Python lint: `uv run ruff check .`

## Documentation Checks

Crawler tests include a lightweight docs-structure check. It verifies that the root and subproject map files exist and that relative links in those map files point to real files.

Update the relevant docs index when adding:

- a new top-level command
- a new subproject or subsystem
- a new runtime path or environment variable
- a new durable operating assumption

## Code Expectations

- Keep public behavior discoverable through `wxc --help`.
- Prefer standard CLI flags over framework-specific argument syntax for user workflows.
- Keep data writes inside root `data/` by default.
- Keep inspector database access read-only.
