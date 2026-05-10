from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from wxc_cfzh_crawler import admin_runtime as runtime

BUSY_EXIT = 75


def crawler_command(pages: int | str) -> list[str]:
    scrapy_bin = shutil.which("scrapy")
    command = [scrapy_bin] if scrapy_bin else [sys.executable, "-m", "scrapy"]
    return [
        *command,
        "crawl",
        "cfzh",
        "-a",
        f"pages={pages}",
        "-a",
        f"database_url={runtime.database_url()}",
    ]


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def db_summary() -> dict[str, Any]:
    path = runtime.database_path()
    if not path.exists():
        return {"db_path": str(path), "db_exists": False}
    try:
        conn = sqlite3.connect(path)
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
        return {"db_path": str(path), "db_exists": True, "error": str(exc)}
    finally:
        if "conn" in locals():
            conn.close()
    return {
        "db_path": str(path),
        "db_exists": True,
        "posts": int(posts or 0),
        "replies": int(replies or 0),
        "latest_crawl_at": latest,
    }


def status_payload() -> dict[str, Any]:
    lock = runtime.read_lock()
    stale = runtime.lock_is_stale(lock)
    return {
        "time": runtime.utc_now_text(),
        "scheduler_paused": runtime.scheduler_paused(),
        "lock": lock,
        "lock_stale": stale,
        "last_status": runtime.read_status(),
        "database": db_summary(),
    }


