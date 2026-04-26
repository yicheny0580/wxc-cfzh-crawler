from __future__ import annotations

import sqlite3
from pathlib import Path

from app._db_connection import resolve_db_path
from app._db_helpers import row_to_dict
from app._time import forum_timestamp_to_api


def fetch_summary(conn: sqlite3.Connection, db_path: Path | None = None) -> dict[str, object]:
    posts = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    replies = conn.execute("SELECT COUNT(*) FROM replies").fetchone()[0]
    authors = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT author FROM posts WHERE author IS NOT NULL AND TRIM(author) != ''
            UNION
            SELECT author FROM replies WHERE author IS NOT NULL AND TRIM(author) != ''
        )
        """
    ).fetchone()[0]
    latest_crawl_at = conn.execute(
        """
        SELECT MAX(value) FROM (
            SELECT crawled_at AS value FROM posts
            UNION ALL
            SELECT crawled_at AS value FROM replies
        )
        """
    ).fetchone()[0]
    latest_post_published_at = conn.execute("SELECT MAX(published_at) FROM posts").fetchone()[0]

    return {
        "db_path": str((db_path or resolve_db_path()).expanduser().resolve()),
        "posts": posts,
        "replies": replies,
        "authors": authors,
        "latest_crawl_at": latest_crawl_at,
        "latest_post_published_at": forum_timestamp_to_api(latest_post_published_at),
    }


def fetch_authors(conn: sqlite3.Connection) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        WITH authors AS (
            SELECT author AS name
            FROM posts
            WHERE author IS NOT NULL AND TRIM(author) != ''
            UNION
            SELECT author AS name
            FROM replies
            WHERE author IS NOT NULL AND TRIM(author) != ''
        ),
        post_counts AS (
            SELECT author AS name, COUNT(*) AS posts
            FROM posts
            WHERE author IS NOT NULL AND TRIM(author) != ''
            GROUP BY author
        ),
        reply_counts AS (
            SELECT author AS name, COUNT(*) AS replies
            FROM replies
            WHERE author IS NOT NULL AND TRIM(author) != ''
            GROUP BY author
        )
        SELECT
            authors.name AS name,
            COALESCE(posts, 0) AS posts,
            COALESCE(replies, 0) AS replies,
            COALESCE(posts, 0) + COALESCE(replies, 0) AS total
        FROM authors
        LEFT JOIN post_counts ON post_counts.name = authors.name
        LEFT JOIN reply_counts ON reply_counts.name = authors.name
        ORDER BY total DESC, name COLLATE NOCASE ASC
        """
    ).fetchall()
    return [row_to_dict(row) for row in rows]
