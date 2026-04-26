from __future__ import annotations

import os
import sqlite3
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException

POST_COLUMNS = """
    post_id, url, forum, title, author, author_profile_url, published_at, edited_at,
    body_text, body_html, byte_count, read_count, reply_count, crawled_at
"""

REPLY_COLUMNS = """
    reply_id, root_post_id, parent_reply_id, url, forum, title, author, author_profile_url,
    published_at, edited_at, body_text, body_html, byte_count, read_count, depth,
    forum_order, crawled_at
"""


def resolve_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "data").exists() and (parent / "pyproject.toml").exists():
            return parent
    return current.parents[3]


def resolve_db_path() -> Path:
    configured = os.environ.get("WXC_INSPECT_DB")
    if configured:
        return Path(configured).expanduser().resolve()
    return resolve_repo_root() / "data" / "crawler.sqlite3"


def connect_readonly(db_path: Path | None = None) -> sqlite3.Connection:
    path = (db_path or resolve_db_path()).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    uri = f"file:{quote(str(path), safe='/:')}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA query_only = ON")
    return conn


async def get_connection() -> AsyncIterator[sqlite3.Connection]:
    path = resolve_db_path()
    try:
        conn = connect_readonly(path)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"SQLite database not found at {path}",
        ) from exc
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not open SQLite database at {path}: {exc}",
        ) from exc

    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return dict(row)


def compact_excerpt(value: str | None, limit: int = 220) -> str | None:
    if not value:
        return None
    compacted = " ".join(value.split())
    if len(compacted) <= limit:
        return compacted
    return f"{compacted[: limit - 1].rstrip()}..."


def _search_pattern(search: str) -> str:
    return f"%{search.strip().lower()}%"


def _post_filters(search: str | None, author: str | None) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []

    if search and search.strip():
        clauses.append(
            """
            (
                LOWER(COALESCE(p.title, '')) LIKE ?
                OR LOWER(COALESCE(p.body_text, '')) LIKE ?
                OR LOWER(COALESCE(p.author, '')) LIKE ?
            )
            """
        )
        pattern = _search_pattern(search)
        params.extend([pattern, pattern, pattern])

    if author and author.strip():
        clauses.append("p.author = ?")
        params.append(author.strip())

    if not clauses:
        return "", params
    return "WHERE " + " AND ".join(clauses), params


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
        "latest_post_published_at": latest_post_published_at,
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


def fetch_posts(
    conn: sqlite3.Connection,
    *,
    search: str | None,
    author: str | None,
    limit: int,
    offset: int,
) -> dict[str, object]:
    where_clause, params = _post_filters(search, author)
    total = conn.execute(
        f"SELECT COUNT(*) FROM posts p {where_clause}",
        params,
    ).fetchone()[0]

    rows = conn.execute(
        f"""
        SELECT
            {POST_COLUMNS},
            (
                SELECT COUNT(*)
                FROM replies r
                WHERE r.root_post_id = p.post_id
            ) AS actual_reply_count
        FROM posts p
        {where_clause}
        ORDER BY
            COALESCE(p.published_at, p.crawled_at, '') DESC,
            CAST(p.post_id AS INTEGER) DESC,
            p.post_id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    ).fetchall()

    items = []
    for row in rows:
        item = row_to_dict(row)
        item["excerpt"] = compact_excerpt(item.get("body_text"))  # type: ignore[arg-type]
        item.pop("body_text", None)
        item.pop("body_html", None)
        items.append(item)

    return {"items": items, "total": total, "limit": limit, "offset": offset}


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
