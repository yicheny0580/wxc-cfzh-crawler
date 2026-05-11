from __future__ import annotations

import sqlite3

from app._db_helpers import (
    POST_COLUMNS,
    compact_excerpt,
    post_filters,
    record_filters,
    row_to_dict,
)


def fetch_posts(
    conn: sqlite3.Connection,
    *,
    search: str | None,
    author: str | None,
    published_from: str | None,
    published_before: str | None,
    limit: int,
    offset: int,
) -> dict[str, object]:
    where_clause, params = post_filters(
        search,
        author,
        published_from=published_from,
        published_before=published_before,
    )
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
            p.published_at IS NULL ASC,
            p.published_at DESC,
            p.crawled_at DESC,
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
    published_from: str | None,
    published_before: str | None,
    include_posts: bool,
    include_replies: bool,
    exclude_root_post_ids: list[str] | None,
    limit: int,
    offset: int,
) -> dict[str, object]:
    selects: list[str] = []
    params: list[object] = []

    if include_posts:
        where_clause, post_params = record_filters(
            "p",
            search=search,
            author=author,
            published_from=published_from,
            published_before=published_before,
            exclude_root_post_ids=exclude_root_post_ids,
        )
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
                CASE WHEN p.published_at IS NULL THEN 1 ELSE 0 END AS sort_is_undated,
                p.published_at AS sort_at,
                CAST(p.post_id AS INTEGER) AS numeric_id,
                p.post_id AS record_id
            FROM posts p
            {where_clause}
            """
        )
        params.extend(post_params)

    if include_replies:
        where_clause, reply_params = record_filters(
            "r",
            search=search,
            author=author,
            published_from=published_from,
            published_before=published_before,
            exclude_root_post_ids=exclude_root_post_ids,
        )
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
                CASE WHEN r.published_at IS NULL THEN 1 ELSE 0 END AS sort_is_undated,
                r.published_at AS sort_at,
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
            sort_is_undated ASC,
            sort_at DESC,
            crawled_at DESC,
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
