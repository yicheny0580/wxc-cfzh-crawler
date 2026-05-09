from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

POST_ID_RE = re.compile(r"/cfzh/(\d+)(?:-print)?\.html(?:[?#].*)?$")
DATE_PATTERNS = ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S")
LISTING_AUTHOR_SELECTOR = (
    "a.nickname, "
    "a.username, "
    "a[href*='passport.wenxuecity.com/members/index.php'][href*='act=profile'], "
    "a[href*='passport.wenxuecity.com/profile.php']"
)
DETAIL_REQUIRED_ANY_FIELDS = (
    "title",
    "author",
    "published_at",
    "body_text",
    "body_html",
    "byte_count",
    "read_count",
)


@dataclass(frozen=True)
class PostListEntry:
    post_id: str
    url: str
    title: str | None
    parent_id: str | None
    root_post_id: str | None
    depth: int
    byte_count: int | None = None
    read_count: int | None = None
    reply_count: int | None = None
    has_children: bool = False
    author: str | None = None
    author_profile_url: str | None = None
    published_at: datetime | None = None


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip() or None


def post_id_from_url(url: str | None) -> str | None:
    if not url:
        return None
    match = POST_ID_RE.search(url)
    return match.group(1) if match else None


def parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"[\d,]+", value)
    if not match:
        return None
    return int(match.group(0).replace(",", ""))


def has_parseable_detail(record: dict[str, Any]) -> bool:
    return any(record.get(field) is not None for field in DETAIL_REQUIRED_ANY_FIELDS)


def parse_datetime(value: str | None) -> datetime | None:
    value = normalize_text(value)
    if not value:
        return None
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(value, pattern)
        except ValueError:
            pass
    return None


def parse_listing_datetime(text: str | None) -> datetime | None:
    text = normalize_text(text)
    if not text:
        return None

    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\b", text)
    if match:
        return parse_datetime(f"{match.group(1)} {match.group(2)}")

    match = re.search(
        r"\b(\d{1,2}/\d{1,2}/\d{4})(?:\s+postreply)?\s+(\d{1,2}:\d{2}:\d{2})\b",
        text,
    )
    if match:
        return parse_datetime(f"{match.group(1)} {match.group(2)}")
    return None


def parse_margin_left(style: str | None) -> int:
    if not style:
        return 0
    match = re.search(r"margin\s*:\s*([^;]+)", style)
    if not match:
        return 0
    parts = match.group(1).split()
    if len(parts) == 1:
        left = parts[0]
    elif len(parts) == 2:
        left = parts[1]
    elif len(parts) == 3:
        left = parts[1]
    else:
        left = parts[3]
    parsed = re.search(r"(-?\d+)px", left)
    return max(int(parsed.group(1)), 0) if parsed else 0


def depth_from_style(style: str | None) -> int:
    return parse_margin_left(style) // 20


def nearest_parent(stack: dict[int, str], depth: int) -> str | None:
    for candidate_depth in range(depth - 1, -1, -1):
        if candidate_depth in stack:
            return stack[candidate_depth]
    return None


def extract_index_entries(response: Any, *, include_sticky: bool = False) -> list[PostListEntry]:
    entries: list[PostListEntry] = []
    stack: dict[int, str] = {}
    seen: set[str] = set()

    for anchor in response.css("#postlist p a.post"):
        href = anchor.attrib.get("href")
        url = response.urljoin(href)
        post_id = post_id_from_url(url)
        is_sticky = "sticky" in (anchor.attrib.get("class") or "").split()
        if is_sticky and not include_sticky:
            continue
        if post_id is None or post_id in seen:
            continue
        seen.add(post_id)

        row = anchor.xpath("ancestor::p[1]")
        row_text = normalize_text(row.xpath("string(.)").get())

        style = row.attrib.get("style")
        depth = depth_from_style(style)
        parent_id = nearest_parent(stack, depth) if depth > 0 else None
        root_post_id = stack.get(0) if parent_id else post_id

        entries.append(
            PostListEntry(
                post_id=post_id,
                url=url,
                title=normalize_text(anchor.xpath("string(.)").get()),
                parent_id=parent_id,
                root_post_id=root_post_id,
                depth=depth,
                **listing_metadata(response, row_text, row),
            )
        )
        stack[depth] = post_id
        for stale_depth in [key for key in stack if key > depth]:
            del stack[stale_depth]

    return entries_with_child_flags(entries)


def extract_root_index_entries(response: Any) -> list[PostListEntry]:
    return [
        entry
        for entry in extract_index_entries(response)
        if entry.parent_id is None and entry.depth == 0
    ]


