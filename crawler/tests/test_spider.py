from __future__ import annotations

import logging
from pathlib import Path

import scrapy
from scrapy.http import TextResponse

from wxc_cfzh_crawler.db import (
    fetch_frontier_row,
    fetch_replies,
    fetch_root_posts,
    upsert_frontier_entry,
)
from wxc_cfzh_crawler.models import FrontierRecord
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


def request_post_ids(results: list[object]) -> list[str]:
    return [result.meta["post_id"] for result in results if isinstance(result, scrapy.Request)]


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
    assert "frontier posts pending=0 in_progress=0 done=0 failed=1" in messages
    assert "\r\x1b[K" in stream.writes
    assert "failed=1" in stream.text
