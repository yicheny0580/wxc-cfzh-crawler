from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import WebSocket, WebSocketDisconnect

from app._db_connection import connect_readonly, resolve_db_path, resolve_repo_root
from app.schemas import CrawlProgressCounts, CrawlStatusResponse
from app.settings import display_db_path

CrawlState = Literal["idle", "running", "stopping", "succeeded", "failed", "stopped"]
ACTIVE_STATES: set[CrawlState] = {"running", "stopping"}
TERMINAL_STATES: set[CrawlState] = {"succeeded", "failed", "stopped"}
TAIL_LIMIT = 4000
FRONTIER_STATUSES = ("pending", "in_progress", "done", "failed", "suppressed")

SubprocessFactory = Callable[..., Awaitable[asyncio.subprocess.Process]]


@dataclass
class CrawlJob:
    job_id: str
    pages: int
    all_pages: bool
    db_path: Path
    process: asyncio.subprocess.Process
    started_at: datetime
    state: CrawlState = "running"
    finished_at: datetime | None = None
    return_code: int | None = None
    error: str | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    stop_requested: bool = False


def utc_now() -> datetime:
    return datetime.now(UTC)


def sqlite_url_for_path(path: Path) -> str:
    return f"sqlite:///{path.expanduser().resolve().as_posix()}"


def trim_tail(text: str) -> str:
    if len(text) <= TAIL_LIMIT:
        return text
    return text[-TAIL_LIMIT:]


def fetch_crawl_progress(db_path: Path) -> CrawlProgressCounts | None:
    if not db_path.exists():
        return None

    try:
        conn = connect_readonly(db_path)
    except (FileNotFoundError, OSError):
        return None

    try:
        frontier = {
            record_type: {status: 0 for status in FRONTIER_STATUSES}
            for record_type in ("post", "reply")
        }
        frontier_columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(frontier)")}
        status_expression = (
            """
            CASE
                WHEN status = 'failed' AND suppressed_at IS NOT NULL THEN 'suppressed'
                ELSE status
            END
            """
            if "suppressed_at" in frontier_columns
            else "status"
        )
        for row in conn.execute(
            f"""
            SELECT record_type, {status_expression} AS progress_status, COUNT(*) AS record_count
            FROM frontier
            GROUP BY record_type, progress_status
            """
        ):
            record_type = str(row["record_type"])
            status = str(row["progress_status"])
            if record_type in frontier and status in frontier[record_type]:
                frontier[record_type][status] = int(row["record_count"] or 0)

        saved_posts = int(conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] or 0)
        saved_replies = int(conn.execute("SELECT COUNT(*) FROM replies").fetchone()[0] or 0)
        return CrawlProgressCounts(
            saved_posts=saved_posts,
            saved_replies=saved_replies,
            frontier=frontier,
        )
    except Exception:  # noqa: BLE001
        return None
    finally:
        conn.close()


