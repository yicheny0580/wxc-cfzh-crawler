from __future__ import annotations

import sqlite3
from datetime import datetime

import pytest

from wxc_cfzh_crawler.db import (
    claim_next_frontier,
    connect,
    fetch_frontier_row,
    fetch_replies,
    fetch_root_posts,
    mark_frontier_done,
    reset_in_progress_frontier,
    save_post_detail,
    save_reply_detail,
    sqlite_path_from_url,
    upsert_frontier_entry,
    upsert_post,
    upsert_reply,
)
from wxc_cfzh_crawler.export import build_posts_with_replies
from wxc_cfzh_crawler.models import ForumPost, ForumReply, FrontierRecord


def test_sqlite_path_supports_project_relative_and_absolute_urls() -> None:
    assert (
        sqlite_path_from_url("sqlite:///data/crawler.sqlite3").as_posix()
        == "data/crawler.sqlite3"
    )
    assert (
        sqlite_path_from_url("sqlite:////tmp/crawler.sqlite3").as_posix()
        == "/tmp/crawler.sqlite3"
    )


def test_sqlite_post_upsert_is_idempotent(tmp_path) -> None:
    conn = connect(f"sqlite:///{tmp_path / 'crawler.sqlite3'}")

    post = ForumPost(
        post_id="100",
        url="https://bbs.wenxuecity.com/cfzh/100.html",
        title="Root A",
        published_at=datetime(2026, 4, 25, 8, 39, 22),
    )
    upsert_post(conn, post)
    upsert_post(conn, post.model_copy(update={"title": "Root A updated"}))

    rows = fetch_root_posts(conn)
    assert len(rows) == 1
    assert rows[0]["title"] == "Root A updated"


def test_sqlite_reply_upsert_is_idempotent(tmp_path) -> None:
    conn = connect(f"sqlite:///{tmp_path / 'crawler.sqlite3'}")

    reply = ForumReply(
        reply_id="101",
        root_post_id="100",
        url="https://bbs.wenxuecity.com/cfzh/101.html",
        title="Reply A",
        published_at=datetime(2026, 4, 25, 8, 51, 0),
        depth=1,
        forum_order=1,
    )
    upsert_reply(conn, reply)
    upsert_reply(conn, reply.model_copy(update={"title": "Reply A updated"}))

    rows = fetch_replies(conn, root_post_id="100")
    assert len(rows) == 1
    assert rows[0]["title"] == "Reply A updated"


