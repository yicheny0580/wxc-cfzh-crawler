from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

FORUM_SOURCE_TIMEZONE_NAME = "America/Los_Angeles"
FORUM_SOURCE_TIMEZONE = ZoneInfo(FORUM_SOURCE_TIMEZONE_NAME)


def parse_timezone(timezone_name: str | None) -> ZoneInfo:
    if not timezone_name:
        return FORUM_SOURCE_TIMEZONE
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {timezone_name}") from exc


def forum_timestamp_to_api(value: object) -> object:
    if not isinstance(value, str) or not value:
        return value

    parsed = parse_datetime_text(value)
    if parsed is None:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=FORUM_SOURCE_TIMEZONE)
    return parsed.isoformat()


def local_date_filter_bounds(
    *,
    published_from: date | None,
    published_to: date | None,
    timezone_name: str | None,
) -> tuple[str | None, str | None]:
    timezone = parse_timezone(timezone_name)
    from_bound = source_bound_for_local_date(published_from, timezone) if published_from else None
    before_bound = (
        source_bound_for_local_date(published_to + timedelta(days=1), timezone)
        if published_to
        else None
    )
    return from_bound, before_bound


def source_bound_for_local_date(value: date, timezone: ZoneInfo) -> str:
    local_midnight = datetime.combine(value, time.min, tzinfo=timezone)
    source_time = local_midnight.astimezone(FORUM_SOURCE_TIMEZONE)
    return source_time.replace(tzinfo=None).isoformat(timespec="seconds")


def parse_datetime_text(value: str) -> datetime | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass

    for pattern in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(normalized, pattern)
        except ValueError:
            pass
    return None
