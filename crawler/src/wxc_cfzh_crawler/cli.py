from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from wxc_cfzh_crawler.paths import default_database_url, resolve_repo_root

DEFAULT_START_URL = "https://bbs.wenxuecity.com/cfzh/"
FRONTEND_DEPENDENCY_MANIFESTS = ("package.json", "package-lock.json")
FRONTEND_SYNC_MARKER = ".wxc-inspect-sync.json"


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wxc",
        description="Run the WXC CFZH crawler, exporter, and local SQLite inspector.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    crawl = subparsers.add_parser("crawl", help="Crawl recent CFZH posts into SQLite.")
    crawl.add_argument(
        "--pages",
        type=positive_int,
        default=3,
        help="Recent forum listing pages to scan for frontier discovery. Default: 3.",
    )
    crawl.add_argument(
        "--max-requests",
        type=positive_int,
        default=None,
        help="Optional cap on detail-page requests for smoke runs.",
    )
    crawl.add_argument(
        "--start-url",
        default=DEFAULT_START_URL,
        help=f"Forum URL to crawl. Default: {DEFAULT_START_URL}",
    )
    crawl.add_argument(
        "--database-url",
        default=default_database_url(),
        help="SQLite database URL. Defaults to the root data/crawler.sqlite3 database.",
    )
    crawl.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default=None,
        help="Override Scrapy log level for this run.",
    )
    crawl.set_defaults(func=run_crawl)

    export = subparsers.add_parser("export", help="Export crawled records from SQLite.")
    export.add_argument(
        "--database-url",
        default=default_database_url(),
        help="SQLite database URL. Defaults to the root data/crawler.sqlite3 database.",
    )
    export.add_argument("--out", required=True, help="Output file path.")
    export.add_argument("--format", choices=["json", "jsonl"], default="jsonl")
    export.add_argument("--shape", choices=["reddit", "flat"], default="reddit")
    export.set_defaults(func=run_export)

    inspect = subparsers.add_parser("inspect", help="Serve the read-only SQLite inspector.")
    inspect.add_argument(
        "--db",
        default=None,
        help="SQLite database file to inspect. Defaults to root data/crawler.sqlite3.",
    )
    inspect.add_argument("--host", default="127.0.0.1", help="Bind host. Default: 127.0.0.1.")
    inspect.add_argument(
        "--port",
        type=positive_int,
        default=8765,
        help="Bind port. Default: 8765.",
    )
    inspect.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn reload for backend development.",
    )
    inspect.add_argument(
        "--skip-ui-build",
        action="store_true",
        help="Do not refresh or build inspector/frontend before starting the backend.",
    )
    inspect.set_defaults(func=run_inspect)

    return parser


def run_crawl(args: argparse.Namespace) -> int:
    from scrapy.crawler import CrawlerProcess
    from scrapy.settings import Settings

    import wxc_cfzh_crawler.settings as project_settings
    from wxc_cfzh_crawler.spiders.cfzh import CfzhSpider

    settings = Settings()
    settings.setmodule(project_settings, priority="project")
    if args.log_level is not None:
        settings.set("LOG_LEVEL", args.log_level, priority="cmdline")

    process = CrawlerProcess(settings)
    process.crawl(
        CfzhSpider,
        pages=args.pages,
        start_url=args.start_url,
        max_requests=args.max_requests,
        database_url=args.database_url,
    )
    process.start()
    return 0


def run_export(args: argparse.Namespace) -> int:
    from wxc_cfzh_crawler.export import export_records

    export_records(
        database_url=args.database_url,
        output_path=Path(args.out),
        output_format=args.format,
        shape=args.shape,
    )
    return 0


def frontend_manifest_hash(frontend_dir: Path) -> str:
    digest = hashlib.sha256()
    for manifest in FRONTEND_DEPENDENCY_MANIFESTS:
        manifest_path = frontend_dir / manifest
        digest.update(manifest.encode("utf-8"))
        digest.update(b"\0")
        digest.update(manifest_path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def frontend_sync_marker_path(frontend_dir: Path) -> Path:
    return frontend_dir / "node_modules" / FRONTEND_SYNC_MARKER


def frontend_dependencies_are_current(frontend_dir: Path, manifest_hash: str) -> bool:
    marker_path = frontend_sync_marker_path(frontend_dir)
    if not marker_path.parent.is_dir():
        return False

    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    return marker.get("manifest_hash") == manifest_hash


def write_frontend_sync_marker(frontend_dir: Path, manifest_hash: str) -> None:
    marker_path = frontend_sync_marker_path(frontend_dir)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(
        json.dumps({"manifest_hash": manifest_hash}, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_frontend_npm(frontend_dir: Path, npm_args: list[str], *, failure_message: str) -> None:
    try:
        subprocess.run(
            ["npm", "--prefix", str(frontend_dir), *npm_args],
            check=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            "Could not refresh the inspector UI because npm was not found. "
            "Install Node/npm or run `wxc inspect --skip-ui-build` for API-only startup."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(failure_message) from exc


def ensure_frontend_ready(repo_root: Path, *, skip_build: bool) -> None:
    frontend_dir = repo_root / "inspector" / "frontend"
    if skip_build:
        return

    manifest_hash = frontend_manifest_hash(frontend_dir)
    if not frontend_dependencies_are_current(frontend_dir, manifest_hash):
        run_frontend_npm(
            frontend_dir,
            ["ci"],
            failure_message=(
                "Inspector UI dependency refresh failed. Run "
                "`npm --prefix inspector/frontend ci` to inspect the npm error, "
                "then retry `wxc inspect`."
            ),
        )
        write_frontend_sync_marker(frontend_dir, manifest_hash)

    run_frontend_npm(
        frontend_dir,
        ["run", "build"],
        failure_message=(
            "Inspector UI build failed. Run `npm --prefix inspector/frontend run build` "
            "to inspect the frontend error, then retry `wxc inspect`."
        ),
    )


def run_inspect(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root()
    if args.db:
        os.environ["WXC_INSPECT_DB"] = str(Path(args.db).expanduser().resolve())

    ensure_frontend_ready(repo_root, skip_build=args.skip_ui_build)

    try:
        import app.main  # noqa: F401
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "The inspector backend is not installed in this environment. "
            "Run `uv sync` from the repository root, then retry `uv run wxc inspect`."
        ) from exc

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