class CrawlManager:
    def __init__(
        self,
        *,
        subprocess_factory: SubprocessFactory | None = None,
        stop_grace_seconds: float = 10.0,
    ) -> None:
        self._subprocess_factory = subprocess_factory or asyncio.create_subprocess_exec
        self._stop_grace_seconds = stop_grace_seconds
        self._lock = asyncio.Lock()
        self._job: CrawlJob | None = None
        self._subscribers: set[asyncio.Queue[CrawlStatusResponse]] = set()

    async def start(
        self,
        *,
        pages: int,
        all_pages: bool = False,
    ) -> tuple[bool, CrawlStatusResponse]:
        async with self._lock:
            if self._job is not None and self._job.state in ACTIVE_STATES:
                return False, self.status()

            db_path = resolve_db_path()
            command = self._build_command(pages=pages, all_pages=all_pages, db_path=db_path)
            env = os.environ.copy()
            env.update(
                {
                    "SCRAPY_SETTINGS_MODULE": "wxc_cfzh_crawler.settings",
                    "WXC_PROGRESS": "off",
                }
            )

            try:
                process = await self._subprocess_factory(
                    *command,
                    cwd=str(resolve_repo_root()),
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except Exception as exc:  # noqa: BLE001
                self._job = self._failed_start_job(
                    pages=pages,
                    all_pages=all_pages,
                    db_path=db_path,
                    error=str(exc),
                )
                status = self.status()
                await self._broadcast_status(status)
                return True, status

            self._job = CrawlJob(
                job_id=uuid.uuid4().hex,
                pages=pages,
                all_pages=all_pages,
                db_path=db_path,
                process=process,
                started_at=utc_now(),
            )
            asyncio.create_task(self._monitor(self._job))
            status = self.status()

        await self._broadcast_status(status)
        return True, status

    async def stop(self) -> CrawlStatusResponse:
        async with self._lock:
            if self._job is None or self._job.state not in ACTIVE_STATES:
                return self.status()

            job = self._job
            if job.state == "running":
                job.state = "stopping"
                job.stop_requested = True
                job.error = "Stop requested by user."
                if job.process.returncode is None:
                    job.process.terminate()
                asyncio.create_task(self._kill_after_grace(job))
            status = self.status()

        await self._broadcast_status(status)
        return status

    def status(self) -> CrawlStatusResponse:
        job = self._job
        db_path = job.db_path if job is not None else resolve_db_path()
        progress = fetch_crawl_progress(db_path)

        if job is None:
            return CrawlStatusResponse(
                state="idle",
                db_path=display_db_path(str(db_path)),
                progress=progress,
            )

        finished_at = job.finished_at
        elapsed_until = finished_at or utc_now()
        return CrawlStatusResponse(
            state=job.state,
            job_id=job.job_id,
            pages=job.pages,
            all_pages=job.all_pages,
            started_at=job.started_at,
            finished_at=finished_at,
            elapsed_seconds=max(0.0, (elapsed_until - job.started_at).total_seconds()),
            return_code=job.return_code,
            error=job.error,
            stdout_tail=job.stdout_tail or None,
            stderr_tail=job.stderr_tail or None,
            db_path=display_db_path(str(db_path)),
            progress=progress,
        )

    async def subscribe(self, websocket: WebSocket) -> None:
        await websocket.accept()
        queue: asyncio.Queue[CrawlStatusResponse] = asyncio.Queue(maxsize=10)
        self._subscribers.add(queue)
        try:
            await websocket.send_json(self.status().model_dump(mode="json"))
            while True:
                try:
                    message = await asyncio.wait_for(websocket.receive(), timeout=1.0)
                    if message["type"] == "websocket.disconnect":
                        break
                except TimeoutError:
                    pass
                try:
                    status = queue.get_nowait()
                except asyncio.QueueEmpty:
                    status = self.status()
                await websocket.send_json(status.model_dump(mode="json"))
        except WebSocketDisconnect:
            return
        finally:
            self._subscribers.discard(queue)

    def _build_command(self, *, pages: int, all_pages: bool, db_path: Path) -> list[str]:
        page_argument = "all" if all_pages else str(pages)
        return [
            "uv",
            "run",
            "--package",
            "wxc-cfzh-crawler",
            "scrapy",
            "crawl",
            "cfzh",
            "-a",
            f"pages={page_argument}",
            "-a",
            f"database_url={sqlite_url_for_path(db_path)}",
        ]

    def _failed_start_job(
        self,
        *,
        pages: int,
        all_pages: bool,
        db_path: Path,
        error: str,
    ) -> CrawlJob:
        now = utc_now()
        return CrawlJob(
            job_id=uuid.uuid4().hex,
            pages=pages,
            all_pages=all_pages,
            db_path=db_path,
            process=_CompletedProcess(),
            started_at=now,
            finished_at=now,
            state="failed",
            return_code=None,
            error=f"Failed to start crawler: {error}",
        )

    async def _monitor(self, job: CrawlJob) -> None:
        stdout_task = asyncio.create_task(self._read_stream(job, "stdout"))
        stderr_task = asyncio.create_task(self._read_stream(job, "stderr"))

        while job.process.returncode is None:
            try:
                await asyncio.wait_for(job.process.wait(), timeout=1.0)
            except TimeoutError:
                await self._broadcast_status(self.status())

        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)

        async with self._lock:
            job.return_code = job.process.returncode
            job.finished_at = utc_now()
            if job.stop_requested or job.state == "stopping":
                job.state = "stopped"
            elif job.process.returncode == 0:
                job.state = "succeeded"
                job.error = None
            else:
                job.state = "failed"
                if job.error is None:
                    job.error = f"Crawler exited with code {job.process.returncode}."
            status = self.status()

        await self._broadcast_status(status)

    async def _read_stream(self, job: CrawlJob, stream_name: Literal["stdout", "stderr"]) -> None:
        stream = getattr(job.process, stream_name, None)
        if stream is None:
            return

        while True:
            chunk = await stream.readline()
            if not chunk:
                return
            text = chunk.decode("utf-8", errors="replace")
            if stream_name == "stdout":
                job.stdout_tail = trim_tail(job.stdout_tail + text)
            else:
                job.stderr_tail = trim_tail(job.stderr_tail + text)

    async def _kill_after_grace(self, job: CrawlJob) -> None:
        await asyncio.sleep(self._stop_grace_seconds)
        if job.process.returncode is not None or job.state != "stopping":
            return
        job.error = "Crawler did not stop before the grace period expired; killed."
        job.process.kill()
        await self._broadcast_status(self.status())

    async def _broadcast_status(self, status: CrawlStatusResponse) -> None:
        stale: list[asyncio.Queue[CrawlStatusResponse]] = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(status)
            except asyncio.QueueFull:
                stale.append(queue)
        for queue in stale:
            self._subscribers.discard(queue)


class _CompletedProcess:
    returncode: int | None = None
    stdout = None
    stderr = None

    async def wait(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        return

    def kill(self) -> None:
        return


crawl_manager = CrawlManager()
