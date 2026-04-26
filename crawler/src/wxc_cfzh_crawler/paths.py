from __future__ import annotations

import os
from pathlib import Path


def resolve_repo_root(start: Path | None = None) -> Path:
    configured = os.getenv("WXC_REPO_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()

    current = (start or Path(__file__)).resolve()
    for parent in current.parents:
        if (parent / "crawler").is_dir() and (parent / "inspector").is_dir():
            return parent

    for parent in current.parents:
        if parent.name == "crawler" and (parent / "pyproject.toml").is_file():
            return parent.parent

    return Path.cwd().resolve()


def default_data_dir() -> Path:
    configured = os.getenv("WXC_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return resolve_repo_root() / "data"


def sqlite_url_for_path(path: Path) -> str:
    return f"sqlite:///{path.expanduser().resolve().as_posix()}"


def default_database_url() -> str:
    return os.getenv("DATABASE_URL", sqlite_url_for_path(default_data_dir() / "crawler.sqlite3"))
