from __future__ import annotations

import sqlite3

from app._db_helpers import POST_COLUMNS, REPLY_COLUMNS, row_to_dict


def fetch_post(conn: sqlite3.Connection, post_id: str) -> dict[str, object] | None:
    row = conn.execute(
        f"""
        SELECT
            {POST_COLUMNS},
            (
                SELECT COUNT(*)
                FROM replies r
                WHERE r.root_post_id = p.post_id
            ) AS actual_reply_count
        FROM posts p
        WHERE p.post_id = ?
        """,
        (post_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def fetch_reply_rows(conn: sqlite3.Connection, post_id: str) -> list[dict[str, object]]:
    rows = conn.execute(
        f"""
        SELECT {REPLY_COLUMNS}
        FROM replies
        WHERE root_post_id = ?
        ORDER BY
            COALESCE(forum_order, 2147483647) ASC,
            COALESCE(published_at, '') ASC,
            CAST(reply_id AS INTEGER) ASC,
            reply_id ASC
        """,
        (post_id,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def build_reply_tree(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    nodes: dict[str, dict[str, object]] = {}
    for row in rows:
        reply_id = str(row["reply_id"])
        nodes[reply_id] = {**row, "replies": []}

    roots: list[dict[str, object]] = []
    for row in rows:
        node = nodes[str(row["reply_id"])]
        parent_id = row.get("parent_reply_id")
        if parent_id and str(parent_id) in nodes:
            parent = nodes[str(parent_id)]
            children = parent["replies"]
            assert isinstance(children, list)
            children.append(node)
        else:
            roots.append(node)
    return roots
