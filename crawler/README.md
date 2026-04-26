# Crawler

Scrapy crawler and SQLite export package for Wenxuecity `财富智汇`.

Start with [docs/index.md](docs/index.md) for crawler behavior, parameters, and local checks.

From the repository root, prefer:

```bash
uv run wxc crawl --pages 3
uv run wxc export --shape reddit --format json --out data/exports/cfzh-posts.json
```

Low-level Scrapy debugging is still available from this directory:

```bash
uv run scrapy crawl cfzh -a pages=1 -a max_requests=3
```
