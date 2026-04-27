from __future__ import annotations

import os

from wxc_cfzh_crawler import admin_runtime as runtime
from wxc_cfzh_crawler.admin_cli import BUSY_EXIT, run_refresh


def test_manual_refresh_reports_busy_when_lock_is_active(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("WXC_ADMIN_DATA_DIR", str(tmp_path))
    acquired, _ = runtime.acquire_lock(
        {
            "run_id": "active",
            "reason": "scheduled",
            "pages": 2,
            "pid": os.getpid(),
        }
    )

    assert acquired is True
    assert run_refresh(2, "manual", quiet_busy=True) == BUSY_EXIT
    assert runtime.read_lock()["run_id"] == "active"  # type: ignore[index]


def test_acquire_lock_recovers_stale_lock(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WXC_ADMIN_DATA_DIR", str(tmp_path))
    acquired, _ = runtime.acquire_lock(
        {
            "run_id": "stale",
            "reason": "manual",
            "pages": 2,
            "pid": 999999999,
        }
    )
    assert acquired is True

    reacquired, active = runtime.acquire_lock({"run_id": "next", "reason": "manual"})

    assert reacquired is True
    assert active is None
    assert runtime.read_lock()["run_id"] == "next"  # type: ignore[index]


def test_scheduler_pause_flag_round_trips(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WXC_ADMIN_DATA_DIR", str(tmp_path))

    runtime.set_scheduler_paused(True)
    assert runtime.scheduler_paused() is True

    runtime.set_scheduler_paused(False)
    assert runtime.scheduler_paused() is False