def extract_comment_entries(
    response: Any,
    *,
    root_post_id: str,
    base_parent_id: str,
    base_depth: int,
) -> list[PostListEntry]:
    entries: list[PostListEntry] = []
    stack: dict[int, str] = {base_depth: base_parent_id}
    seen: set[str] = set()

    for anchor in response.css("#comment #postlist a.post"):
        href = anchor.attrib.get("href")
        url = response.urljoin(href)
        post_id = post_id_from_url(url)
        if post_id is None or post_id in seen:
            continue
        seen.add(post_id)

        row = anchor.xpath("ancestor::p[1]")
        row_text = normalize_text(row.xpath("string(.)").get())
        style = row.attrib.get("style")
        depth = base_depth + depth_from_style(style) + 1
        parent_id = nearest_parent(stack, depth)

        entries.append(
            PostListEntry(
                post_id=post_id,
                url=url,
                title=normalize_text(anchor.xpath("string(.)").get()),
                parent_id=parent_id,
                root_post_id=root_post_id,
                depth=depth,
                **listing_metadata(response, row_text, row),
            )
        )
        stack[depth] = post_id
        for stale_depth in [key for key in stack if key > depth]:
            del stack[stale_depth]

    return entries_with_child_flags(entries)


def listing_metadata(
    response: Any,
    row_text: str | None,
    row: Any,
) -> dict[str, Any]:
    author_anchor = row.css(LISTING_AUTHOR_SELECTOR)
    author_profile_url = author_anchor.attrib.get("href") if author_anchor else None
    if author_profile_url:
        author_profile_url = response.urljoin(author_profile_url)

    return {
        "byte_count": parse_int(_first_match(r"\(([\d,]+)\s*bytes\)", row_text)),
        "read_count": parse_int(_first_match(r"\(([\d,]+)\s*reads\)", row_text)),
        "reply_count": parse_reply_count(row_text),
        "author": normalize_text(author_anchor.xpath("string(.)").get()),
        "author_profile_url": author_profile_url,
        "published_at": parse_listing_datetime(row_text),
    }


def entries_with_child_flags(entries: list[PostListEntry]) -> list[PostListEntry]:
    flagged: list[PostListEntry] = []
    for index, entry in enumerate(entries):
        next_entry = entries[index + 1] if index + 1 < len(entries) else None
        has_nested_row = next_entry is not None and next_entry.depth > entry.depth
        has_children = bool(entry.reply_count and entry.reply_count > 0) or has_nested_row
        flagged.append(replace(entry, has_children=has_children))
    return flagged


def extract_post_record(response: Any, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = meta or {}
    post_id = post_id_from_url(response.url)
    if post_id is None:
        raise ValueError(f"Could not extract post id from URL: {response.url}")

    title = normalize_text(response.css("h1.title::text, h1::text").get())
    author = normalize_text(response.css("#postmeta a.username span::text").get())
    author_profile_url = response.css("#postmeta a.username::attr(href)").get()
    if author_profile_url:
        author_profile_url = response.urljoin(author_profile_url)

    published_at = parse_datetime(response.css("#postmeta span.date::text").get())
    meta_text = normalize_text(response.css("#postmeta").xpath("string(.)").get()) or ""
    byte_count = parse_int(_first_match(r"\(([\d,]+)\s*bytes\)", meta_text))
    read_count = parse_int(response.css("#countnum::text").get()) or parse_int(
        _first_match(r"阅读数\s*:\s*([\d,]+)", meta_text)
    )

    edit_text = normalize_text(response.css("#editmessage").xpath("string(.)").get())
    edited_at = parse_datetime(_first_match(r"本帖于\s+([\d:-]+\s+[\d:]+)\s+时间", edit_text))

    body_selector = response.css("#msgbodyContent")
    if not body_selector:
        body_selector = response.css("#articleBody")
    body_html = body_selector.get()
    body_text = normalize_text(body_selector.xpath("string(.)").get())

    record = {
        "item_type": "post",
        "post_id": post_id,
        "url": response.url,
        "forum": "cfzh",
        "title": title,
        "author": author,
        "author_profile_url": author_profile_url,
        "published_at": published_at,
        "edited_at": edited_at,
        "body_text": body_text,
        "body_html": body_html,
        "byte_count": byte_count,
        "read_count": read_count,
        "reply_count": parse_reply_count(meta.get("listing_text")),
    }
    if not has_parseable_detail(record):
        raise ValueError(f"No parseable post detail fields in response: {response.url}")
    return record


def extract_reply_record(response: Any, *, meta: dict[str, Any]) -> dict[str, Any]:
    root_post_id = str(meta["root_post_id"])
    post_record = extract_post_record(response, meta=meta)
    reply_id = str(post_record.pop("post_id"))

    parent_url = response.css("#postparent a[href*='/cfzh/']::attr(href)").get()
    parent_id = post_id_from_url(urljoin(response.url, parent_url)) if parent_url else None
    parent_id = str(meta.get("parent_id") or parent_id or "")
    parent_reply_id = parent_id if parent_id and parent_id != root_post_id else None

    return {
        **post_record,
        "item_type": "reply",
        "reply_id": reply_id,
        "root_post_id": root_post_id,
        "parent_reply_id": parent_reply_id,
        "depth": int(meta.get("reply_depth", 1) or 1),
        "forum_order": meta.get("forum_order"),
    }


def parse_reply_count(text: str | None) -> int | None:
    text = normalize_text(text)
    if not text:
        return None
    match = re.search(r"\((\d+)\)\s*$", text)
    return int(match.group(1)) if match else None


def _first_match(pattern: str, text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(pattern, text)
    return match.group(1) if match else None
