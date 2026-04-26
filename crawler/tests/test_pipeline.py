from __future__ import annotations

import sqlite3

from wxc_cfzh_crawler.db import (
    claim_next_frontier,
    connect,
    fetch_crawl_progress,
    save_post_detail,
    save_reply_detail,
    upsert_frontier_entry,
)
from wxc_cfzh_crawler.models import ForumPost, ForumReply, FrontierRecord
from wxc_cfzh_crawler.progress import (
    configure_crawl_progress_reporter,
    get_crawl_progress_reporter,
    reset_crawl_progress_reporter,
)


class StreamBuffer:
    def __init__(self) -> None:
        self.writes: list[str] = []

    def isatty(self) -> bool:
        return True

    def write(self, value: str) -> int:
        self.writes.append(value)
        return len(value)

    def flush(self) -> None:
        pass

    @property
    def text(self) -> str:
        return "".join(self.writes)


class ProgressSpider:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.scheduled_detail_requests = 2
        self.max_requests = 5

    def update_progress(self) -> None:
        get_crawl_progress_reporter().update_progress(
            fetch_crawl_progress(self.conn),
            scheduled=self.scheduled_detail_requests,
            max_requests=self.max_requests,
        )


def test_atomic_detail_persistence_updates_live_post_and_reply_progress(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'crawler.sqlite3'}"
    conn = connect(db_url)
    post_frontier = FrontierRecord(
        post_id="100",
        url="https://bbs.wenxuecity.com/cfzh/100.html",
        record_type="post",
        root_post_id="100",
    )
    reply_frontier = FrontierRecord(
        post_id="101",
        url="https://bbs.wenxuecity.com/cfzh/101.html",
        record_type="reply",
        root_post_id="100",
        depth=1,
    )
    upsert_frontier_entry(conn, post_frontier)
    upsert_frontier_entry(conn, reply_frontier)
    claim_next_frontier(conn)
    claim_next_frontier(conn)

    stream = StreamBuffer()
    spider = ProgressSpider(conn)
    configure_crawl_progress_reporter(mode="live", stream=stream)
    try:
        save_post_detail(
            conn,
            ForumPost(post_id="100", url="https://bbs.wenxuecity.com/cfzh/100.html"),
            [],
            frontier_post_id="100",
            http_status=200,
        )
        spider.update_progress()
        save_reply_detail(
            conn,
            ForumReply(
                reply_id="101",
                root_post_id="100",
                url="https://bbs.wenxuecity.com/cfzh/101.html",
                depth=1,
            ),
            [],
            frontier_post_id="101",
            http_status=200,
        )
        spider.update_progress()
    finally:
        reset_crawl_progress_reporter()
        conn.close()

    assert "CFZH saved posts=1 replies=0" in stream.text
    assert "CFZH saved posts=1 replies=1" in stream.text
    assert "pending posts=0 replies=0" in stream.text
    assert "scheduled=2/5" in stream.text
