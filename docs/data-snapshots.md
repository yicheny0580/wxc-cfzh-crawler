# Data Snapshots

Published data snapshots let users bootstrap a local SQLite database without
running a fresh crawl. Snapshots are GitHub Release assets; SQLite databases and
SQLite sidecar files remain ignored runtime data under `data/`.

## Repo Consumption

For a fresh clone, install dependencies and download the latest snapshot only
when `data/crawler.sqlite3` is missing:

```bash
just setup-data
```

To download explicitly:

```bash
just data-download
just data-download force=true
```

`force=true` replaces an existing local database and removes stale
`crawler.sqlite3-wal` and `crawler.sqlite3-shm` sidecars. The downloader fetches
the latest GitHub Release, downloads `crawler-snapshot.json` and
`crawler.sqlite3.gz`, verifies the gzip checksum, decompresses the database,
verifies the SQLite checksum, runs `PRAGMA integrity_check`, and installs the
database at `data/crawler.sqlite3`.

Use `repo=owner/name` to consume snapshots from a fork or another compatible
release source:

```bash
just data-download repo=yicheny0580/wxc-cfzh-crawler
```

## Release Assets

Each published snapshot release contains:

- `crawler.sqlite3.gz`: gzip-compressed SQLite database.
- `crawler-snapshot.json`: manifest describing the snapshot and checksums.

The manifest is the artifact contract for consumers. It includes:

- `published_at`: when the snapshot release was prepared.
- `latest_crawl_at`: latest `crawled_at` value across posts and replies.
- `posts` and `replies`: record counts in the SQLite database.
- `release_tag`: GitHub Release tag for the snapshot.
- `assets.database_gzip`: gzip asset name, byte size, and SHA-256 checksum.
- `assets.database_sqlite`: decompressed SQLite asset name, byte size, and
  SHA-256 checksum.

## Manual Consumption

Manual consumers should download both assets from the latest GitHub Release and
verify them before using the database:

```bash
gh release download --repo yicheny0580/wxc-cfzh-crawler \
  --pattern crawler-snapshot.json \
  --pattern crawler.sqlite3.gz \
  --dir /tmp/wxc-cfzh-snapshot
```

Verify and install the database:

```bash
cd /tmp/wxc-cfzh-snapshot
sha256sum crawler.sqlite3.gz
gzip -dc crawler.sqlite3.gz > crawler.sqlite3
sha256sum crawler.sqlite3
sqlite3 crawler.sqlite3 'PRAGMA integrity_check;'
```

Compare both `sha256sum` outputs with `crawler-snapshot.json`. The integrity
check must print `ok`. After verification, copy the decompressed SQLite file to
the consumer's expected path, such as this repository's `data/crawler.sqlite3`.

## Producer Notes

Maintainers publish snapshots from a machine with a current local database and
an authenticated GitHub CLI:

```bash
just data-snapshot
just data-publish
```

`data-publish` regenerates local snapshot assets under `data/publish/` and
creates a GitHub Release containing `crawler.sqlite3.gz` and
`crawler-snapshot.json`.
