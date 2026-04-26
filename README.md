# wxc-cfzh

Local-first crawler and SQLite inspector for the Wenxuecity `财富智汇` forum.

## Quick Start

```bash
uv tool install rust-just
just setup
just crawl
just inspect
```

Useful smoke crawl:

```bash
just crawl-smoke
```

Export flat root/reply records:

```bash
just export-flat
```

Export root posts with nested replies:

```bash
just export-reddit
```

## Repository Map

- [AGENTS.md](AGENTS.md): short agent entry point and source-of-truth map.
- [justfile](justfile): canonical root command harness for humans and Codex.
- [docs/index.md](docs/index.md): root documentation index.
- [docs/design-docs/index.md](docs/design-docs/index.md): project invariants, harness design, and code unit design.
- [docs/product-specs/index.md](docs/product-specs/index.md): product principles and supported workflows.
- [docs/references/index.md](docs/references/index.md): external references and target-site examples.
- [docs/exec-plans/index.md](docs/exec-plans/index.md): first-class checked-in plans for substantial work.
- [crawler/](crawler/): Scrapy crawler, SQLite persistence, export logic, and crawler tests.
- [crawler/docs/index.md](crawler/docs/index.md): crawler behavior, parameters, and data notes.
- [inspector/](inspector/): FastAPI backend and React frontend for read-only SQLite inspection.
- [inspector/docs/index.md](inspector/docs/index.md): inspector startup, API, frontend, and troubleshooting.
- `data/`: ignored local SQLite databases and exports.

## Common Commands

```bash
just list
just doctor
just check
```

`just` is the root command harness for both humans and Codex. Run `just setup`
after cloning or when `inspector/frontend/package.json` or `package-lock.json`
changes. `just inspect` rebuilds `inspector/frontend`, then serves the UI and API
through FastAPI.

This repo is doc-first. Meaningful implementation starts by opening the relevant
source-of-truth docs under [docs/](docs/index.md). When changing behavior,
commands, APIs, workflows, product intent, or durable assumptions, update docs
first, implement second, then revise docs if implementation changes the final
design.

Low-level Scrapy usage is still available for troubleshooting:

```bash
SCRAPY_SETTINGS_MODULE=wxc_cfzh_crawler.settings \
  uv run --package wxc-cfzh-crawler scrapy crawl cfzh -a pages=1 -a max_requests=3
```

Other supported `just` installation paths are listed in the
[Just Programmer's Manual](https://just.systems/man/en/packages.html).
