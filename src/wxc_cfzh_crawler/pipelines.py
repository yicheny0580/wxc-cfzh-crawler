from __future__ import annotations

from typing import Any

from wxc_cfzh_crawler.db import connect, mark_frontier_done, upsert_post, upsert_reply
from wxc_cfzh_crawler.models import ForumPost, ForumReply


class SQLitePipeline:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.conn = None

    @classmethod
    def from_crawler(cls, crawler: Any) -> SQLitePipeline:
        return cls(
            database_url=crawler.settings.get("DATABASE_URL"),
        )

    def open_spider(self) -> None:
        self.conn = connect(self.database_url)

    def close_spider(self) -> None:
        if self.conn is not None:
            self.conn.close()

    def process_item(self, item: dict[str, Any]) -> dict[str, Any]:
        if self.conn is None:
            raise RuntimeError("SQLite connection is not open")

        item_type = item.get("item_type")
        if item_type == "post":
            post_data = self.public_item_data(item)
            post = ForumPost.model_validate(post_data)
            upsert_post(self.conn, post)
            mark_frontier_done(
                self.conn,
                str(item.get("_frontier_post_id") or post.post_id),
                http_status=item.get("_http_status"),
            )
        elif item_type == "reply":
            reply_data = self.public_item_data(item)
            reply = ForumReply.model_validate(reply_data)
            upsert_reply(self.conn, reply)
            mark_frontier_done(
                self.conn,
                str(item.get("_frontier_post_id") or reply.reply_id),
                http_status=item.get("_http_status"),
            )
        return item

    @staticmethod
    def public_item_data(item: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in item.items()
            if key != "item_type" and not key.startswith("_")
        }
