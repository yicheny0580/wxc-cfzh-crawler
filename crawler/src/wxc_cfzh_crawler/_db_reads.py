from __future__ import annotations

import sqlite3

from wxc_cfzh_crawler._db_columns import POST_SELECT_COLUMNS, REPLY_SELECT_COLUMNS


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
