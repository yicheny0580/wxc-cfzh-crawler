from __future__ import annotations

POST_SELECT_COLUMNS = """
    post_id, url, forum, title, author, author_profile_url, published_at, edited_at,
    body_text, body_html, byte_count, read_count, reply_count, crawled_at
"""

REPLY_SELECT_COLUMNS = """
    reply_id, root_post_id, parent_reply_id, url, forum, title, author, author_profile_url,
    published_at, edited_at, body_text, body_html, byte_count, read_count, depth,
    forum_order, crawled_at
"""

FRONTIER_SELECT_COLUMNS = """
    post_id, url, record_type, root_post_id, parent_reply_id, depth, forum_order, listing_title,
    listing_reply_count, status, attempts, discovered_at, updated_at, last_fetched_at,
    last_http_status, last_error, suppressed_at
"""
