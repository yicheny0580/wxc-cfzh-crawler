from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class FrontierRecord(BaseModel):
    post_id: str
    url: str
    record_type: Literal["post", "reply"]
    root_post_id: str | None = None
    parent_reply_id: str | None = None
    depth: int = 0
    forum_order: int | None = None
    listing_title: str | None = None
    listing_reply_count: int | None = None
    status: Literal["pending", "in_progress", "done", "failed"] = "pending"
    attempts: int = 0
    discovered_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_fetched_at: datetime | None = None
    last_http_status: int | None = None
    last_error: str | None = None


class ForumPost(BaseModel):
    post_id: str
    url: str
    forum: str = "cfzh"
    title: str | None = None
    author: str | None = None
    author_profile_url: str | None = None
    published_at: datetime | None = None
    edited_at: datetime | None = None
    body_text: str | None = None
    body_html: str | None = None
    byte_count: int | None = None
    read_count: int | None = None
    reply_count: int | None = None
    crawled_at: datetime = Field(default_factory=utc_now)


class ForumReply(BaseModel):
    reply_id: str
    root_post_id: str
    parent_reply_id: str | None = None
    url: str
    forum: str = "cfzh"
    title: str | None = None
    author: str | None = None
    author_profile_url: str | None = None
    published_at: datetime | None = None
    edited_at: datetime | None = None
    body_text: str | None = None
    body_html: str | None = None
    byte_count: int | None = None
    read_count: int | None = None
    depth: int = 1
    forum_order: int | None = None
    crawled_at: datetime = Field(default_factory=utc_now)
