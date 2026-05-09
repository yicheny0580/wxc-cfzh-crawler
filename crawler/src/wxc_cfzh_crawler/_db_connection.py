from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import unquote, urlparse

from wxc_cfzh_crawler._db_search import backfill_search_index, init_search_index


def sqlite_path_from_url(database_url: str) -> Path:
    parsed = urlparse(database_url)
    if parsed.scheme in {"", "sqlite"}:
        if parsed.scheme == "":
            return Path(database_url)
        if parsed.netloc and parsed.netloc != "":
            raise ValueError(f"Only local SQLite URLs are supported: {database_url}")
        path = unquote(parsed.path)
        if path.startswith("//"):
            return Path(path[1:])
        return Path(path.lstrip("/"))
    raise ValueError(f"Unsupported DATABASE_URL scheme for local scaffold: {parsed.scheme}")


def connect(database_url: str) -> sqlite3.Connection:
    db_path = sqlite_path_from_url(database_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;

        DROP TABLE IF EXISTS pages;

        CREATE TABLE IF NOT EXISTS posts (
            post_id TEXT PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            forum TEXT NOT NULL,
            title TEXT,
            author TEXT,
            author_profile_url TEXT,
            published_at TEXT,
            edited_at TEXT,
            body_text TEXT,
            body_html TEXT,
            byte_count INTEGER,
            read_count INTEGER,
            reply_count INTEGER,
            crawled_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS replies (
            reply_id TEXT PRIMARY KEY,
            root_post_id TEXT NOT NULL,
            parent_reply_id TEXT,
            url TEXT NOT NULL UNIQUE,
            forum TEXT NOT NULL,
            title TEXT,
            author TEXT,
            author_profile_url TEXT,
            published_at TEXT,
            edited_at TEXT,
            body_text TEXT,
            body_html TEXT,
            byte_count INTEGER,
            read_count INTEGER,
            depth INTEGER NOT NULL DEFAULT 1,
            forum_order INTEGER,
            crawled_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS frontier (
            post_id TEXT PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            record_type TEXT NOT NULL CHECK(record_type IN ('post', 'reply')),
            root_post_id TEXT,
            parent_reply_id TEXT,
            depth INTEGER NOT NULL DEFAULT 0,
            forum_order INTEGER,
            listing_title TEXT,
            listing_reply_count INTEGER,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'in_progress', 'done', 'failed')),
            attempts INTEGER NOT NULL DEFAULT 0,
            discovered_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_fetched_at TEXT,
            last_http_status INTEGER,
            last_error TEXT,
            suppressed_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_posts_published_at ON posts(published_at);
        CREATE INDEX IF NOT EXISTS idx_replies_root_post_id ON replies(root_post_id);
        CREATE INDEX IF NOT EXISTS idx_replies_parent_reply_id ON replies(parent_reply_id);
        CREATE INDEX IF NOT EXISTS idx_replies_published_at ON replies(published_at);
        CREATE INDEX IF NOT EXISTS idx_frontier_status ON frontier(status);
        CREATE INDEX IF NOT EXISTS idx_frontier_root_post_id ON frontier(root_post_id);
        """
    )
    ensure_frontier_columns(conn)
    init_search_index(conn)
    backfill_frontier(conn)
    backfill_search_index(conn)
    conn.commit()


def ensure_frontier_columns(conn: sqlite3.Connection) -> None:
    columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(frontier)")}
    if "suppressed_at" not in columns:
        conn.execute("ALTER TABLE frontier ADD COLUMN suppressed_at TEXT")


def backfill_frontier(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        INSERT OR IGNORE INTO frontier (
            post_id, url, record_type, root_post_id, parent_reply_id, depth, forum_order,
            listing_title, listing_reply_count, status, attempts, discovered_at, updated_at,
            last_fetched_at, last_http_status, last_error, suppressed_at
        )
        SELECT
            post_id, url, 'post', post_id, NULL, 0, NULL, title, reply_count, 'done', 0,
            crawled_at, crawled_at, crawled_at, 200, NULL, NULL
        FROM posts;

        INSERT OR IGNORE INTO frontier (
            post_id, url, record_type, root_post_id, parent_reply_id, depth, forum_order,
            listing_title, listing_reply_count, status, attempts, discovered_at, updated_at,
            last_fetched_at, last_http_status, last_error, suppressed_at
        )
        SELECT
            reply_id, url, 'reply', root_post_id, parent_reply_id, depth, forum_order,
            title, NULL, 'done', 0,
            crawled_at, crawled_at, crawled_at, 200, NULL, NULL
        FROM replies;
        """
    )
