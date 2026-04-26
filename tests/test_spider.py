from __future__ import annotations

from pathlib import Path

import scrapy
from scrapy.http import TextResponse

from wxc_cfzh_crawler.spiders.cfzh import CfzhSpider

FIXTURES = Path(__file__).parent / "fixtures"


def response_for(name: str, url: str) -> TextResponse:
    body = (FIXTURES / name).read_bytes()
    request = scrapy.Request(url, meta={})
    return TextResponse(url=url, body=body, encoding="utf-8", request=request)


def request_post_ids(results: list[object]) -> list[str]:
    return [result.meta["post_id"] for result in results if isinstance(result, scrapy.Request)]


def test_parse_index_schedules_non_sticky_frontier_posts_and_replies(tmp_path: Path) -> None:
    spider = CfzhSpider(pages=1, database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    response = response_for("forum_index.html", "https://bbs.wenxuecity.com/cfzh/")

    results = list(spider.parse_index(response, page_number=1))

    assert request_post_ids(results) == ["100", "200", "101", "102"]


def test_parse_root_post_schedules_replies_under_root(tmp_path: Path) -> None:
    spider = CfzhSpider(pages=1, database_url=f"sqlite:///{tmp_path / 'crawler.sqlite3'}")
    response = response_for("thread.html", "https://bbs.wenxuecity.com/cfzh/100.html")

    results = list(spider.parse_root_post(response))
    requests = [result for result in results if isinstance(result, scrapy.Request)]
    items = [result for result in results if not isinstance(result, scrapy.Request)]

    assert any(item.get("item_type") == "post" and item.get("post_id") == "100" for item in items)
    assert [request.meta["reply_id"] for request in requests] == ["101", "102"]
    assert [request.meta["root_post_id"] for request in requests] == ["100", "100"]
    assert [request.meta["parent_id"] for request in requests] == ["100", "101"]
