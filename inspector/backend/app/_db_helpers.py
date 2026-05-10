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

MIN_SEARCH_LENGTH = 2
FTS_SEARCH_LENGTH = 3


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


def parse_search_terms(search: str | None) -> list[str]:
    if search is None:
        return []

    terms = [term for term in search.strip().split() if term]
    if not terms:
        return []

    short_terms = [term for term in terms if len(term) < MIN_SEARCH_LENGTH]
    if short_terms:
        raise ValueError(f"Search terms must be at least {MIN_SEARCH_LENGTH} characters.")

    return terms


def fts_query(term: str) -> str:
    escaped = term.replace('"', '""')
    return f'"{escaped}"'


def substring_search_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def add_search_filters(
    clauses: list[str],
    params: list[object],
    *,
    search: str | None,
    alias: str,
    id_column: str,
    fts_table: str,
) -> None:
    for term in parse_search_terms(search):
        if len(term) >= FTS_SEARCH_LENGTH:
            clauses.append(
                f"""
                {alias}.{id_column} IN (
                    SELECT {id_column} FROM {fts_table} WHERE {fts_table} MATCH ?
                )
                """
            )
            params.append(fts_query(term))
            continue

        pattern = substring_search_pattern(term)
        clauses.append(
            f"""
            (
                COALESCE({alias}.title, '') LIKE ? ESCAPE '\\'
                OR COALESCE({alias}.author, '') LIKE ? ESCAPE '\\'
                OR COALESCE({alias}.body_text, '') LIKE ? ESCAPE '\\'
            )
            """
        )
        params.extend([pattern, pattern, pattern])


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

    add_search_filters(
        clauses,
        params,
        search=search,
        alias="p",
        id_column="post_id",
        fts_table="posts_fts",
    )

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

    if alias == "p":
        add_search_filters(
            clauses,
            params,
            search=search,
            alias=alias,
            id_column="post_id",
            fts_table="posts_fts",
        )
    elif alias == "r":
        add_search_filters(
            clauses,
            params,
            search=search,
            alias=alias,
            id_column="reply_id",
            fts_table="replies_fts",
        )

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
