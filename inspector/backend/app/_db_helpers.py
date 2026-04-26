from __future__ import annotations

import sqlite3

POST_COLUMNS = """
    post_id, url, forum, title, author, author_profile_url, published_at, edited_at,
    body_text, body_html, byte_count, read_count, reply_count, crawled_at
"""

REPLY_COLUMNS = """
    reply_id, root_post_id, parent_reply_id, url, forum, title, author, author_profile_url,
    published_at, edited_at, body_text, body_html, byte_count, read_count, depth,
    forum_order, crawled_at
"""


def row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return dict(row)


def compact_excerpt(value: str | None, limit: int = 220) -> str | None:
    if not value:
        return None
    compacted = " ".join(value.split())
    if len(compacted) <= limit:
        return compacted
    return f"{compacted[: limit - 1].rstrip()}..."


def search_pattern(search: str) -> str:
    return f"%{search.strip().lower()}%"


def post_filters(search: str | None, author: str | None) -> tuple[str, list[object]]:
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
        pattern = search_pattern(search)
        params.extend([pattern, pattern, pattern])

    if author and author.strip():
        clauses.append("p.author = ?")
        params.append(author.strip())

    if not clauses:
        return "", params
    return "WHERE " + " AND ".join(clauses), params


def record_filters(
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
        pattern = search_pattern(search)
        params.extend([pattern, pattern, pattern])

    if author and author.strip():
        clauses.append(f"{alias}.author = ?")
        params.append(author.strip())

    if not clauses:
        return "", params
    return "WHERE " + " AND ".join(clauses), params
