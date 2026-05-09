from __future__ import annotations

import os
from pathlib import Path

from app._db_connection import resolve_repo_root

TRUE_VALUES = {"1", "true", "yes", "on"}
PUBLIC_DB_LABEL = "SQLite database"


def inspect_public_mode() -> bool:
    return os.getenv("WXC_INSPECT_PUBLIC", "").strip().lower() in TRUE_VALUES


def display_db_path(path: str) -> str:
    if inspect_public_mode():
        return PUBLIC_DB_LABEL

    resolved_path = Path(path).expanduser().resolve()
    try:
        return resolved_path.relative_to(resolve_repo_root()).as_posix()
    except ValueError:
        return resolved_path.name or PUBLIC_DB_LABEL