def run_refresh(
    pages: int,
    reason: str,
    *,
    all_pages: bool = False,
    quiet_busy: bool = False,
) -> int:
    run_id = uuid.uuid4().hex
    started_at = runtime.utc_now_text()
    requested_pages: int | str = "all" if all_pages else pages
    lock_payload: dict[str, Any] = {
        "run_id": run_id,
        "reason": reason,
        "pages": requested_pages,
        "all_pages": all_pages,
        "started_at": started_at,
    }
    acquired, active = runtime.acquire_lock(lock_payload)
    if not acquired:
        runtime.append_log("skip_busy", reason=reason, active=active)
        if not quiet_busy:
            print_json({"state": "busy", "active": active})
        return BUSY_EXIT

    log_handle = runtime.log_path().open("a", encoding="utf-8")
    process: subprocess.Popen[str] | None = None
    try:
        command = crawler_command(requested_pages)
        env = os.environ.copy()
        env.update({"SCRAPY_SETTINGS_MODULE": "wxc_cfzh_crawler.settings", "WXC_PROGRESS": "off"})
        process = subprocess.Popen(
            command,
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        pgid = os.getpgid(process.pid)
        lock_payload.update({"pid": process.pid, "pgid": pgid, "command": command})
        runtime.update_lock(lock_payload)
        runtime.write_status(
            {
                "state": "running",
                "run_id": run_id,
                "reason": reason,
                "pages": requested_pages,
                "all_pages": all_pages,
                "pid": process.pid,
                "pgid": pgid,
                "started_at": started_at,
            }
        )
        runtime.append_log(
            "crawl_started",
            run_id=run_id,
            reason=reason,
            pages=requested_pages,
            all_pages=all_pages,
        )
        return_code = process.wait()
        finished_at = runtime.utc_now_text()
        state = "succeeded" if return_code == 0 else "stopped" if return_code < 0 else "failed"
        runtime.write_status(
            {
                "state": state,
                "run_id": run_id,
                "reason": reason,
                "pages": requested_pages,
                "all_pages": all_pages,
                "pid": process.pid,
                "pgid": pgid,
                "started_at": started_at,
                "finished_at": finished_at,
                "return_code": return_code,
            }
        )
        runtime.append_log(
            "crawl_finished",
            run_id=run_id,
            state=state,
            return_code=return_code,
            all_pages=all_pages,
        )
        print_json({"state": state, "run_id": run_id, "return_code": return_code})
        return int(return_code or 0)
    finally:
        runtime.release_lock(run_id)
        log_handle.close()


def command_refresh(args: argparse.Namespace) -> int:
    return run_refresh(args.pages, args.reason, all_pages=args.all_pages)


def wait_for_stop(lock: dict[str, Any], force_after: float) -> str:
    pid = lock.get("pid")
    pgid = lock.get("pgid")
    if not runtime.process_alive(pid):
        runtime.release_lock(str(lock.get("run_id") or ""))
        return "idle"

    runtime.signal_process_group(pgid, signal.SIGTERM)
    deadline = time.monotonic() + force_after
    while time.monotonic() < deadline:
        if not runtime.process_alive(pid):
            return "stopped"
        time.sleep(0.25)

    killed = runtime.signal_process_group(pgid, signal.SIGKILL)
    return "killed" if killed else "stopped"


def command_stop(args: argparse.Namespace) -> int:
    lock = runtime.read_lock()
    if lock is None or runtime.lock_is_stale(lock):
        runtime.release_lock()
        payload = {"state": "idle", "detail": "No active crawl."}
        runtime.append_log("stop_idle")
        print_json(payload)
        return 0

    if not args.wait:
        runtime.signal_process_group(lock.get("pgid"), signal.SIGTERM)
        runtime.append_log("stop_requested", result="stopping", active=lock)
        print_json({"state": "stopping", "active": lock})
        return 0

    result = wait_for_stop(lock, args.force_after)
    runtime.append_log("stop_requested", result=result, active=lock)
    print_json({"state": result, "active": lock})
    return 0


def command_status(args: argparse.Namespace) -> int:
    payload = status_payload()
    if args.json:
        print_json(payload)
    else:
        active = payload["lock"]
        state = "busy" if active and not payload["lock_stale"] else "idle"
        print(f"state: {state}")
        print(f"scheduler_paused: {payload['scheduler_paused']}")
        print(f"db_posts: {payload['database'].get('posts', '-')}")
        print(f"db_replies: {payload['database'].get('replies', '-')}")
        if active:
            print(f"active_run: {active.get('run_id')} reason={active.get('reason')}")
        if payload["lock_stale"]:
            print("warning: stale crawl lock detected")
    return 0


def command_report(_args: argparse.Namespace) -> int:
    payload = status_payload()
    disk = shutil.disk_usage(runtime.data_dir())
    print("WXC CFZH diagnostics")
    print(f"time: {payload['time']}")
    print(f"scheduler_paused: {payload['scheduler_paused']}")
    print(f"lock_stale: {payload['lock_stale']}")
    print(f"database: {payload['database']}")
    print(f"last_status: {payload['last_status']}")
    print(f"data_disk_free_mb: {disk.free // 1024 // 1024}")
    print(f"log_file: {runtime.log_path()}")
    return 0


def tail_lines(path: Path, count: int) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return []
    return lines[-count:]


def command_logs(args: argparse.Namespace) -> int:
    path = runtime.log_path()
    for line in tail_lines(path, args.tail):
        print(line)
    if not args.follow:
        return 0
    with path.open("a+", encoding="utf-8") as handle:
        handle.seek(0, os.SEEK_END)
        while True:
            line = handle.readline()
            if line:
                print(line, end="")
            else:
                time.sleep(0.5)


def scheduler_run(args: argparse.Namespace) -> int:
    runtime.append_log("scheduler_started", interval=args.interval, pages=args.pages)
    while True:
        if runtime.scheduler_paused():
            runtime.append_log("skip_paused")
        else:
            run_refresh(args.pages, "scheduled", quiet_busy=True)
        time.sleep(args.interval)


def scheduler_pause(_args: argparse.Namespace) -> int:
    runtime.set_scheduler_paused(True)
    runtime.append_log("scheduler_paused")
    print_json({"scheduler_paused": True})
    return 0


def scheduler_resume(_args: argparse.Namespace) -> int:
    runtime.set_scheduler_paused(False)
    runtime.append_log("scheduler_resumed")
    print_json({"scheduler_paused": False})
    return 0


def scheduler_status(args: argparse.Namespace) -> int:
    return command_status(argparse.Namespace(json=args.json))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wxc-cfzh-admin")
    subparsers = parser.add_subparsers(dest="command", required=True)

    refresh = subparsers.add_parser("refresh")
    refresh.add_argument("--pages", type=int, default=2)
    refresh.add_argument("--all-pages", action="store_true")
    refresh.add_argument("--reason", default="manual")
    refresh.set_defaults(func=command_refresh)

    stop = subparsers.add_parser("stop")
    stop.add_argument("--wait", action="store_true")
    stop.add_argument("--force-after", type=float, default=30.0)
    stop.set_defaults(func=command_stop)

    status = subparsers.add_parser("status")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=command_status)

    report = subparsers.add_parser("report")
    report.set_defaults(func=command_report)

    logs = subparsers.add_parser("logs")
    logs.add_argument("--tail", type=int, default=200)
    logs.add_argument("--follow", action="store_true")
    logs.set_defaults(func=command_logs)

    scheduler = subparsers.add_parser("scheduler")
    scheduler_subparsers = scheduler.add_subparsers(dest="scheduler_command", required=True)
    scheduler_run_parser = scheduler_subparsers.add_parser("run")
    scheduler_run_parser.add_argument("--interval", type=int, default=120)
    scheduler_run_parser.add_argument("--pages", type=int, default=2)
    scheduler_run_parser.set_defaults(func=scheduler_run)
    scheduler_subparsers.add_parser("pause").set_defaults(func=scheduler_pause)
    scheduler_subparsers.add_parser("resume").set_defaults(func=scheduler_resume)
    scheduler_status_parser = scheduler_subparsers.add_parser("status")
    scheduler_status_parser.add_argument("--json", action="store_true")
    scheduler_status_parser.set_defaults(func=scheduler_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