def test_frontier_claim_and_done_transition(tmp_path) -> None:
    conn = connect(f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    upsert_frontier_entry(
        conn,
        FrontierRecord(
            post_id="100",
            url="https://bbs.wenxuecity.com/cfzh/100.html",
            record_type="post",
            root_post_id="100",
            listing_title="Root A",
        ),
    )

    claimed = claim_next_frontier(conn)
    assert claimed is not None
    assert claimed["post_id"] == "100"
    assert claimed["status"] == "in_progress"
    assert claimed["attempts"] == 1

    mark_frontier_done(conn, "100", http_status=200)
    row = fetch_frontier_row(conn, "100")
    assert row is not None
    assert row["status"] == "done"
    assert row["last_http_status"] == 200


def test_reset_in_progress_frontier_restores_pending_without_spending_attempt(
    tmp_path,
) -> None:
    conn = connect(f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    upsert_frontier_entry(
        conn,
        FrontierRecord(
            post_id="100",
            url="https://bbs.wenxuecity.com/cfzh/100.html",
            record_type="post",
            root_post_id="100",
        ),
    )

    claim_next_frontier(conn)
    reset_in_progress_frontier(conn)

    row = fetch_frontier_row(conn, "100")
    assert row is not None
    assert row["status"] == "pending"
    assert row["attempts"] == 0


def test_frontier_delta_refresh_marks_root_and_known_replies_pending(tmp_path) -> None:
    conn = connect(f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    upsert_post(
        conn,
        ForumPost(
            post_id="100",
            url="https://bbs.wenxuecity.com/cfzh/100.html",
            title="Root A",
            reply_count=2,
        ),
    )
    for record in [
        FrontierRecord(
            post_id="100",
            url="https://bbs.wenxuecity.com/cfzh/100.html",
            record_type="post",
            root_post_id="100",
            listing_reply_count=2,
        ),
        FrontierRecord(
            post_id="101",
            url="https://bbs.wenxuecity.com/cfzh/101.html",
            record_type="reply",
            root_post_id="100",
            depth=1,
        ),
        FrontierRecord(
            post_id="102",
            url="https://bbs.wenxuecity.com/cfzh/102.html",
            record_type="reply",
            root_post_id="100",
            parent_reply_id="101",
            depth=2,
        ),
        FrontierRecord(
            post_id="200",
            url="https://bbs.wenxuecity.com/cfzh/200.html",
            record_type="post",
            root_post_id="200",
            listing_reply_count=1,
        ),
        FrontierRecord(
            post_id="201",
            url="https://bbs.wenxuecity.com/cfzh/201.html",
            record_type="reply",
            root_post_id="200",
            depth=1,
        ),
    ]:
        upsert_frontier_entry(conn, record)

    while row := claim_next_frontier(conn):
        mark_frontier_done(conn, str(row["post_id"]), http_status=200)

    upsert_frontier_entry(
        conn,
        FrontierRecord(
            post_id="100",
            url="https://bbs.wenxuecity.com/cfzh/100.html",
            record_type="post",
            root_post_id="100",
            listing_reply_count=3,
        ),
    )

    for post_id in ("100", "101", "102"):
        row = fetch_frontier_row(conn, post_id)
        assert row is not None
        assert row["status"] == "pending"
        assert row["attempts"] == 0

    for post_id in ("200", "201"):
        row = fetch_frontier_row(conn, post_id)
        assert row is not None
        assert row["status"] == "done"
        assert row["attempts"] == 1


def test_frontier_backfills_existing_posts_and_replies(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'crawler.sqlite3'}"
    conn = connect(db_url)
    upsert_post(
        conn,
        ForumPost(post_id="100", url="https://bbs.wenxuecity.com/cfzh/100.html"),
    )
    upsert_reply(
        conn,
        ForumReply(
            reply_id="101",
            root_post_id="100",
            url="https://bbs.wenxuecity.com/cfzh/101.html",
            depth=1,
        ),
    )
    conn.close()

    conn = connect(db_url)
    post_row = fetch_frontier_row(conn, "100")
    reply_row = fetch_frontier_row(conn, "101")

    assert post_row is not None
    assert post_row["status"] == "done"
    assert post_row["record_type"] == "post"
    assert reply_row is not None
    assert reply_row["status"] == "done"
    assert reply_row["record_type"] == "reply"


def test_save_post_detail_persists_record_children_and_done_atomically(tmp_path) -> None:
    conn = connect(f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    upsert_frontier_entry(
        conn,
        FrontierRecord(
            post_id="100",
            url="https://bbs.wenxuecity.com/cfzh/100.html",
            record_type="post",
            root_post_id="100",
        ),
    )
    claim_next_frontier(conn)

    save_post_detail(
        conn,
        ForumPost(post_id="100", url="https://bbs.wenxuecity.com/cfzh/100.html"),
        [
            FrontierRecord(
                post_id="101",
                url="https://bbs.wenxuecity.com/cfzh/101.html",
                record_type="reply",
                root_post_id="100",
                depth=1,
            )
        ],
        frontier_post_id="100",
        http_status=200,
    )

    assert len(fetch_root_posts(conn)) == 1
    parent_row = fetch_frontier_row(conn, "100")
    child_row = fetch_frontier_row(conn, "101")
    assert parent_row is not None
    assert parent_row["status"] == "done"
    assert child_row is not None
    assert child_row["status"] == "pending"


def test_save_reply_detail_persists_record_children_and_done_atomically(tmp_path) -> None:
    conn = connect(f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    upsert_frontier_entry(
        conn,
        FrontierRecord(
            post_id="101",
            url="https://bbs.wenxuecity.com/cfzh/101.html",
            record_type="reply",
            root_post_id="100",
            depth=1,
        ),
    )
    claim_next_frontier(conn)

    save_reply_detail(
        conn,
        ForumReply(
            reply_id="101",
            root_post_id="100",
            url="https://bbs.wenxuecity.com/cfzh/101.html",
            depth=1,
        ),
        [
            FrontierRecord(
                post_id="102",
                url="https://bbs.wenxuecity.com/cfzh/102.html",
                record_type="reply",
                root_post_id="100",
                parent_reply_id="101",
                depth=2,
            )
        ],
        frontier_post_id="101",
        http_status=200,
    )

    assert len(fetch_replies(conn, root_post_id="100")) == 1
    parent_row = fetch_frontier_row(conn, "101")
    child_row = fetch_frontier_row(conn, "102")
    assert parent_row is not None
    assert parent_row["status"] == "done"
    assert child_row is not None
    assert child_row["status"] == "pending"


def test_save_post_detail_rolls_back_when_child_frontier_fails(tmp_path) -> None:
    conn = connect(f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    upsert_frontier_entry(
        conn,
        FrontierRecord(
            post_id="100",
            url="https://bbs.wenxuecity.com/cfzh/100.html",
            record_type="post",
            root_post_id="100",
        ),
    )
    claim_next_frontier(conn)

    with pytest.raises(sqlite3.IntegrityError):
        save_post_detail(
            conn,
            ForumPost(post_id="100", url="https://bbs.wenxuecity.com/cfzh/100.html"),
            [
                FrontierRecord(
                    post_id="101",
                    url="https://bbs.wenxuecity.com/cfzh/101.html",
                    record_type="reply",
                    root_post_id="100",
                    depth=1,
                ),
                FrontierRecord(
                    post_id="102",
                    url="https://bbs.wenxuecity.com/cfzh/101.html",
                    record_type="reply",
                    root_post_id="100",
                    depth=1,
                ),
            ],
            frontier_post_id="100",
            http_status=200,
        )

    assert fetch_root_posts(conn) == []
    parent_row = fetch_frontier_row(conn, "100")
    assert parent_row is not None
    assert parent_row["status"] == "in_progress"
    assert fetch_frontier_row(conn, "101") is None
    assert fetch_frontier_row(conn, "102") is None


def test_build_posts_with_replies_preserves_nested_replies() -> None:
    posts = [
        {"post_id": "100", "title": "Root"},
    ]
    replies = [
        {"reply_id": "101", "root_post_id": "100", "parent_reply_id": None, "title": "Reply"},
        {"reply_id": "102", "root_post_id": "100", "parent_reply_id": "101", "title": "Nested"},
    ]

    records = build_posts_with_replies(posts, replies)

    assert records[0]["post_id"] == "100"
    assert records[0]["replies"][0]["reply_id"] == "101"
    assert records[0]["replies"][0]["replies"][0]["reply_id"] == "102"
