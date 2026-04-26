from __future__ import annotations

import os
import sqlite3
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException


def resolve_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "data").exists() and (parent / "pyproject.toml").exists():
            return parent
    return current.parents[3]


def resolve_db_path() -> Path:
    configured = os.environ.get("WXC_INSPECT_DB")
    if configured:
        return Path(configured).expanduser().resolve()
    return resolve_repo_root() / "data" / "crawler.sqlite3"


def connect_readonly(db_path: Path | None = None) -> sqlite3.Connection:
    path = (db_path or resolve_db_path()).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    uri = f"file:{quote(str(path), safe='/:')}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA query_only = ON")
    return conn


async def get_connection() -> AsyncIterator[sqlite3.Connection]:
    path = resolve_db_path()
    try:
        conn = connect_readonly(path)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"SQLite database not found at {path}",
        ) from exc
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not open SQLite database at {path}: {exc}",
        ) from exc

    try:
        yield conn
    finally:
        conn.close()
