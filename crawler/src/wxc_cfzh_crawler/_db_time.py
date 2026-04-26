from __future__ import annotations

from datetime import UTC, datetime


def dt_to_text(value: object) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else value  # type: ignore[return-value]


def utc_now_text() -> str:
    return datetime.now(UTC).isoformat()
