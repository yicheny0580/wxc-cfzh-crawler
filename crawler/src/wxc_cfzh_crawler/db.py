from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from wxc_cfzh_crawler.models import ForumPost, ForumReply, FrontierRecord

POST_SELECT_COLUMNS = """
    post_id, url, forum, title, author, author_profile_url, published_at, edited_at,
    body_text, body_html, byte_count, read_count, reply_count, crawled_at
"""

REPLY_SELECT_COLUMNS = """
    reply_id, root_post_id, parent_reply_id, url, forum, title, author, author_profile_url,
    published_at, edited_at, body_text, body_html, byte_count, read_count, depth,
    forum_order, crawled_at
"""

FRONTIER_SELECT_COLUMNS = """
    post_id, url, record_type, root_post_id, parent_reply_id, depth, forum_order, listing_title,
    listing_reply_count, status, attempts, discovered_at, updated_at, last_fetched_at,
    last_http_status, last_error
"""


def sqlite_path_from_url(database_url: str) -> Path:
    parsed = urlparse(database_url)
    if parsed.scheme in {"", "sqlite"}:
        if parsed.scheme == "":
            return Path(database_url)
        if parsed.netloc and parsed.netloc != "":
            raise ValueError(f"Only local SQLite URLs are supported: {database_url}")
        path = unquote(parsed.path)
        if path.startswith("//"):
            return Path(path[1:])
        return Path(path.lstrip("/"))
    raise ValueError(f"Unsupported DATABASE_URL scheme for local scaffold: {parsed.scheme}")


