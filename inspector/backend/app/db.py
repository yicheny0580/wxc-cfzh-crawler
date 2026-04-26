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


def _record_filters(
    alias: str,
    *,
    search: str | None,
    author: str | None,
) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []

    if search and search.strip():
        clauses.append(
            f"""
            (
                LOWER(COALESCE({alias}.title, '')) LIKE ?
                OR LOWER(COALESCE({alias}.body_text, '')) LIKE ?
                OR LOWER(COALESCE({alias}.author, '')) LIKE ?
            )
            """
        )
        pattern = _search_pattern(search)
        params.extend([pattern, pattern, pattern])

    if author and author.strip():
        clauses.append(f"{alias}.author = ?")
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


def fetch_results(
    conn: sqlite3.Connection,
    *,
    search: str | None,
    author: str | None,
    include_posts: bool,
    include_replies: bool,
    limit: int,
    offset: int,
) -> dict[str, object]:
    selects: list[str] = []
    params: list[object] = []

    if include_posts:
        where_clause, post_params = _record_filters("p", search=search, author=author)
        selects.append(
            f"""
            SELECT
                'post' AS record_type,
                p.post_id AS post_id,
                NULL AS reply_id,
                p.post_id AS root_post_id,
                p.url AS url,
                p.forum AS forum,
                p.title AS title,
                p.author AS author,
                p.author_profile_url AS author_profile_url,
                p.published_at AS published_at,
                p.edited_at AS edited_at,
                p.byte_count AS byte_count,
                p.read_count AS read_count,
                p.reply_count AS reply_count,
                (
                    SELECT COUNT(*)
                    FROM replies r
                    WHERE r.root_post_id = p.post_id
                ) AS actual_reply_count,
                NULL AS root_title,
                NULL AS root_author,
                NULL AS root_url,
                p.body_text AS body_text,
                p.crawled_at AS crawled_at,
                COALESCE(p.published_at, p.crawled_at, '') AS sort_at,
                CAST(p.post_id AS INTEGER) AS numeric_id,
                p.post_id AS record_id
            FROM posts p
            {where_clause}
            """
        )
        params.extend(post_params)

    if include_replies:
        where_clause, reply_params = _record_filters("r", search=search, author=author)
        selects.append(
            f"""
            SELECT
                'reply' AS record_type,
                r.root_post_id AS post_id,
                r.reply_id AS reply_id,
                r.root_post_id AS root_post_id,
                r.url AS url,
                r.forum AS forum,
                r.title AS title,
                r.author AS author,
                r.author_profile_url AS author_profile_url,
                r.published_at AS published_at,
                r.edited_at AS edited_at,
                r.byte_count AS byte_count,
                r.read_count AS read_count,
                NULL AS reply_count,
                NULL AS actual_reply_count,
                p.title AS root_title,
                p.author AS root_author,
                p.url AS root_url,
                r.body_text AS body_text,
                r.crawled_at AS crawled_at,
                COALESCE(r.published_at, r.crawled_at, '') AS sort_at,
                CAST(r.reply_id AS INTEGER) AS numeric_id,
                r.reply_id AS record_id
            FROM replies r
            LEFT JOIN posts p ON p.post_id = r.root_post_id
            {where_clause}
            """
        )
        params.extend(reply_params)

    if not selects:
        return {"items": [], "total": 0, "limit": limit, "offset": offset}

    combined_sql = "\nUNION ALL\n".join(selects)
    total = conn.execute(f"SELECT COUNT(*) FROM ({combined_sql}) results", params).fetchone()[0]
    rows = conn.execute(
        f"""
        SELECT
            record_type,
            post_id,
            reply_id,
            root_post_id,
            url,
            forum,
            title,
            author,
            author_profile_url,
            published_at,
            edited_at,
            byte_count,
            read_count,
            reply_count,
            actual_reply_count,
            root_title,
            root_author,
            root_url,
            body_text,
            crawled_at
        FROM ({combined_sql}) results
        ORDER BY
            sort_at DESC,
            numeric_id DESC,
            record_id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    ).fetchall()

    items = []
    for row in rows:
        item = row_to_dict(row)
        item["excerpt"] = compact_excerpt(item.get("body_text"))  # type: ignore[arg-type]
        item.pop("body_text", None)
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
