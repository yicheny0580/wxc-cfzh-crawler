from __future__ import annotations

import sqlite3
from dataclasses import dataclass

FRONTIER_RECORD_TYPES = ("post", "reply")
FRONTIER_STATUSES = ("pending", "in_progress", "done", "failed")


@dataclass(frozen=True)
class CrawlProgress:
    saved_posts: int
    saved_replies: int
    frontier: dict[str, dict[str, int]]

    def frontier_count(self, record_type: str, status: str) -> int:
        return self.frontier.get(record_type, {}).get(status, 0)


def fetch_crawl_progress(conn: sqlite3.Connection) -> CrawlProgress:
    frontier = {
        record_type: {status: 0 for status in FRONTIER_STATUSES}
        for record_type in FRONTIER_RECORD_TYPES
    }
    for row in conn.execute(
        """
        SELECT record_type, status, COUNT(*) AS record_count
        FROM frontier
        GROUP BY record_type, status
        """
    ):
        frontier[str(row["record_type"])][str(row["status"])] = int(row["record_count"])

    saved_posts = int(conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] or 0)
    saved_replies = int(conn.execute("SELECT COUNT(*) FROM replies").fetchone()[0] or 0)
    return CrawlProgress(
        saved_posts=saved_posts,
        saved_replies=saved_replies,
        frontier=frontier,
    )


def format_crawl_progress(progress: CrawlProgress) -> str:
    return (
        f"saved posts={progress.saved_posts} replies={progress.saved_replies}; "
        "frontier posts "
        f"pending={progress.frontier_count('post', 'pending')} "
        f"in_progress={progress.frontier_count('post', 'in_progress')} "
        f"done={progress.frontier_count('post', 'done')} "
        f"failed={progress.frontier_count('post', 'failed')}; "
        "frontier replies "
        f"pending={progress.frontier_count('reply', 'pending')} "
        f"in_progress={progress.frontier_count('reply', 'in_progress')} "
        f"done={progress.frontier_count('reply', 'done')} "
        f"failed={progress.frontier_count('reply', 'failed')}"
    )


def format_live_crawl_progress(
    progress: CrawlProgress,
    *,
    scheduled: int | None = None,
    max_requests: int | None = None,
) -> str:
    pending_posts = progress.frontier_count("post", "pending")
    pending_replies = progress.frontier_count("reply", "pending")
    active = progress.frontier_count("post", "in_progress") + progress.frontier_count(
        "reply",
        "in_progress",
    )
    failed = progress.frontier_count("post", "failed") + progress.frontier_count(
        "reply",
        "failed",
    )
    return (
        f"CFZH saved posts={progress.saved_posts} replies={progress.saved_replies}"
        f" | pending posts={pending_posts} replies={pending_replies}"
        f" | active={active}"
        f" | failed={failed}"
        f" | scheduled={format_scheduled_count(scheduled, max_requests)}"
    )


def format_scheduled_count(scheduled: int | None, max_requests: int | None) -> str:
    if scheduled is None:
        return "?"
    limit = max_requests if max_requests is not None else "unlimited"
    return f"{scheduled}/{limit}"
