# Crawler

Scrapy crawler and SQLite export package for Wenxuecity `财富智汇`.

Start with [docs/index.md](docs/index.md) for crawler behavior, parameters, and local checks.
For repo-wide invariants, product intent, and target-site references, start from
[../docs/index.md](../docs/index.md).

From the repository root, prefer:

```bash
just crawl
just export-reddit
```

Low-level Scrapy debugging is still available:

```bash
SCRAPY_SETTINGS_MODULE=wxc_cfzh_crawler.settings \
  uv run --package wxc-cfzh-crawler scrapy crawl cfzh -a pages=1 -a max_requests=3
```
