from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from wxc_cfzh_crawler._db_frontier import (
    DEFAULT_SUPPRESSION_ATTEMPTS,
    mark_frontier_done,
    upsert_frontier_entry,
)
from wxc_cfzh_crawler._db_search import upsert_post_search, upsert_reply_search
from wxc_cfzh_crawler._db_time import dt_to_text
from wxc_cfzh_crawler.models import ForumPost, ForumReply, FrontierRecord


def upsert_post(
    conn: sqlite3.Connection,
    post: ForumPost,
    *,
    commit: bool = True,
) -> None:
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
    upsert_post_search(conn, post)
    if commit:
        conn.commit()


def upsert_reply(
    conn: sqlite3.Connection,
    reply: ForumReply,
    *,
    commit: bool = True,
) -> None:
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
    upsert_reply_search(conn, reply)
    if commit:
        conn.commit()


def save_post_detail(
    conn: sqlite3.Connection,
    post: ForumPost,
    child_frontier: Iterable[FrontierRecord],
    *,
    frontier_post_id: str,
    http_status: int | None = None,
    max_attempts: int = DEFAULT_SUPPRESSION_ATTEMPTS,
) -> None:
    with conn:
        upsert_post(conn, post, commit=False)
        for entry in child_frontier:
            upsert_frontier_entry(
                conn,
                entry,
                max_attempts=max_attempts,
                commit=False,
            )
        mark_frontier_done(
            conn,
            frontier_post_id,
            http_status=http_status,
            commit=False,
        )


def save_reply_detail(
    conn: sqlite3.Connection,
    reply: ForumReply,
    child_frontier: Iterable[FrontierRecord],
    *,
    frontier_post_id: str,
    http_status: int | None = None,
    max_attempts: int = DEFAULT_SUPPRESSION_ATTEMPTS,
) -> None:
    with conn:
        upsert_reply(conn, reply, commit=False)
        for entry in child_frontier:
            upsert_frontier_entry(
                conn,
                entry,
                max_attempts=max_attempts,
                commit=False,
            )
        mark_frontier_done(
            conn,
            frontier_post_id,
            http_status=http_status,
            commit=False,
        )


def save_listing_record_without_detail(
    conn: sqlite3.Connection,
    record: ForumPost | ForumReply,
    frontier: FrontierRecord,
    *,
    max_attempts: int = DEFAULT_SUPPRESSION_ATTEMPTS,
) -> None:
    with conn:
        upsert_frontier_entry(
            conn,
            frontier,
            max_attempts=max_attempts,
            commit=False,
        )
        if isinstance(record, ForumPost):
            upsert_post(conn, record, commit=False)
        else:
            upsert_reply(conn, record, commit=False)
        mark_frontier_done(
            conn,
            frontier.post_id,
            http_status=None,
            commit=False,
        )
