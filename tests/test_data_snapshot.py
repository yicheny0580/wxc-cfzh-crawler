from __future__ import annotations

import gzip
import hashlib
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))

from data_snapshot import (  # noqa: E402
    DataSnapshotError,
    create_snapshot,
    install_snapshot,
    sha256_file,
)


def write_crawler_db(path: Path, *, with_records: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE posts (
                post_id TEXT PRIMARY KEY,
                crawled_at TEXT NOT NULL
            );
            CREATE TABLE replies (
                reply_id TEXT PRIMARY KEY,
                crawled_at TEXT NOT NULL
            );
            """
        )
        if with_records:
            conn.execute(
                "INSERT INTO posts (post_id, crawled_at) VALUES (?, ?)",
                ("100", "2026-05-09T15:27:08.089709+00:00"),
            )
            conn.execute(
                "INSERT INTO replies (reply_id, crawled_at) VALUES (?, ?)",
                ("101", "2026-05-09T15:30:00+00:00"),
            )


def test_create_snapshot_writes_metadata_and_assets(tmp_path: Path) -> None:
    db_path = tmp_path / "crawler.sqlite3"
    out_dir = tmp_path / "publish"
    write_crawler_db(db_path)

    manifest = create_snapshot(
        db_path=db_path,
        out_dir=out_dir,
        published_at=datetime(2026, 5, 9, 16, 1, 2, tzinfo=UTC),
    )

    assert manifest["published_at"] == "2026-05-09T16:01:02Z"
    assert manifest["latest_crawl_at"] == "2026-05-09T15:30:00Z"
    assert manifest["release_tag"] == "data-published-20260509T160102Z-crawl-20260509T153000Z"
    assert manifest["posts"] == 1
    assert manifest["replies"] == 1
    assert (out_dir / "crawler.sqlite3").is_file()
    assert (out_dir / "crawler.sqlite3.gz").is_file()
    assert json.loads((out_dir / "crawler-snapshot.json").read_text()) == manifest
    assert "Latest crawl at: 2026-05-09T15:30:00Z" in (
        out_dir / "crawler-snapshot-release-notes.md"
    ).read_text()


def test_create_snapshot_requires_crawled_records(tmp_path: Path) -> None:
    db_path = tmp_path / "crawler.sqlite3"
    write_crawler_db(db_path, with_records=False)

    with pytest.raises(DataSnapshotError, match="before any records are crawled"):
        create_snapshot(db_path=db_path, out_dir=tmp_path / "publish")


def test_install_snapshot_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    db_path = tmp_path / "crawler.sqlite3"
    out_dir = tmp_path / "publish"
    target = tmp_path / "data" / "crawler.sqlite3"
    write_crawler_db(db_path)
    create_snapshot(db_path=db_path, out_dir=out_dir)
    target.parent.mkdir()
    target.write_text("existing", encoding="utf-8")

    with pytest.raises(DataSnapshotError, match="already exists"):
        install_snapshot(
            manifest_path=out_dir / "crawler-snapshot.json",
            gzip_path=out_dir / "crawler.sqlite3.gz",
            db_path=target,
        )


def test_install_snapshot_verifies_gzip_checksum(tmp_path: Path) -> None:
    db_path = tmp_path / "crawler.sqlite3"
    out_dir = tmp_path / "publish"
    write_crawler_db(db_path)
    create_snapshot(db_path=db_path, out_dir=out_dir)
    (out_dir / "crawler.sqlite3.gz").write_bytes(b"corrupted")

    with pytest.raises(DataSnapshotError, match="gzip checksum"):
        install_snapshot(
            manifest_path=out_dir / "crawler-snapshot.json",
            gzip_path=out_dir / "crawler.sqlite3.gz",
            db_path=tmp_path / "data" / "crawler.sqlite3",
        )


def test_install_snapshot_checks_sqlite_integrity(tmp_path: Path) -> None:
    payload = b"not a sqlite database"
    gzip_path = tmp_path / "crawler.sqlite3.gz"
    manifest_path = tmp_path / "crawler-snapshot.json"
    with gzip.open(gzip_path, "wb") as handle:
        handle.write(payload)
    manifest_path.write_text(
        json.dumps(
            {
                "assets": {
                    "database_gzip": {"sha256": sha256_file(gzip_path)},
                    "database_sqlite": {"sha256": hashlib.sha256(payload).hexdigest()},
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DataSnapshotError, match="not readable|integrity check failed"):
        install_snapshot(
            manifest_path=manifest_path,
            gzip_path=gzip_path,
            db_path=tmp_path / "data" / "crawler.sqlite3",
        )


def test_install_snapshot_force_replaces_database_and_removes_sidecars(tmp_path: Path) -> None:
    db_path = tmp_path / "crawler.sqlite3"
    out_dir = tmp_path / "publish"
    target = tmp_path / "data" / "crawler.sqlite3"
    write_crawler_db(db_path)
    create_snapshot(db_path=db_path, out_dir=out_dir)
    target.parent.mkdir()
    target.write_text("old", encoding="utf-8")
    target.with_name(target.name + "-wal").write_text("old wal", encoding="utf-8")
    target.with_name(target.name + "-shm").write_text("old shm", encoding="utf-8")

    install_snapshot(
        manifest_path=out_dir / "crawler-snapshot.json",
        gzip_path=out_dir / "crawler.sqlite3.gz",
        db_path=target,
        force=True,
    )

    with sqlite3.connect(target) as conn:
        assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 1
    assert not target.with_name(target.name + "-wal").exists()
    assert not target.with_name(target.name + "-shm").exists()
