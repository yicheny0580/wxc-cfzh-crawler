from __future__ import annotations

import sqlite3

from app._time import forum_timestamp_to_api

POST_COLUMNS = """
    post_id, url, forum, title, author, author_profile_url, published_at, edited_at,
    body_text, body_html, byte_count, read_count, reply_count, crawled_at
"""

REPLY_COLUMNS = """
    reply_id, root_post_id, parent_reply_id, url, forum, title, author, author_profile_url,
    published_at, edited_at, body_text, body_html, byte_count, read_count, depth,
    forum_order, crawled_at
"""

MIN_SEARCH_LENGTH = 3


def row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    item = dict(row)
    for key in ("published_at", "edited_at"):
        if key in item:
            item[key] = forum_timestamp_to_api(item.get(key))
    return item


def compact_excerpt(value: str | None, limit: int = 220) -> str | None:
    if not value:
        return None
    compacted = " ".join(value.split())
    if len(compacted) <= limit:
        return compacted
    return f"{compacted[: limit - 1].rstrip()}..."


def fts_query(search: str | None) -> str | None:
    if search is None:
        return None

    terms = [term for term in search.strip().split() if term]
    if not terms:
        return None

    short_terms = [term for term in terms if len(term) < MIN_SEARCH_LENGTH]
    if short_terms:
        raise ValueError(f"Search terms must be at least {MIN_SEARCH_LENGTH} characters.")

    quoted_terms = []
    for term in terms:
        escaped = term.replace('"', '""')
        quoted_terms.append(f'"{escaped}"')
    return " ".join(quoted_terms)


def add_published_date_filters(
    clauses: list[str],
    params: list[object],
    alias: str,
    *,
    published_from: str | None,
    published_before: str | None,
) -> None:
    if published_from or published_before:
        clauses.append(f"{alias}.published_at IS NOT NULL")

    if published_from:
        clauses.append(f"replace({alias}.published_at, ' ', 'T') >= ?")
        params.append(published_from)

    if published_before:
        clauses.append(f"replace({alias}.published_at, ' ', 'T') < ?")
        params.append(published_before)


def post_filters(
    search: str | None,
    author: str | None,
    *,
    published_from: str | None = None,
    published_before: str | None = None,
) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []

    query = fts_query(search)
    if query:
        clauses.append(
            """
            p.post_id IN (
                SELECT post_id FROM posts_fts WHERE posts_fts MATCH ?
            )
            """
        )
        params.append(query)

    if author and author.strip():
        clauses.append("p.author = ?")
        params.append(author.strip())

    add_published_date_filters(
        clauses,
        params,
        "p",
        published_from=published_from,
        published_before=published_before,
    )

    if not clauses:
        return "", params
    return "WHERE " + " AND ".join(clauses), params


def record_filters(
    alias: str,
    *,
    search: str | None,
    author: str | None,
    published_from: str | None = None,
    published_before: str | None = None,
) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []

    query = fts_query(search)
    if query and alias == "p":
        clauses.append(
            """
            p.post_id IN (
                SELECT post_id FROM posts_fts WHERE posts_fts MATCH ?
            )
            """
        )
        params.append(query)
    elif query and alias == "r":
        clauses.append(
            """
            r.reply_id IN (
                SELECT reply_id FROM replies_fts WHERE replies_fts MATCH ?
            )
            """
        )
        params.append(query)

    if author and author.strip():
        clauses.append(f"{alias}.author = ?")
        params.append(author.strip())

    add_published_date_filters(
        clauses,
        params,
        alias,
        published_from=published_from,
        published_before=published_before,
    )

    if not clauses:
        return "", params
    return "WHERE " + " AND ".join(clauses), params
