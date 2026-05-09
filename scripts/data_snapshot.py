from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_REPO = "yicheny0580/wxc-cfzh-crawler"
DEFAULT_DB = Path("data/crawler.sqlite3")
DEFAULT_OUT = Path("data/publish")
SQLITE_ASSET = "crawler.sqlite3"
GZIP_ASSET = "crawler.sqlite3.gz"
MANIFEST_ASSET = "crawler-snapshot.json"
NOTES_ASSET = "crawler-snapshot-release-notes.md"


class DataSnapshotError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def compact_time(value: str) -> str:
    return parse_time(value).strftime("%Y%m%dT%H%M%SZ")


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_db_summary(db_path: Path) -> dict[str, Any]:
    if not db_path.is_file():
        raise DataSnapshotError(f"SQLite database does not exist: {db_path}")

    uri = f"file:{db_path.expanduser().resolve().as_posix()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as conn:
            posts = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
            replies = conn.execute("SELECT COUNT(*) FROM replies").fetchone()[0]
            latest = conn.execute(
                """
                SELECT MAX(value) FROM (
                    SELECT crawled_at AS value FROM posts
                    UNION ALL
                    SELECT crawled_at AS value FROM replies
                )
                """
            ).fetchone()[0]
    except sqlite3.Error as exc:
        raise DataSnapshotError(f"Could not read SQLite summary: {exc}") from exc

    if latest is None:
        raise DataSnapshotError("Cannot publish a snapshot before any records are crawled.")

    return {
        "posts": int(posts or 0),
        "replies": int(replies or 0),
        "latest_crawl_at": iso_utc(parse_time(str(latest))),
    }

