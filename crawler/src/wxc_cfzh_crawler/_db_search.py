from __future__ import annotations

import sqlite3

from wxc_cfzh_crawler.models import ForumPost, ForumReply


def numeric_rowid(value: str) -> int | None:
    if not value.isdecimal():
        return None
    return int(value)


def init_search_index(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
            post_id UNINDEXED,
            title,
            author,
            body_text,
            tokenize = 'trigram'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS replies_fts USING fts5(
            reply_id UNINDEXED,
            root_post_id UNINDEXED,
            title,
            author,
            body_text,
            tokenize = 'trigram'
        );
        """
    )


def backfill_search_index(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        INSERT INTO posts_fts(rowid, post_id, title, author, body_text)
        SELECT CAST(p.post_id AS INTEGER), p.post_id, p.title, p.author, p.body_text
        FROM posts p
        WHERE p.post_id GLOB '[0-9]*'
            AND NOT EXISTS (
                SELECT 1 FROM posts_fts f WHERE f.rowid = CAST(p.post_id AS INTEGER)
            );

        INSERT INTO replies_fts(rowid, reply_id, root_post_id, title, author, body_text)
        SELECT
            CAST(r.reply_id AS INTEGER),
            r.reply_id,
            r.root_post_id,
            r.title,
            r.author,
            r.body_text
        FROM replies r
        WHERE r.reply_id GLOB '[0-9]*'
            AND NOT EXISTS (
                SELECT 1 FROM replies_fts f WHERE f.rowid = CAST(r.reply_id AS INTEGER)
            );
        """
    )


def upsert_post_search(conn: sqlite3.Connection, post: ForumPost) -> None:
    rowid = numeric_rowid(post.post_id)
    if rowid is None:
        return
    conn.execute("DELETE FROM posts_fts WHERE rowid = ?", (rowid,))
    conn.execute(
        """
        INSERT INTO posts_fts(rowid, post_id, title, author, body_text)
        VALUES (?, ?, ?, ?, ?)
        """,
        (rowid, post.post_id, post.title, post.author, post.body_text),
    )


def upsert_reply_search(conn: sqlite3.Connection, reply: ForumReply) -> None:
    rowid = numeric_rowid(reply.reply_id)
    if rowid is None:
        return
    conn.execute("DELETE FROM replies_fts WHERE rowid = ?", (rowid,))
    conn.execute(
        """
        INSERT INTO replies_fts(rowid, reply_id, root_post_id, title, author, body_text)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            rowid,
            reply.reply_id,
            reply.root_post_id,
            reply.title,
            reply.author,
            reply.body_text,
        ),
    )
