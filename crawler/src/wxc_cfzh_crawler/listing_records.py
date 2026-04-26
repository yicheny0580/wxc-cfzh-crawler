from __future__ import annotations

from wxc_cfzh_crawler.models import ForumPost, ForumReply, FrontierRecord
from wxc_cfzh_crawler.parsing import PostListEntry


def is_root_entry(entry: PostListEntry) -> bool:
    return entry.parent_id is None and entry.depth == 0


def should_skip_detail(entry: PostListEntry) -> bool:
    return entry.byte_count == 0 and not entry.has_children


def frontier_record_from_entry(
    entry: PostListEntry,
    *,
    forum_order: int | None = None,
) -> FrontierRecord:
    is_root = is_root_entry(entry)
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
        listing_reply_count=entry.reply_count if is_root else None,
    )


def frontier_records_from_entries(entries: list[PostListEntry]) -> list[FrontierRecord]:
    return [
        frontier_record_from_entry(entry, forum_order=forum_order)
        for forum_order, entry in enumerate(entries, start=1)
    ]


def record_from_listing_entry(
    entry: PostListEntry,
    *,
    forum_order: int | None = None,
) -> ForumPost | ForumReply:
    if is_root_entry(entry):
        return ForumPost(
            post_id=entry.post_id,
            url=entry.url,
            title=entry.title,
            author=entry.author,
            author_profile_url=entry.author_profile_url,
            published_at=entry.published_at,
            byte_count=entry.byte_count,
            read_count=entry.read_count,
            reply_count=entry.reply_count,
        )

    root_post_id = str(entry.root_post_id or entry.post_id)
    parent_reply_id = entry.parent_id if entry.parent_id != root_post_id else None
    return ForumReply(
        reply_id=entry.post_id,
        root_post_id=root_post_id,
        parent_reply_id=parent_reply_id,
        url=entry.url,
        title=entry.title,
        author=entry.author,
        author_profile_url=entry.author_profile_url,
        published_at=entry.published_at,
        byte_count=entry.byte_count,
        read_count=entry.read_count,
        depth=entry.depth,
        forum_order=forum_order,
    )
