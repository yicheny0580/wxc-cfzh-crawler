from __future__ import annotations

import json
import os
import signal
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wxc_cfzh_crawler.paths import default_data_dir, sqlite_url_for_path

LOCK_FILE = "crawl.lock"
STATUS_FILE = "crawl-status.json"
PAUSE_FILE = "scheduler.paused"
LOG_FILE = "admin.log"


def utc_now_text() -> str:
    return datetime.now(UTC).isoformat()


def data_dir() -> Path:
    configured = os.getenv("WXC_ADMIN_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return default_data_dir()


def database_path() -> Path:
    configured = os.getenv("WXC_ADMIN_DB") or os.getenv("WXC_INSPECT_DB")
    if configured:
        return Path(configured).expanduser().resolve()
    return data_dir() / "crawler.sqlite3"


def database_url() -> str:
    return sqlite_url_for_path(database_path())


def runtime_dir() -> Path:
    path = data_dir() / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def lock_path() -> Path:
    return runtime_dir() / LOCK_FILE


def status_path() -> Path:
    return runtime_dir() / STATUS_FILE


def pause_path() -> Path:
    return runtime_dir() / PAUSE_FILE


def log_path() -> Path:
    configured = os.getenv("WXC_ADMIN_LOG")
    if configured:
        path = Path(configured).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return runtime_dir() / LOG_FILE


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_lock() -> dict[str, Any] | None:
    return read_json(lock_path())


def read_status() -> dict[str, Any] | None:
    return read_json(status_path())


def write_status(payload: dict[str, Any]) -> None:
    payload = {**payload, "updated_at": utc_now_text()}
    write_json(status_path(), payload)


def process_alive(pid: object) -> bool:
    try:
        parsed = int(pid)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    if parsed <= 0:
        return False
    try:
        os.kill(parsed, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def lock_is_stale(payload: dict[str, Any] | None = None) -> bool:
    current = payload if payload is not None else read_lock()
    if current is None:
        return False
    pid = current.get("pid")
    return pid is not None and not process_alive(pid)


def acquire_lock(payload: dict[str, Any]) -> tuple[bool, dict[str, Any] | None]:
    path = lock_path()
    current = read_lock()
    if current and lock_is_stale(current):
        path.unlink(missing_ok=True)
        current = None

    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False, read_lock()

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return True, None


def update_lock(payload: dict[str, Any]) -> None:
    write_json(lock_path(), payload)


def release_lock(run_id: str | None = None) -> None:
    current = read_lock()
    if run_id and current and current.get("run_id") != run_id:
        return
    lock_path().unlink(missing_ok=True)


def scheduler_paused() -> bool:
    return pause_path().exists()


def set_scheduler_paused(paused: bool) -> None:
    path = pause_path()
    if paused:
        path.write_text(utc_now_text() + "\n", encoding="utf-8")
    else:
        path.unlink(missing_ok=True)


def append_log(event: str, **fields: object) -> None:
    payload = {"time": utc_now_text(), "event": event, **fields}
    with log_path().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def signal_process_group(pgid: object, sig: signal.Signals) -> bool:
    try:
        parsed = int(pgid)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    if parsed <= 0:
        return False
    try:
        os.killpg(parsed, sig)
    except ProcessLookupError:
        return False
    return True
