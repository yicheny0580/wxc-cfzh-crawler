# Code Unit Design

Code units should be small enough that future agents can inspect, modify, and
test them without loading unrelated behavior. Prefer explicit boundaries over
large files that mix parsing, storage, transport, and UI concerns.

## Python Units

- Keep domain modules focused on one responsibility: parsing, model shape,
  database connection, database reads/writes, progress reporting, subprocess
  control, or route wiring.
- Parse and validate external data at package boundaries. Do not let guessed HTML,
  JSON, query parameter, or subprocess shapes leak through the codebase.
- Keep public models and response schemas easy to find. Crawler records live in
  crawler models; inspector API responses live in inspector schemas.
- Split files by responsibility before raising the production file length limit.

## Frontend Units

- Keep API transport, shared types, state hooks, formatting helpers, and visible
  UI components separate.
- Frontend response types should mirror backend schemas intentionally. When a
  backend API shape changes, update frontend types and product/API docs together.
- Components should own presentation and interaction state for a focused
  workflow, not backend parsing or database assumptions.

## Interfaces

- Root `just` recipes are the supported command interface.
- FastAPI routes are the inspector public API.
- SQLite tables are the crawler-to-inspector data interface.
- Export shapes are user-facing data interfaces and require tests when changed.

## Tests

- Parser tests should cover target-site HTML assumptions and nested reply
  behavior.
- Persistence tests should cover inserts, updates, frontier state, and export
  shape.
- Backend tests should cover API filters, detail views, read-only access, and
  refresh-control behavior.
- Frontend changes should at least pass `just ui-build`; add focused tests before
  broadening UI behavior if a test harness is introduced.
- Docs-structure tests should cover source-of-truth map files and links.
