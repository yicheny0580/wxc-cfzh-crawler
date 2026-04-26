# Project Invariants

These rules are durable project constraints. When code and docs disagree, treat
this document and the linked source-of-truth docs as the intended design. Change
the docs first when intentionally changing the design, then implement, then
revise the docs again if implementation exposes a better or more accurate
design.

## Doc-First Workflow

- Start every meaningful implementation task by opening the relevant docs from
  [../index.md](../index.md).
- If the change affects behavior, commands, public APIs, runtime paths, product
  intent, target-site assumptions, workflows, or durable operating assumptions,
  update the relevant source-of-truth doc before changing implementation.
- Implement against the documented intent, not against an unstated plan.
- After implementation, revise the docs if the implementation revealed a
  necessary correction, constraint, or sharper wording.
- Purely mechanical changes may leave docs unchanged only after confirming the
  existing docs already describe the intended behavior.
- Keep `AGENTS.md` and `README.md` as maps. Do not turn either file into the
  repository manual.
- Prefer small focused docs over one large handbook. Add a new source-of-truth
  page only when an existing page would become ambiguous or overloaded.
- Capture repeated review feedback as docs or tooling so future maintainers can
  reuse the decision.
- Keep durable cross-domain knowledge in root `docs/`: invariants, product
  intent, architecture, command behavior, quality policy, references, and
  workflow expectations.
- Keep child docs under `crawler/docs/` and `inspector/docs/` as package-local
  maps and package behavior notes. Link back to root docs instead of duplicating
  cross-domain rules.
- Agent planning, checked-in execution-plan lifecycle, and stable-doc promotion
  rules live in [agent-workflow.md](agent-workflow.md).

## Repository Boundaries

- Keep domain implementation code inside `crawler/` or `inspector/`.
- Keep root files focused on workspace control: docs, `pyproject.toml`, `uv.lock`,
  `justfile`, shared quality scripts, and root tests.
- Keep local runtime outputs under ignored `data/` by default.
- User-facing workflows belong in the root `justfile` before they are advertised
  in README or domain docs.

## Domain Boundaries

- Crawler code owns Scrapy crawling, HTML parsing, SQLite persistence, frontier
  state, and export shapes.
- Inspector code owns read-only SQLite inspection, FastAPI routes, React UI, and
  the controlled crawl refresh trigger.
- Crawler code must not import inspector code.
- Inspector query endpoints must open SQLite read-only. The only inspector write
  path is the refresh control that starts the crawler subprocess against the
  inspected database.

## Data And Target Site

- Default data writes resolve to root `data/` unless a caller explicitly
  overrides the path.
- Stored records are organized by post and reply identity, not listing page
  number.
- Listing pages are discovery feeds. Root posts and replies may discover more
  nested reply links while a crawl is running.
- Target-site assumptions and sample URLs live in
  [../references/wenxuecity-cfzh.md](../references/wenxuecity-cfzh.md).

## Quality Invariants

- `just check` is the full local validation harness.
- Production source files stay at or below 400 physical lines unless the quality
  rule is intentionally changed in [../quality.md](../quality.md) and tooling.
- Prefer explicit boundary validation or typed schemas over guessed data shapes.
- Add or update tests when changing parser behavior, persistence behavior, API
  response shape, frontend data flow, command behavior, or docs structure.
