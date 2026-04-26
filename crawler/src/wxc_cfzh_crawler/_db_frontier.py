from __future__ import annotations

import sqlite3

from wxc_cfzh_crawler._db_columns import FRONTIER_SELECT_COLUMNS
from wxc_cfzh_crawler._db_time import utc_now_text
from wxc_cfzh_crawler.models import FrontierRecord


def current_root_reply_count(conn: sqlite3.Connection, root_post_id: str) -> int:
    stored = conn.execute(
        "SELECT reply_count FROM posts WHERE post_id = ?",
        (root_post_id,),
    ).fetchone()
    stored_count = int(stored["reply_count"] or 0) if stored else 0
    actual_count = conn.execute(
        "SELECT COUNT(*) FROM replies WHERE root_post_id = ?",
        (root_post_id,),
    ).fetchone()[0]
    return max(stored_count, int(actual_count or 0))


def fetch_frontier_row(
    conn: sqlite3.Connection,
    post_id: str,
) -> dict[str, object] | None:
    row = conn.execute(
        f"SELECT {FRONTIER_SELECT_COLUMNS} FROM frontier WHERE post_id = ?",
        (post_id,),
    ).fetchone()
    return dict(row) if row else None


def upsert_frontier_entry(
    conn: sqlite3.Connection,
    entry: FrontierRecord,
    *,
    max_attempts: int = 3,
) -> None:
    now = utc_now_text()
    existing = fetch_frontier_row(conn, entry.post_id)

    if existing is None:
        conn.execute(
            """
            INSERT INTO frontier (
                post_id, url, record_type, root_post_id, parent_reply_id, depth, forum_order,
                listing_title, listing_reply_count, status, attempts, discovered_at, updated_at,
                last_fetched_at, last_http_status, last_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?, NULL, NULL, NULL)
            """,
            (
                entry.post_id,
                entry.url,
                entry.record_type,
                entry.root_post_id,
                entry.parent_reply_id,
                entry.depth,
                entry.forum_order,
                entry.listing_title,
                entry.listing_reply_count,
                entry.discovered_at.isoformat(),
                now,
            ),
        )
        conn.commit()
        return

    status = str(existing["status"])
    last_error = existing["last_error"]
    attempts = int(existing["attempts"] or 0)

    if (
        status == "done"
        and entry.record_type == "post"
        and entry.listing_reply_count is not None
        and entry.listing_reply_count > current_root_reply_count(conn, entry.post_id)
    ):
        status = "pending"
        last_error = None
    elif status == "failed" and attempts < max_attempts:
        status = "pending"
        last_error = None

    conn.execute(
        """
        UPDATE frontier SET
            url = ?,
            record_type = ?,
            root_post_id = ?,
            parent_reply_id = ?,
            depth = ?,
            forum_order = COALESCE(?, forum_order),
            listing_title = COALESCE(?, listing_title),
            listing_reply_count = COALESCE(?, listing_reply_count),
            status = ?,
            updated_at = ?,
            last_error = ?
        WHERE post_id = ?
        """,
        (
            entry.url,
            entry.record_type,
            entry.root_post_id or existing["root_post_id"],
            (
                entry.parent_reply_id
                if entry.parent_reply_id is not None
                else existing["parent_reply_id"]
            ),
            entry.depth,
            entry.forum_order,
            entry.listing_title,
            entry.listing_reply_count,
            status,
            now,
            last_error,
            entry.post_id,
        ),
    )
    conn.commit()


def reset_in_progress_frontier(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE frontier
        SET status = 'pending', updated_at = ?
        WHERE status = 'in_progress'
        """,
        (utc_now_text(),),
    )
    conn.commit()


def claim_next_frontier(
    conn: sqlite3.Connection,
    *,
    max_attempts: int = 3,
) -> dict[str, object] | None:
    row = conn.execute(
        f"""
        SELECT {FRONTIER_SELECT_COLUMNS}
        FROM frontier
        WHERE status = 'pending' AND attempts < ?
        ORDER BY
            CASE record_type WHEN 'post' THEN 0 ELSE 1 END ASC,
            discovered_at ASC,
            CAST(post_id AS INTEGER) ASC,
            post_id ASC
        LIMIT 1
        """,
        (max_attempts,),
    ).fetchone()
    if row is None:
        return None

    now = utc_now_text()
    conn.execute(
        """
        UPDATE frontier
        SET status = 'in_progress',
            attempts = attempts + 1,
            updated_at = ?,
            last_error = NULL
        WHERE post_id = ? AND status = 'pending'
        """,
        (now, row["post_id"]),
    )
    conn.commit()
    return fetch_frontier_row(conn, str(row["post_id"]))


def mark_frontier_done(
    conn: sqlite3.Connection,
    post_id: str,
    *,
    http_status: int | None = None,
) -> None:
    now = utc_now_text()
    conn.execute(
        """
        UPDATE frontier
        SET status = 'done',
            updated_at = ?,
            last_fetched_at = ?,
            last_http_status = ?,
            last_error = NULL
        WHERE post_id = ?
        """,
        (now, now, http_status, post_id),
    )
    conn.commit()


def mark_frontier_failed(
    conn: sqlite3.Connection,
    post_id: str,
    *,
    http_status: int | None = None,
    error: str | None = None,
) -> None:
    now = utc_now_text()
    conn.execute(
        """
        UPDATE frontier
        SET status = 'failed',
            updated_at = ?,
            last_fetched_at = ?,
            last_http_status = ?,
            last_error = ?
        WHERE post_id = ?
        """,
        (now, now, http_status, error, post_id),
    )
    conn.commit()
