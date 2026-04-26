from __future__ import annotations

import os
import sqlite3
from typing import Any
from urllib.parse import urlencode

import scrapy

from wxc_cfzh_crawler.db import (
    claim_next_frontier,
    connect,
    fetch_crawl_progress,
    format_crawl_progress,
    mark_frontier_failed,
    reset_in_progress_frontier,
    save_post_detail,
    save_reply_detail,
    upsert_frontier_entry,
)
from wxc_cfzh_crawler.models import ForumPost, ForumReply, FrontierRecord
from wxc_cfzh_crawler.parsing import (
    PostListEntry,
    extract_comment_entries,
    extract_index_entries,
    extract_post_record,
    extract_reply_record,
    parse_reply_count,
    post_id_from_url,
)
from wxc_cfzh_crawler.paths import default_database_url
from wxc_cfzh_crawler.progress import get_crawl_progress_reporter

DEFAULT_DATABASE_URL = default_database_url()
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
            elapsed_text = self.elapsed_time_text()
            progress = fetch_crawl_progress(self.conn)
            get_crawl_progress_reporter().close()
            self.logger.info(
                "CFZH crawl finished reason=%s elapsed=%s scheduled=%s; %s",
                reason,
                elapsed_text,
                self.scheduled_detail_requests,
                format_crawl_progress(progress),
            )
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

        entries = list(extract_index_entries(response))
        for entry in entries:
            self.enqueue_frontier_entry(entry)

        self.update_progress()

        yield from self.next_frontier_requests()

    def parse_root_post(self, response: scrapy.http.Response):
        try:
            post_item = extract_post_record(response, meta=response.meta)
        except Exception as exc:  # noqa: BLE001
            self.mark_response_failed(response, exc)
            yield from self.next_frontier_requests()
            return

        root_post_id = str(post_item["post_id"])
        child_frontier = self.comment_frontier_records(
            response,
            root_post_id=root_post_id,
            base_parent_id=root_post_id,
            base_depth=0,
        )
        try:
            save_post_detail(
                self.frontier_conn(),
                ForumPost.model_validate(self.public_item_data(post_item)),
                child_frontier,
                frontier_post_id=str(response.meta.get("frontier_post_id") or root_post_id),
                http_status=response.status,
                max_attempts=MAX_FRONTIER_ATTEMPTS,
            )
        except Exception as exc:  # noqa: BLE001
            self.mark_response_failed(response, exc)
            yield from self.next_frontier_requests()
            return

        self.update_comment_progress(len(child_frontier))
        yield from self.next_frontier_requests()

    def parse_reply(self, response: scrapy.http.Response):
        try:
            reply_item = extract_reply_record(response, meta=response.meta)
        except Exception as exc:  # noqa: BLE001
            self.mark_response_failed(response, exc)
            yield from self.next_frontier_requests()
            return

        child_frontier = self.comment_frontier_records(
            response,
            root_post_id=str(reply_item["root_post_id"]),
            base_parent_id=str(reply_item["reply_id"]),
            base_depth=int(reply_item.get("depth") or 1),
        )
        try:
            save_reply_detail(
                self.frontier_conn(),
                ForumReply.model_validate(self.public_item_data(reply_item)),
                child_frontier,
                frontier_post_id=str(
                    response.meta.get("frontier_post_id") or reply_item["reply_id"]
                ),
                http_status=response.status,
                max_attempts=MAX_FRONTIER_ATTEMPTS,
            )
        except Exception as exc:  # noqa: BLE001
            self.mark_response_failed(response, exc)
            yield from self.next_frontier_requests()
            return

        self.update_comment_progress(len(child_frontier))
        yield from self.next_frontier_requests()

    def parse_post(self, response: scrapy.http.Response):
        yield from self.parse_root_post(response)

    def comment_frontier_records(
        self,
        response: scrapy.http.Response,
        *,
        root_post_id: str,
        base_parent_id: str,
        base_depth: int,
    ) -> list[FrontierRecord]:
        entries = extract_comment_entries(
            response,
            root_post_id=root_post_id,
            base_parent_id=base_parent_id,
            base_depth=base_depth,
        )
        return [
            self.frontier_record_from_entry(entry, forum_order=forum_order)
            for forum_order, entry in enumerate(entries, start=1)
        ]

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
            self.update_progress()
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
        error = failure.getErrorMessage()
        mark_frontier_failed(
            self.frontier_conn(),
            str(post_id),
            http_status=getattr(response, "status", None),
            error=error,
        )
        self.log_frontier_failure(
            request.meta,
            str(post_id),
            http_status=getattr(response, "status", None),
            error=error,
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
        self.log_frontier_failure(
            response.meta,
            str(post_id),
            http_status=response.status,
            error=str(exc),
        )

    def update_comment_progress(self, reply_count: int) -> None:
        if reply_count == 0:
            return
        self.update_progress()

    def log_frontier_failure(
        self,
        meta: dict[str, Any],
        post_id: str,
        *,
        http_status: int | None,
        error: str,
    ) -> None:
        get_crawl_progress_reporter().clear()
        self.logger.warning(
            "CFZH failed %s id=%s status=%s error=%s; %s",
            self.record_type_from_meta(meta),
            post_id,
            http_status if http_status is not None else "unknown",
            error,
            format_crawl_progress(fetch_crawl_progress(self.frontier_conn())),
        )
        self.update_progress()

    def update_progress(self) -> None:
        mode = self.progress_mode()
        reporter = get_crawl_progress_reporter(mode=mode)
        reporter.update_progress(
            fetch_crawl_progress(self.frontier_conn()),
            scheduled=self.scheduled_detail_requests,
            max_requests=self.max_requests,
        )

    def progress_mode(self) -> str | None:
        settings = getattr(getattr(self, "crawler", None), "settings", None)
        if settings is None:
            return os.getenv("WXC_PROGRESS")
        return settings.get("WXC_PROGRESS", os.getenv("WXC_PROGRESS"))

    def elapsed_time_text(self) -> str:
        stats = getattr(getattr(self, "crawler", None), "stats", None)
        elapsed = stats.get_value("elapsed_time_seconds") if stats is not None else None
        if isinstance(elapsed, (int, float)):
            return f"{elapsed:.1f}s"
        return "unknown"

    @staticmethod
    def record_type_from_meta(meta: dict[str, Any]) -> str:
        return "reply" if meta.get("reply_id") else "post"

    @staticmethod
    def optional_positive_int(value: str | int | None) -> int | None:
        if value in (None, "", "0"):
            return None
        return max(1, int(value))

    @staticmethod
    def public_item_data(item: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in item.items()
            if key != "item_type" and not key.startswith("_")
        }

    def parse(self, response: scrapy.http.Response):
        if post_id_from_url(response.url):
            yield from self.parse_root_post(response)
        else:
            yield from self.parse_index(response, page_number=1)