def connect(database_url: str) -> sqlite3.Connection:
    db_path = sqlite_path_from_url(database_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;

        DROP TABLE IF EXISTS pages;

        CREATE TABLE IF NOT EXISTS posts (
            post_id TEXT PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            forum TEXT NOT NULL,
            title TEXT,
            author TEXT,
            author_profile_url TEXT,
            published_at TEXT,
            edited_at TEXT,
            body_text TEXT,
            body_html TEXT,
            byte_count INTEGER,
            read_count INTEGER,
            reply_count INTEGER,
            crawled_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS replies (
            reply_id TEXT PRIMARY KEY,
            root_post_id TEXT NOT NULL,
            parent_reply_id TEXT,
            url TEXT NOT NULL UNIQUE,
            forum TEXT NOT NULL,
            title TEXT,
            author TEXT,
            author_profile_url TEXT,
            published_at TEXT,
            edited_at TEXT,
            body_text TEXT,
            body_html TEXT,
            byte_count INTEGER,
            read_count INTEGER,
            depth INTEGER NOT NULL DEFAULT 1,
            forum_order INTEGER,
            crawled_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS frontier (
            post_id TEXT PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            record_type TEXT NOT NULL CHECK(record_type IN ('post', 'reply')),
            root_post_id TEXT,
            parent_reply_id TEXT,
            depth INTEGER NOT NULL DEFAULT 0,
            forum_order INTEGER,
            listing_title TEXT,
            listing_reply_count INTEGER,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'in_progress', 'done', 'failed')),
            attempts INTEGER NOT NULL DEFAULT 0,
            discovered_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_fetched_at TEXT,
            last_http_status INTEGER,
            last_error TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_posts_published_at ON posts(published_at);
        CREATE INDEX IF NOT EXISTS idx_replies_root_post_id ON replies(root_post_id);
        CREATE INDEX IF NOT EXISTS idx_replies_parent_reply_id ON replies(parent_reply_id);
        CREATE INDEX IF NOT EXISTS idx_replies_published_at ON replies(published_at);
        CREATE INDEX IF NOT EXISTS idx_frontier_status ON frontier(status);
        CREATE INDEX IF NOT EXISTS idx_frontier_root_post_id ON frontier(root_post_id);
        """
    )
    backfill_frontier(conn)
    conn.commit()


def dt_to_text(value: object) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else value  # type: ignore[return-value]


def utc_now_text() -> str:
    return datetime.now(UTC).isoformat()


def backfill_frontier(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        INSERT OR IGNORE INTO frontier (
            post_id, url, record_type, root_post_id, parent_reply_id, depth, forum_order,
            listing_title, listing_reply_count, status, attempts, discovered_at, updated_at,
            last_fetched_at, last_http_status, last_error
        )
        SELECT
            post_id, url, 'post', post_id, NULL, 0, NULL, title, reply_count, 'done', 0,
            crawled_at, crawled_at, crawled_at, 200, NULL
        FROM posts;

        INSERT OR IGNORE INTO frontier (
            post_id, url, record_type, root_post_id, parent_reply_id, depth, forum_order,
            listing_title, listing_reply_count, status, attempts, discovered_at, updated_at,
            last_fetched_at, last_http_status, last_error
        )
        SELECT
            reply_id, url, 'reply', root_post_id, parent_reply_id, depth, forum_order,
            title, NULL, 'done', 0,
            crawled_at, crawled_at, crawled_at, 200, NULL
        FROM replies;
        """
    )


def upsert_post(conn: sqlite3.Connection, post: ForumPost) -> None:
    conn.execute(
        """
        INSERT INTO posts (
            post_id, url, forum, title, author, author_profile_url, published_at, edited_at,
            body_text, body_html, byte_count, read_count, reply_count, crawled_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(post_id) DO UPDATE SET
            url = excluded.url,
            forum = excluded.forum,
            title = excluded.title,
            author = excluded.author,
            author_profile_url = excluded.author_profile_url,
            published_at = excluded.published_at,
            edited_at = excluded.edited_at,
            body_text = excluded.body_text,
            body_html = excluded.body_html,
            byte_count = excluded.byte_count,
            read_count = excluded.read_count,
            reply_count = excluded.reply_count,
            crawled_at = excluded.crawled_at
        """,
        (
            post.post_id,
            post.url,
            post.forum,
            post.title,
            post.author,
            post.author_profile_url,
            dt_to_text(post.published_at),
            dt_to_text(post.edited_at),
            post.body_text,
            post.body_html,
            post.byte_count,
            post.read_count,
            post.reply_count,
            post.crawled_at.isoformat(),
        ),
    )
    conn.commit()


def upsert_reply(conn: sqlite3.Connection, reply: ForumReply) -> None:
    conn.execute(
        """
        INSERT INTO replies (
            reply_id, root_post_id, parent_reply_id, url, forum, title, author,
            author_profile_url, published_at, edited_at, body_text, body_html,
            byte_count, read_count, depth, forum_order, crawled_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(reply_id) DO UPDATE SET
            root_post_id = excluded.root_post_id,
            parent_reply_id = excluded.parent_reply_id,
            url = excluded.url,
            forum = excluded.forum,
            title = excluded.title,
            author = excluded.author,
            author_profile_url = excluded.author_profile_url,
            published_at = excluded.published_at,
            edited_at = excluded.edited_at,
            body_text = excluded.body_text,
            body_html = excluded.body_html,
            byte_count = excluded.byte_count,
            read_count = excluded.read_count,
            depth = excluded.depth,
            forum_order = COALESCE(excluded.forum_order, replies.forum_order),
            crawled_at = excluded.crawled_at
        """,
        (
            reply.reply_id,
            reply.root_post_id,
            reply.parent_reply_id,
            reply.url,
            reply.forum,
            reply.title,
            reply.author,
            reply.author_profile_url,
            dt_to_text(reply.published_at),
            dt_to_text(reply.edited_at),
            reply.body_text,
            reply.body_html,
            reply.byte_count,
            reply.read_count,
            reply.depth,
            reply.forum_order,
            reply.crawled_at.isoformat(),
        ),
    )
    conn.commit()


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


def fetch_root_posts(conn: sqlite3.Connection) -> list[dict[str, object]]:
    rows = conn.execute(
        f"""
        SELECT {POST_SELECT_COLUMNS}
        FROM posts
        ORDER BY
            COALESCE(published_at, '') ASC,
            CAST(post_id AS INTEGER) ASC,
            post_id ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_replies(
    conn: sqlite3.Connection,
    root_post_id: str | None = None,
) -> list[dict[str, object]]:
    params: tuple[str, ...] = ()
    where_clause = ""
    if root_post_id is not None:
        where_clause = "WHERE root_post_id = ?"
        params = (root_post_id,)

    rows = conn.execute(
        f"""
        SELECT {REPLY_SELECT_COLUMNS}
        FROM replies
        {where_clause}
        ORDER BY
            root_post_id ASC,
            COALESCE(forum_order, 2147483647) ASC,
            COALESCE(published_at, '') ASC,
            CAST(reply_id AS INTEGER) ASC,
            reply_id ASC
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]
