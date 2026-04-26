from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool
    db_path: str
    db_exists: bool
    read_only: bool = True
    detail: str | None = None


class SummaryResponse(BaseModel):
    db_path: str
    posts: int
    replies: int
    authors: int
    latest_crawl_at: str | None = None
    latest_post_published_at: str | None = None


class AuthorSummary(BaseModel):
    name: str
    posts: int
    replies: int
    total: int


class PostBase(BaseModel):
    post_id: str
    url: str
    forum: str
    title: str | None = None
    author: str | None = None
    author_profile_url: str | None = None
    published_at: str | None = None
    edited_at: str | None = None
    byte_count: int | None = None
    read_count: int | None = None
    reply_count: int | None = None
    actual_reply_count: int
    crawled_at: str


class PostListItem(PostBase):
    excerpt: str | None = None


class PostListResponse(BaseModel):
    items: list[PostListItem]
    total: int
    limit: int
    offset: int


class ResultItem(BaseModel):
    record_type: Literal["post", "reply"]
    post_id: str
    reply_id: str | None = None
    root_post_id: str
    url: str
    forum: str
    title: str | None = None
    author: str | None = None
    author_profile_url: str | None = None
    published_at: str | None = None
    edited_at: str | None = None
    byte_count: int | None = None
    read_count: int | None = None
    reply_count: int | None = None
    actual_reply_count: int | None = None
    root_title: str | None = None
    root_author: str | None = None
    root_url: str | None = None
    crawled_at: str
    excerpt: str | None = None


class ResultListResponse(BaseModel):
    items: list[ResultItem]
    total: int
    limit: int
    offset: int


class ReplyDetail(BaseModel):
    reply_id: str
    root_post_id: str
    parent_reply_id: str | None = None
    url: str
    forum: str
    title: str | None = None
    author: str | None = None
    author_profile_url: str | None = None
    published_at: str | None = None
    edited_at: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    byte_count: int | None = None
    read_count: int | None = None
    depth: int
    forum_order: int | None = None
    crawled_at: str
    replies: list[ReplyDetail] = Field(default_factory=list)


class PostDetail(PostBase):
    body_text: str | None = None
    body_html: str | None = None
    replies: list[ReplyDetail] = Field(default_factory=list)
