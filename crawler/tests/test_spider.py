from __future__ import annotations

import logging
from pathlib import Path

import scrapy
from scrapy.http import TextResponse

from wxc_cfzh_crawler.db import (
    claim_next_frontier,
    fetch_frontier_row,
    fetch_replies,
    fetch_root_posts,
    mark_frontier_done,
    mark_frontier_failed,
    upsert_frontier_entry,
    upsert_post,
)
from wxc_cfzh_crawler.models import ForumPost, FrontierRecord
from wxc_cfzh_crawler.progress import (
    configure_crawl_progress_reporter,
    reset_crawl_progress_reporter,
)
from wxc_cfzh_crawler.spiders.cfzh import CfzhSpider

FIXTURES = Path(__file__).parent / "fixtures"


def response_for(name: str, url: str) -> TextResponse:
    body = (FIXTURES / name).read_bytes()
    request = scrapy.Request(url, meta={})
    return TextResponse(url=url, body=body, encoding="utf-8", request=request)


def response_from_html(html: str, url: str) -> TextResponse:
    request = scrapy.Request(url, meta={})
    return TextResponse(url=url, body=html.encode(), encoding="utf-8", request=request)


def request_post_ids(results: list[object]) -> list[str]:
    return [result.meta["post_id"] for result in results if isinstance(result, scrapy.Request)]


def mark_pending_frontier_done(spider: CfzhSpider) -> None:
    while row := claim_next_frontier(spider.frontier_conn()):
        mark_frontier_done(spider.frontier_conn(), str(row["post_id"]), http_status=200)


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


