from __future__ import annotations

import os
import sqlite3
from typing import Any
from urllib.parse import urlencode

import scrapy

from wxc_cfzh_crawler.db import (
    claim_next_frontier,
    connect,
    mark_frontier_failed,
    reset_in_progress_frontier,
    upsert_frontier_entry,
)
from wxc_cfzh_crawler.models import FrontierRecord
from wxc_cfzh_crawler.parsing import (
    PostListEntry,
    extract_comment_entries,
    extract_index_entries,
    extract_post_record,
    extract_reply_record,
    parse_reply_count,
    post_id_from_url,
)

DEFAULT_DATABASE_URL = "sqlite:///data/crawler.sqlite3"
MAX_FRONTIER_ATTEMPTS = 3


class CfzhSpider(scrapy.Spider):
    name = "cfzh"
    allowed_domains = ["bbs.wenxuecity.com"]

    def __init__(
        self,
        pages: str | int = 3,
        start_url: str = "https://bbs.wenxuecity.com/cfzh/",
        max_requests: str | int | None = None,
        max_posts: str | int | None = None,
        database_url: str | None = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.pages = max(1, int(pages))
        self.start_url = start_url
        self.max_requests = self.optional_positive_int(max_requests)
        if self.max_requests is None:
            self.max_requests = self.optional_positive_int(max_posts)
        self.database_url = database_url
        self.scheduled_detail_requests = 0
        self.conn: sqlite3.Connection | None = None
        self.frontier_prepared = False

    async def start(self):
        self.prepare_frontier()
        for page in range(1, self.pages + 1):
            yield scrapy.Request(
                self.index_url(page),
                callback=self.parse_index,
                cb_kwargs={"page_number": page},
            )

    def closed(self, reason: str) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def frontier_conn(self) -> sqlite3.Connection:
        if self.conn is None:
            settings = getattr(getattr(self, "crawler", None), "settings", None)
            database_url = self.database_url
            if database_url is None and settings is not None:
                database_url = settings.get("DATABASE_URL")
            if database_url is None:
                database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
            self.conn = connect(database_url)
        return self.conn

    def prepare_frontier(self) -> None:
        if self.frontier_prepared:
            return
        reset_in_progress_frontier(self.frontier_conn())
        self.frontier_prepared = True

    def index_url(self, page_number: int) -> str:
        if page_number == 1:
            return self.start_url
        separator = "&" if "?" in self.start_url else "?"
        return f"{self.start_url}{separator}{urlencode({'page': page_number})}"

    def parse_index(self, response: scrapy.http.Response, page_number: int):
        self.prepare_frontier()

        for entry in extract_index_entries(response):
            self.enqueue_frontier_entry(entry)

        yield from self.next_frontier_requests()

    def parse_root_post(self, response: scrapy.http.Response):
        try:
            post_item = extract_post_record(response, meta=response.meta)
        except Exception as exc:  # noqa: BLE001
            self.mark_response_failed(response, exc)
            yield from self.next_frontier_requests()
            return

        post_item["_frontier_post_id"] = (
            response.meta.get("frontier_post_id") or post_item["post_id"]
        )
        post_item["_http_status"] = response.status
        yield post_item

        root_post_id = str(post_item["post_id"])
        self.enqueue_comment_entries(
            response,
            root_post_id=root_post_id,
            base_parent_id=root_post_id,
            base_depth=0,
        )
        yield from self.next_frontier_requests()

    def parse_reply(self, response: scrapy.http.Response):
        try:
            reply_item = extract_reply_record(response, meta=response.meta)
        except Exception as exc:  # noqa: BLE001
            self.mark_response_failed(response, exc)
            yield from self.next_frontier_requests()
            return

        reply_item["_frontier_post_id"] = (
            response.meta.get("frontier_post_id") or reply_item["reply_id"]
        )
        reply_item["_http_status"] = response.status
        yield reply_item

        self.enqueue_comment_entries(
            response,
            root_post_id=str(reply_item["root_post_id"]),
            base_parent_id=str(reply_item["reply_id"]),
            base_depth=int(reply_item.get("depth") or 1),
        )
        yield from self.next_frontier_requests()

    def parse_post(self, response: scrapy.http.Response):
        yield from self.parse_root_post(response)

    def enqueue_comment_entries(
        self,
        response: scrapy.http.Response,
        *,
        root_post_id: str,
        base_parent_id: str,
        base_depth: int,
    ) -> None:
        for forum_order, entry in enumerate(
            extract_comment_entries(
                response,
                root_post_id=root_post_id,
                base_parent_id=base_parent_id,
                base_depth=base_depth,
            ),
            start=1,
        ):
            self.enqueue_frontier_entry(entry, forum_order=forum_order)

    def enqueue_frontier_entry(
        self,
        entry: PostListEntry,
        *,
        forum_order: int | None = None,
    ) -> None:
        upsert_frontier_entry(
            self.frontier_conn(),
            self.frontier_record_from_entry(entry, forum_order=forum_order),
            max_attempts=MAX_FRONTIER_ATTEMPTS,
        )

    @staticmethod
    def frontier_record_from_entry(
        entry: PostListEntry,
        *,
        forum_order: int | None = None,
    ) -> FrontierRecord:
        is_root = entry.parent_id is None and entry.depth == 0
        root_post_id = entry.post_id if is_root else entry.root_post_id
        parent_reply_id = None
        if not is_root and entry.parent_id and entry.parent_id != root_post_id:
            parent_reply_id = entry.parent_id

        return FrontierRecord(
            post_id=entry.post_id,
            url=entry.url,
            record_type="post" if is_root else "reply",
            root_post_id=root_post_id,
            parent_reply_id=parent_reply_id,
            depth=entry.depth,
            forum_order=forum_order,
            listing_title=entry.title,
            listing_reply_count=parse_reply_count(entry.title) if is_root else None,
        )

    def next_frontier_requests(self):
        while self.can_schedule_detail_request():
            row = claim_next_frontier(
                self.frontier_conn(),
                max_attempts=MAX_FRONTIER_ATTEMPTS,
            )
            if row is None:
                return
            self.scheduled_detail_requests += 1
            yield self.frontier_request(row)

    def can_schedule_detail_request(self) -> bool:
        return self.max_requests is None or self.scheduled_detail_requests < self.max_requests

    def frontier_request(self, row: dict[str, Any]) -> scrapy.Request:
        record_type = str(row["record_type"])
        post_id = str(row["post_id"])
        root_post_id = str(row["root_post_id"] or post_id)
        callback = self.parse_root_post if record_type == "post" else self.parse_reply
        meta: dict[str, object] = {
            "frontier_post_id": post_id,
            "post_id": post_id,
            "listing_title": row.get("listing_title"),
            "listing_text": row.get("listing_title"),
        }
        if record_type == "reply":
            meta.update(
                {
                    "reply_id": post_id,
                    "root_post_id": root_post_id,
                    "parent_id": row.get("parent_reply_id") or root_post_id,
                    "reply_depth": int(row.get("depth") or 1),
                    "forum_order": row.get("forum_order"),
                }
            )

        return scrapy.Request(
            str(row["url"]),
            callback=callback,
            errback=self.frontier_errback,
            meta=meta,
            dont_filter=False,
        )

    def frontier_errback(self, failure: Any) -> None:
        request = getattr(failure, "request", None)
        if request is None:
            return
        post_id = request.meta.get("frontier_post_id") or request.meta.get("post_id")
        if post_id is None:
            return
        response = getattr(getattr(failure, "value", None), "response", None)
        mark_frontier_failed(
            self.frontier_conn(),
            str(post_id),
            http_status=getattr(response, "status", None),
            error=failure.getErrorMessage(),
        )

    def mark_response_failed(self, response: scrapy.http.Response, exc: Exception) -> None:
        post_id = response.meta.get("frontier_post_id") or post_id_from_url(response.url)
        if post_id is None:
            return
        mark_frontier_failed(
            self.frontier_conn(),
            str(post_id),
            http_status=response.status,
            error=str(exc),
        )

    @staticmethod
    def optional_positive_int(value: str | int | None) -> int | None:
        if value in (None, "", "0"):
            return None
        return max(1, int(value))

    def parse(self, response: scrapy.http.Response):
        if post_id_from_url(response.url):
            yield from self.parse_root_post(response)
        else:
            yield from self.parse_index(response, page_number=1)
