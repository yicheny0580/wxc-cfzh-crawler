from __future__ import annotations

import os

TRUE_VALUES = {"1", "true", "yes", "on"}
PUBLIC_DB_LABEL = "SQLite database"


def inspect_public_mode() -> bool:
    return os.getenv("WXC_INSPECT_PUBLIC", "").strip().lower() in TRUE_VALUES


def display_db_path(path: str) -> str:
    if inspect_public_mode():
        return PUBLIC_DB_LABEL
    return path
