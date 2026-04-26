from __future__ import annotations

import sqlite3

from wxc_cfzh_crawler._db_time import dt_to_text
from wxc_cfzh_crawler.models import ForumPost, ForumReply


def upsert_post(conn: sqlite3.Connection, post: ForumPost) -> None:
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
    conn.commit()


def upsert_reply(conn: sqlite3.Connection, reply: ForumReply) -> None:
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
    conn.commit()
