# Architecture

The repository is organized around three domains:

- `crawler/`: Scrapy spider, parser, SQLite persistence, export code, and crawler tests.
- `inspector/`: SQLite inspector with FastAPI backend, React frontend, and a controlled
  crawler refresh trigger.
- `data/`: ignored local runtime data, including SQLite databases and exports.
- Docker deployment files at the repository root: production image, Compose
  topology, and manual CI/CD workflow entry points for the personal public
  deployment.

The root is the workspace control plane. It contains thin docs, the root
`pyproject.toml`, the shared `uv.lock`, the canonical `justfile`, and no domain
implementation code.

Root docs are the source of truth for durable cross-domain project knowledge.
Indexes are thin maps that route readers to focused docs rather than repeating
their contents:

- [design-docs/project-invariants.md](design-docs/project-invariants.md): repo-wide rules and doc-first workflow.
- [design-docs/agent-workflow.md](design-docs/agent-workflow.md): canonical agent planning, exec-plan, validation, review, and commit workflow.
- [design-docs/code-unit-design.md](design-docs/code-unit-design.md): implementation unit boundaries.
- [product-specs/index.md](product-specs/index.md): product intent and workflow expectations.
- [references/index.md](references/index.md): external references and target-site examples.
- [exec-plans/index.md](exec-plans/index.md): resumable execution records for substantial work.
- [deployment.md](deployment.md): cloud deployment topology, SSH operations,
  scheduler behavior, and cost guardrails.

Package-local docs remain in `crawler/docs/` and `inspector/docs/`. They should
map package source files, package-specific configuration, local behavior notes,
and checks while linking back to root docs for durable cross-domain rules.

## Workspace

The root `pyproject.toml` defines a `uv` workspace with these members:

- `crawler`
- `inspector/backend`

The root `justfile` is the public command harness. It orchestrates workspace
setup, crawl, export, inspection, tests, linting, and frontend builds by calling
the underlying package tools directly.

## Boundaries

- Crawler code must not import inspector code.
- Inspector query endpoints read the SQLite database in read-only mode. The only inspector
  local-development write path is the crawl refresh control, which starts the crawler package
  as a subprocess. Public deployment mode disables browser-accessible crawl start/stop routes.
- Production crawling is owned by the crawler admin CLI and scheduler service.
  Manual and scheduled refreshes must share one runtime lock so crawls do not overlap.
- Shared local data paths should resolve to root `data/` unless explicitly overridden.
- User-facing workflows should be added to the root `justfile` before adding README-only command recipes.
- Changes to boundaries, package ownership, or public interfaces should follow
  the exec-plan gate when it applies, then update the relevant source-of-truth
  doc before implementation code and revise it if the final design changes.