def vacuum_into(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    uri = f"file:{source.expanduser().resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.execute(f"VACUUM main INTO {sql_literal(str(destination))}")


def gzip_file(source: Path, destination: Path) -> None:
    temp = destination.with_name(f".{destination.name}.tmp")
    temp.unlink(missing_ok=True)
    with source.open("rb") as in_file, gzip.open(temp, "wb", compresslevel=9) as out_file:
        shutil.copyfileobj(in_file, out_file)
    os.replace(temp, destination)


def build_manifest(
    *,
    summary: dict[str, Any],
    published_at: datetime,
    sqlite_path: Path,
    gzip_path: Path,
) -> dict[str, Any]:
    published_text = iso_utc(published_at)
    latest_crawl_at = str(summary["latest_crawl_at"])
    release_tag = (
        f"data-published-{compact_time(published_text)}"
        f"-crawl-{compact_time(latest_crawl_at)}"
    )
    return {
        "schema_version": 1,
        "forum": "wenxuecity-cfzh",
        "published_at": published_text,
        "latest_crawl_at": latest_crawl_at,
        "posts": summary["posts"],
        "replies": summary["replies"],
        "release_tag": release_tag,
        "assets": {
            "database_sqlite": {
                "name": SQLITE_ASSET,
                "bytes": sqlite_path.stat().st_size,
                "sha256": sha256_file(sqlite_path),
            },
            "database_gzip": {
                "name": GZIP_ASSET,
                "bytes": gzip_path.stat().st_size,
                "sha256": sha256_file(gzip_path),
            },
        },
    }


def write_release_notes(path: Path, manifest: dict[str, Any]) -> None:
    gzip_asset = manifest["assets"]["database_gzip"]
    path.write_text(
        "\n".join(
            [
                "# Crawler SQLite Snapshot",
                "",
                f"- Published at: {manifest['published_at']}",
                f"- Latest crawl at: {manifest['latest_crawl_at']}",
                f"- Posts: {manifest['posts']}",
                f"- Replies: {manifest['replies']}",
                f"- Asset: {gzip_asset['name']}",
                f"- SHA-256: {gzip_asset['sha256']}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def create_snapshot(
    db_path: Path = DEFAULT_DB,
    out_dir: Path = DEFAULT_OUT,
    *,
    published_at: datetime | None = None,
) -> dict[str, Any]:
    source = db_path.expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = read_db_summary(source)

    sqlite_path = out_dir / SQLITE_ASSET
    gzip_path = out_dir / GZIP_ASSET
    manifest_path = out_dir / MANIFEST_ASSET
    notes_path = out_dir / NOTES_ASSET
    temp_sqlite = out_dir / f".{SQLITE_ASSET}.tmp"

    vacuum_into(source, temp_sqlite)
    os.replace(temp_sqlite, sqlite_path)
    gzip_file(sqlite_path, gzip_path)

    manifest = build_manifest(
        summary=summary,
        published_at=published_at or utc_now(),
        sqlite_path=sqlite_path,
        gzip_path=gzip_path,
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_release_notes(notes_path, manifest)
    return manifest

def asset_sha(manifest: dict[str, Any], key: str) -> str:
    try:
        return str(manifest["assets"][key]["sha256"])
    except KeyError as exc:
        raise DataSnapshotError(f"Manifest is missing assets.{key}.sha256") from exc


def assert_sqlite_integrity(path: Path) -> None:
    try:
        with sqlite3.connect(path) as conn:
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
    except sqlite3.Error as exc:
        raise DataSnapshotError(f"Downloaded SQLite database is not readable: {exc}") from exc
    if result != "ok":
        raise DataSnapshotError(f"Downloaded SQLite integrity check failed: {result}")


def remove_sidecars(db_path: Path) -> None:
    for suffix in ("-wal", "-shm"):
        db_path.with_name(db_path.name + suffix).unlink(missing_ok=True)


def install_snapshot(
    *,
    manifest_path: Path,
    gzip_path: Path,
    db_path: Path = DEFAULT_DB,
    force: bool = False,
) -> dict[str, Any]:
    target = db_path.expanduser()
    if target.exists() and not force:
        raise DataSnapshotError(f"{target} already exists. Re-run with force=true to replace it.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_gzip_sha = asset_sha(manifest, "database_gzip")
    actual_gzip_sha = sha256_file(gzip_path)
    if actual_gzip_sha != expected_gzip_sha:
        raise DataSnapshotError("Downloaded gzip checksum does not match the release manifest.")

    target.parent.mkdir(parents=True, exist_ok=True)
    temp_db = target.with_name(f".{target.name}.download")
    temp_db.unlink(missing_ok=True)
    try:
        with gzip.open(gzip_path, "rb") as in_file, temp_db.open("wb") as out_file:
            shutil.copyfileobj(in_file, out_file)

        expected_sqlite_sha = asset_sha(manifest, "database_sqlite")
        actual_sqlite_sha = sha256_file(temp_db)
        if actual_sqlite_sha != expected_sqlite_sha:
            raise DataSnapshotError(
                "Downloaded SQLite checksum does not match the release manifest."
            )

        assert_sqlite_integrity(temp_db)
        if force:
            remove_sidecars(target)
        os.replace(temp_db, target)
        remove_sidecars(target)
    finally:
        temp_db.unlink(missing_ok=True)
    return manifest


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "wxc-cfzh-crawler-data-snapshot",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def download_url(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers=github_headers())
    with urllib.request.urlopen(request) as response, destination.open("wb") as out_file:
        shutil.copyfileobj(response, out_file)


def read_json_url(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=github_headers())
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def find_release_asset(release: dict[str, Any], name: str) -> str:
    for asset in release.get("assets", []):
        if asset.get("name") == name and asset.get("browser_download_url"):
            return str(asset["browser_download_url"])
    raise DataSnapshotError(f"Latest release does not contain asset {name!r}.")


def download_latest_snapshot(
    *,
    repo: str = DEFAULT_REPO,
    db_path: Path = DEFAULT_DB,
    force: bool = False,
) -> dict[str, Any]:
    target = db_path.expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        raise DataSnapshotError(f"{target} already exists. Re-run with force=true to replace it.")

    release = read_json_url(f"https://api.github.com/repos/{repo}/releases/latest")
    manifest_url = find_release_asset(release, MANIFEST_ASSET)
    gzip_url = find_release_asset(release, GZIP_ASSET)

    with tempfile.TemporaryDirectory(prefix="crawler-snapshot-", dir=target.parent) as tmp:
        tmp_dir = Path(tmp)
        manifest_path = tmp_dir / MANIFEST_ASSET
        gzip_path = tmp_dir / GZIP_ASSET
        download_url(manifest_url, manifest_path)
        download_url(gzip_url, gzip_path)
        return install_snapshot(
            manifest_path=manifest_path,
            gzip_path=gzip_path,
            db_path=target,
            force=force,
        )


def publish_snapshot(
    *,
    db_path: Path = DEFAULT_DB,
    out_dir: Path = DEFAULT_OUT,
    repo: str = DEFAULT_REPO,
) -> dict[str, Any]:
    manifest = create_snapshot(db_path=db_path, out_dir=out_dir)
    gh = shutil.which("gh")
    if gh is None:
        raise DataSnapshotError("GitHub CLI `gh` is required for data-publish.")

    tag = str(manifest["release_tag"])
    title = f"Crawler SQLite snapshot {manifest['latest_crawl_at']}"
    subprocess.run(
        [
            gh,
            "release",
            "create",
            tag,
            str(out_dir / GZIP_ASSET),
            str(out_dir / MANIFEST_ASSET),
            "--repo",
            repo,
            "--title",
            title,
            "--notes-file",
            str(out_dir / NOTES_ASSET),
        ],
        check=True,
    )
    return manifest


def add_common_path_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish and download crawler SQLite snapshots.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot = subparsers.add_parser("snapshot", help="Create local snapshot assets.")
    add_common_path_args(snapshot)

    publish = subparsers.add_parser("publish", help="Create and publish a GitHub Release snapshot.")
    add_common_path_args(publish)
    publish.add_argument("--repo", default=DEFAULT_REPO)

    download = subparsers.add_parser(
        "download",
        help="Download the latest GitHub Release snapshot.",
    )
    download.add_argument("--repo", default=DEFAULT_REPO)
    download.add_argument("--db", type=Path, default=DEFAULT_DB)
    download.add_argument("--force", action="store_true")

    return parser.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        if args.command == "snapshot":
            manifest = create_snapshot(db_path=args.db, out_dir=args.out)
        elif args.command == "publish":
            manifest = publish_snapshot(db_path=args.db, out_dir=args.out, repo=args.repo)
        elif args.command == "download":
            manifest = download_latest_snapshot(repo=args.repo, db_path=args.db, force=args.force)
        else:
            raise DataSnapshotError(f"Unknown command: {args.command}")
    except (DataSnapshotError, subprocess.CalledProcessError, urllib.error.URLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
