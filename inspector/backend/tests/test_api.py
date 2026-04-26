from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from app.main import app


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "crawler.sqlite3"
    import sqlite3

    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE posts (
            post_id TEXT PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            forum TEXT NOT NULL,
            title TEXT,
            author TEXT,
            author_profile_url TEXT,
            published_at TEXT,
            edited_at TEXT,
            body_text TEXT,
            body_html TEXT,
            byte_count INTEGER,
            read_count INTEGER,
            reply_count INTEGER,
            crawled_at TEXT NOT NULL
        );

        CREATE TABLE replies (
            reply_id TEXT PRIMARY KEY,
            root_post_id TEXT NOT NULL,
            parent_reply_id TEXT,
            url TEXT NOT NULL UNIQUE,
            forum TEXT NOT NULL,
            title TEXT,
            author TEXT,
            author_profile_url TEXT,
            published_at TEXT,
            edited_at TEXT,
            body_text TEXT,
            body_html TEXT,
            byte_count INTEGER,
            read_count INTEGER,
            depth INTEGER NOT NULL DEFAULT 1,
            forum_order INTEGER,
            crawled_at TEXT NOT NULL
        );
        """
    )
    conn.executemany(
        """
        INSERT INTO posts (
            post_id, url, forum, title, author, author_profile_url, published_at, edited_at,
            body_text, body_html, byte_count, read_count, reply_count, crawled_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "100",
                "https://bbs.wenxuecity.com/cfzh/100.html",
                "cfzh",
                "Alpha setup",
                "Alice",
                None,
                "2026-04-25T09:00:00",
                None,
                "Apple and market structure notes.",
                (
                    "<div id=\"msgbodyContent\"><p>Apple<br>and market structure notes.</p>"
                    "<p><img src=\"/upload/alpha.jpeg\" alt=\"Alpha chart\"></p></div>"
                ),
                34,
                10,
                2,
                "2026-04-25T10:01:00",
            ),
            (
                "200",
                "https://bbs.wenxuecity.com/cfzh/200.html",
                "cfzh",
                "Beta rotation",
                "Bob",
                None,
                "2026-04-25T09:30:00",
                None,
                None,
                "<div id=\"msgbodyContent\"><p><img src=\"/upload/beta.jpeg\"></p></div>",
                23,
                20,
                1,
                "2026-04-25T10:02:00",
            ),
        ],
    )
    conn.executemany(
        """
        INSERT INTO replies (
            reply_id, root_post_id, parent_reply_id, url, forum, title, author,
            author_profile_url, published_at, edited_at, body_text, body_html,
            byte_count, read_count, depth, forum_order, crawled_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "101",
                "100",
                None,
                "https://bbs.wenxuecity.com/cfzh/101.html",
                "cfzh",
                "First reply",
                "Carol",
                None,
                "2026-04-25T09:05:00",
                None,
                "Root reply",
                "<p>Root reply<img src=\"/upload/reply.jpeg\" alt=\"reply chart\"></p>",
                10,
                None,
                1,
                1,
                "2026-04-25T10:01:30",
            ),
            (
                "102",
                "100",
                "101",
                "https://bbs.wenxuecity.com/cfzh/102.html",
                "cfzh",
                "Nested reply",
                "Alice",
                None,
                "2026-04-25T09:06:00",
                None,
                "Nested reply body",
                "<p>Nested reply body</p>",
                17,
                None,
                2,
                2,
                "2026-04-25T10:01:40",
            ),
            (
                "201",
                "200",
                None,
                "https://bbs.wenxuecity.com/cfzh/201.html",
                "cfzh",
                "Beta reply",
                "Carol",
                None,
                "2026-04-25T09:35:00",
                None,
                "Another root reply",
                "<p>Another root reply</p>",
                18,
                None,
                1,
                1,
                "2026-04-25T10:02:30",
            ),
        ],
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
async def client(
    monkeypatch: pytest.MonkeyPatch,
    db_path: Path,
) -> AsyncIterator[httpx.AsyncClient]:
    monkeypatch.setenv("WXC_INSPECT_DB", str(db_path))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client


@pytest.mark.anyio
async def test_summary_counts(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["posts"] == 2
    assert payload["replies"] == 3
    assert payload["authors"] == 3
    assert payload["latest_crawl_at"] == "2026-04-25T10:02:30"


@pytest.mark.anyio
async def test_post_list_supports_search_and_author_filter(client: httpx.AsyncClient) -> None:
    search_response = await client.get("/api/posts", params={"search": "apple"})
    author_response = await client.get("/api/posts", params={"author": "Bob"})

    assert search_response.status_code == 200
    assert [item["post_id"] for item in search_response.json()["items"]] == ["100"]
    assert search_response.json()["items"][0]["actual_reply_count"] == 2

    assert author_response.status_code == 200
    assert [item["post_id"] for item in author_response.json()["items"]] == ["200"]


@pytest.mark.anyio
async def test_authors_include_post_and_reply_counts(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/authors")

    assert response.status_code == 200
    authors = {item["name"]: item for item in response.json()}
    assert authors["Alice"] == {"name": "Alice", "posts": 1, "replies": 1, "total": 2}
    assert authors["Carol"] == {"name": "Carol", "posts": 0, "replies": 2, "total": 2}


@pytest.mark.anyio
async def test_post_detail_returns_recursive_replies(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/posts/100")

    assert response.status_code == 200
    payload = response.json()
    assert payload["post_id"] == "100"
    assert "<br>" in payload["body_html"]
    assert "/upload/alpha.jpeg" in payload["body_html"]
    assert payload["replies"][0]["reply_id"] == "101"
    assert "/upload/reply.jpeg" in payload["replies"][0]["body_html"]
    assert payload["replies"][0]["replies"][0]["reply_id"] == "102"


@pytest.mark.anyio
async def test_post_detail_returns_image_only_html(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/posts/200")

    assert response.status_code == 200
    payload = response.json()
    assert payload["post_id"] == "200"
    assert payload["body_text"] is None
    assert "/upload/beta.jpeg" in payload["body_html"]


@pytest.mark.anyio
async def test_post_detail_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/posts/999")

    assert response.status_code == 404