def test_parse_index_schedules_non_sticky_frontier_posts_and_replies(tmp_path: Path) -> None:
    spider = CfzhSpider(pages=1, database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    response = response_for("forum_index.html", "https://bbs.wenxuecity.com/cfzh/")

    results = list(spider.parse_index(response, page_number=1))

    assert request_post_ids(results) == ["100", "200", "101", "102"]


def test_parse_index_skips_zero_byte_leaf_details(tmp_path: Path) -> None:
    spider = CfzhSpider(pages=1, database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    response = response_from_html(
        """
        <!doctype html>
        <html>
          <body>
            <div id="postlist">
              <p style="margin:2px 0 17px 0px; width:705px">
                * <a href="/cfzh/100.html" class="post">Root A</a>
                - <a href="//passport.wenxuecity.com/profile.php?cid=author-a">
                  Author A
                </a>
                - M (570 bytes) (12 reads) 04/26/2026 08:00:00 (2)
              </p>
              <p style="margin:2px 0 2px 20px; width:683px">
                * <a href="/cfzh/101.html" class="post">Reply A1</a>
                - Author B - F (0 bytes) (2 reads) 04/26/2026 08:01:00 (1)
              </p>
              <p style="margin:2px 0 2px 40px; width:661px">
                * <a href="/cfzh/102.html" class="post">Reply A1a</a>
                - Author C - M (0 bytes) (1 reads) 04/26/2026 08:02:00
              </p>
              <p style="margin:2px 0 17px 0px; width:705px">
                * <a href="/cfzh/200.html" class="post">Root B</a>
                - Author D - F (0 bytes) (3 reads) 04/26/2026 08:03:00
              </p>
              <p style="margin:2px 0 17px 0px; width:705px">
                * <a href="/cfzh/300.html" class="post">Root C</a>
                - Author E - M (12 bytes) (4 reads) 04/26/2026 08:04:00
              </p>
            </div>
          </body>
        </html>
        """,
        "https://bbs.wenxuecity.com/cfzh/",
    )

    results = list(spider.parse_index(response, page_number=1))

    assert request_post_ids(results) == ["100", "300", "101"]
    replies = fetch_replies(spider.frontier_conn(), root_post_id="100")
    posts = fetch_root_posts(spider.frontier_conn())
    assert [reply["reply_id"] for reply in replies] == ["102"]
    assert replies[0]["parent_reply_id"] == "101"
    assert replies[0]["byte_count"] == 0
    assert [post["post_id"] for post in posts] == ["200"]
    assert posts[0]["byte_count"] == 0

    for post_id in ("102", "200"):
        row = fetch_frontier_row(spider.frontier_conn(), post_id)
        assert row is not None
        assert row["status"] == "done"
        assert row["last_http_status"] is None


def test_parse_index_keeps_replies_under_sticky_duplicate_root(tmp_path: Path) -> None:
    spider = CfzhSpider(pages=1, database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    response = response_from_html(
        """
        <!doctype html>
        <html>
          <body>
            <div id="postlist">
              <a href="/cfzh/100.html" class="sticky">Root A sticky</a>
              <p style="margin:2px 0 17px 0px; width:705px">
                * <a href="/cfzh/200.html" class="post">Root B</a>
                - M (12 bytes) (3 reads) 04/26/2026 08:00:00
              </p>
              <p style="margin:2px 0 17px 0px; width:705px">
                * <a href="/cfzh/100.html" class="post">Root A</a>
                - M (12 bytes) (4 reads) 04/26/2026 08:01:00 (1)
              </p>
              <p style="margin:2px 0 2px 20px; width:683px">
                * <a href="/cfzh/101.html" class="post">Reply A1</a>
                - F (0 bytes) (1 reads) 04/26/2026 08:02:00
              </p>
            </div>
          </body>
        </html>
        """,
        "https://bbs.wenxuecity.com/cfzh/",
    )

    results = list(spider.parse_index(response, page_number=1))

    assert request_post_ids(results) == ["200", "100"]
    assert fetch_replies(spider.frontier_conn(), root_post_id="200") == []
    replies = fetch_replies(spider.frontier_conn(), root_post_id="100")
    assert [reply["reply_id"] for reply in replies] == ["101"]
    assert replies[0]["parent_reply_id"] is None


def test_parse_index_updates_live_progress(tmp_path: Path) -> None:
    spider = CfzhSpider(pages=1, database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    response = response_for("forum_index.html", "https://bbs.wenxuecity.com/cfzh/")
    stream = StreamBuffer()

    configure_crawl_progress_reporter(mode="live", stream=stream)
    try:
        list(spider.parse_index(response, page_number=1))
    finally:
        reset_crawl_progress_reporter()

    assert "CFZH saved posts=0 replies=0" in stream.text
    assert "pending posts=0 replies=0" in stream.text
    assert "active=4" in stream.text
    assert "scheduled=4/unlimited" in stream.text


def test_parse_index_schedules_changed_root_and_reopened_replies(tmp_path: Path) -> None:
    spider = CfzhSpider(pages=1, database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    conn = spider.frontier_conn()
    upsert_post(
        conn,
        ForumPost(
            post_id="100",
            url="https://bbs.wenxuecity.com/cfzh/100.html",
            reply_count=2,
        ),
    )
    upsert_post(
        conn,
        ForumPost(
            post_id="200",
            url="https://bbs.wenxuecity.com/cfzh/200.html",
            reply_count=1,
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
    mark_pending_frontier_done(spider)

    response = response_from_html(
        """
        <!doctype html>
        <html>
          <body>
            <div id="postlist">
              <p><a href="/cfzh/100.html" class="post">Root A (3)</a></p>
              <p><a href="/cfzh/200.html" class="post">Root B (1)</a></p>
            </div>
          </body>
        </html>
        """,
        "https://bbs.wenxuecity.com/cfzh/",
    )

    results = list(spider.parse_index(response, page_number=1))

    assert request_post_ids(results) == ["100", "101", "102"]
    for post_id in ("100", "101", "102"):
        row = fetch_frontier_row(conn, post_id)
        assert row is not None
        assert row["status"] == "in_progress"
    for post_id in ("200", "201"):
        row = fetch_frontier_row(conn, post_id)
        assert row is not None
        assert row["status"] == "done"


def test_parse_index_requeues_failed_frontier_without_listing_rediscovery(
    tmp_path: Path,
) -> None:
    spider = CfzhSpider(
        pages=1,
        max_requests=1,
        database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}",
    )
    conn = spider.frontier_conn()
    upsert_frontier_entry(
        conn,
        FrontierRecord(
            post_id="999",
            url="https://bbs.wenxuecity.com/cfzh/999.html",
            record_type="post",
            root_post_id="999",
            listing_title="Previously failed",
        ),
    )
    claimed = claim_next_frontier(conn)
    assert claimed is not None
    mark_frontier_failed(conn, "999", http_status=500, error="temporary upstream error")
    conn.execute("UPDATE frontier SET attempts = 3 WHERE post_id = '999'")
    conn.commit()
    response = response_from_html(
        """
        <!doctype html>
        <html>
          <body><div id="postlist"></div></body>
        </html>
        """,
        "https://bbs.wenxuecity.com/cfzh/",
    )

    results = list(spider.parse_index(response, page_number=1))

    assert request_post_ids(results) == ["999"]
    row = fetch_frontier_row(conn, "999")
    assert row is not None
    assert row["status"] == "in_progress"
    assert row["attempts"] == 4


def test_parse_index_does_not_requeue_suppressed_frontier(tmp_path: Path) -> None:
    spider = CfzhSpider(
        pages=1,
        max_requests=1,
        database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}",
    )
    conn = spider.frontier_conn()
    upsert_frontier_entry(
        conn,
        FrontierRecord(
            post_id="999",
            url="https://bbs.wenxuecity.com/cfzh/999.html",
            record_type="post",
            root_post_id="999",
            listing_title="Previously failed",
        ),
    )
    claim_next_frontier(conn)
    mark_frontier_failed(conn, "999", http_status=500, error="persistent upstream error")
    conn.execute("UPDATE frontier SET attempts = 5, suppressed_at = NULL WHERE post_id = '999'")
    conn.commit()
    response = response_from_html(
        """
        <!doctype html>
        <html>
          <body><div id="postlist"></div></body>
        </html>
        """,
        "https://bbs.wenxuecity.com/cfzh/",
    )

    results = list(spider.parse_index(response, page_number=1))

    assert request_post_ids(results) == []
    row = fetch_frontier_row(conn, "999")
    assert row is not None
    assert row["status"] == "failed"
    assert row["attempts"] == 5
    assert row["suppressed_at"] is not None


def test_parse_root_post_saves_atomically_and_schedules_replies(tmp_path: Path) -> None:
    spider = CfzhSpider(pages=1, database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    response = response_for("thread.html", "https://bbs.wenxuecity.com/cfzh/100.html")

    results = list(spider.parse_root_post(response))
    requests = [result for result in results if isinstance(result, scrapy.Request)]
    items = [result for result in results if not isinstance(result, scrapy.Request)]

    assert items == []
    posts = fetch_root_posts(spider.frontier_conn())
    assert [post["post_id"] for post in posts] == ["100"]
    assert [request.meta["reply_id"] for request in requests] == ["101", "102"]
    assert [request.meta["root_post_id"] for request in requests] == ["100", "100"]
    assert [request.meta["parent_id"] for request in requests] == ["100", "101"]


def test_parse_root_post_skips_zero_byte_leaf_child_replies(tmp_path: Path) -> None:
    spider = CfzhSpider(pages=1, database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    response = response_from_html(
        """
        <!doctype html>
        <html>
          <body>
            <h1 class="title">Root A</h1>
            <div id="postmeta">
              <a href="//passport.wenxuecity.com/profile.php?cid=author-a"
                 class="username"><span>Author A</span></a>
              at <span class="date">2026-04-26 08:00:00</span>
              <small>Read count : <strong><span id="countnum">12</span></strong>
                (570 bytes)</small>
            </div>
            <div id="msgbodyContent"><p>Root body text</p></div>
            <div id="comment">
              <div id="postlist">
                <p style="margin:2px 0 2px 0px;">
                  * <a href="/cfzh/101.html" class="post">Empty leaf</a>
                  - Author B - F (0 bytes) () 04/26/2026 postreply 08:01:00
                </p>
                <p style="margin:2px 0 2px 0px;">
                  * <a href="/cfzh/102.html" class="post">Non-empty leaf</a>
                  - Author C - M (12 bytes) () 04/26/2026 postreply 08:02:00
                </p>
              </div>
            </div>
          </body>
        </html>
        """,
        "https://bbs.wenxuecity.com/cfzh/100.html",
    )

    results = list(spider.parse_root_post(response))

    assert request_post_ids(results) == ["102"]
    replies = fetch_replies(spider.frontier_conn(), root_post_id="100")
    assert [reply["reply_id"] for reply in replies] == ["101"]
    assert replies[0]["byte_count"] == 0
    skipped_row = fetch_frontier_row(spider.frontier_conn(), "101")
    scheduled_row = fetch_frontier_row(spider.frontier_conn(), "102")
    assert skipped_row is not None
    assert skipped_row["status"] == "done"
    assert scheduled_row is not None
    assert scheduled_row["status"] == "in_progress"


def test_parse_reply_saves_atomically_and_schedules_nested_replies(tmp_path: Path) -> None:
    spider = CfzhSpider(pages=1, database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    request = scrapy.Request(
        "https://bbs.wenxuecity.com/cfzh/102.html",
        meta={
            "frontier_post_id": "102",
            "reply_id": "102",
            "root_post_id": "100",
            "parent_id": "101",
            "reply_depth": 2,
        },
    )
    response = TextResponse(
        url=request.url,
        body=(FIXTURES / "reply.html").read_bytes(),
        encoding="utf-8",
        request=request,
    )

    results = list(spider.parse_reply(response))

    assert results == []
    replies = fetch_replies(spider.frontier_conn(), root_post_id="100")
    assert [reply["reply_id"] for reply in replies] == ["102"]
    assert replies[0]["parent_reply_id"] == "101"


def test_parse_root_post_rejects_sparse_detail_response(tmp_path: Path) -> None:
    spider = CfzhSpider(pages=1, database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    upsert_frontier_entry(
        spider.frontier_conn(),
        FrontierRecord(
            post_id="999",
            url="https://bbs.wenxuecity.com/cfzh/999.html",
            record_type="post",
            root_post_id="999",
        ),
    )
    request = scrapy.Request(
        "https://bbs.wenxuecity.com/cfzh/999.html",
        meta={"frontier_post_id": "999"},
    )
    response = TextResponse(
        url=request.url,
        body=b"<!doctype html><html><body>loading...</body></html>",
        encoding="utf-8",
        request=request,
    )

    results = list(spider.parse_root_post(response))

    assert results == []
    assert fetch_root_posts(spider.frontier_conn()) == []
    row = fetch_frontier_row(spider.frontier_conn(), "999")
    assert row is not None
    assert row["status"] == "failed"
    assert row["last_http_status"] == 200
    assert "No parseable post detail" in str(row["last_error"])


def test_parse_failure_logs_failed_progress(tmp_path: Path, caplog) -> None:
    spider = CfzhSpider(pages=1, database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    stream = StreamBuffer()
    upsert_frontier_entry(
        spider.frontier_conn(),
        FrontierRecord(
            post_id="999",
            url="https://bbs.wenxuecity.com/cfzh/",
            record_type="post",
            root_post_id="999",
        ),
    )
    request = scrapy.Request(
        "https://bbs.wenxuecity.com/cfzh/",
        meta={"frontier_post_id": "999"},
    )
    response = TextResponse(url=request.url, body=b"", encoding="utf-8", request=request)

    configure_crawl_progress_reporter(mode="live", stream=stream)
    try:
        spider.update_progress()
        with caplog.at_level(logging.WARNING):
            list(spider.parse_root_post(response))
    finally:
        reset_crawl_progress_reporter()

    row = fetch_frontier_row(spider.frontier_conn(), "999")
    assert row is not None
    assert row["status"] == "failed"
    messages = "\n".join(caplog.messages)
    assert "CFZH failed post id=999 status=200" in messages
    assert (
        "frontier posts pending=0 in_progress=0 done=0 failed=1; "
        "frontier replies pending=0 in_progress=0 done=0 failed=0; "
        "suppressed posts=0 replies=0"
    ) in messages
    assert "\r\x1b[K" in stream.writes
    assert "failed=1 | suppressed=0" in stream.text
