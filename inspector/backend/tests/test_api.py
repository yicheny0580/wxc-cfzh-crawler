from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.crawl import CrawlManager
from app.main import app


def result_ids(items: list[dict[str, object]]) -> list[tuple[object, object]]:
    return [(item["record_type"], item["reply_id"] or item["post_id"]) for item in items]


def reply_result_ids(items: list[dict[str, object]]) -> list[tuple[object, object]]:
    return [(item["record_type"], item["reply_id"]) for item in items]


class FakeProcess:
    stdout = None
    stderr = None

    def __init__(self) -> None:
        self.returncode: int | None = None
        self.terminated = False
        self.killed = False
        self._done = asyncio.Event()

    async def wait(self) -> int:
        await self._done.wait()
        return self.returncode if self.returncode is not None else 0

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True
        self.finish(-9)

    def finish(self, returncode: int) -> None:
        self.returncode = returncode
        self._done.set()


class FakeSubprocessFactory:
    def __init__(self) -> None:
        self.commands: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.processes: list[FakeProcess] = []

    async def __call__(self, *command: object, **kwargs: object) -> FakeProcess:
        process = FakeProcess()
        self.commands.append((command, kwargs))
        self.processes.append(process)
        return process


async def wait_for_crawl_state(manager: CrawlManager, state: str) -> None:
    for _ in range(50):
        if manager.status().state == state:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"Crawl state did not become {state}.")


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


@pytest.fixture()
async def crawl_client(
    monkeypatch: pytest.MonkeyPatch,
    db_path: Path,
) -> AsyncIterator[tuple[httpx.AsyncClient, CrawlManager, FakeSubprocessFactory]]:
    monkeypatch.setenv("WXC_INSPECT_DB", str(db_path))
    factory = FakeSubprocessFactory()
    manager = CrawlManager(subprocess_factory=factory, stop_grace_seconds=30.0)
    monkeypatch.setattr("app.main.crawl_manager", manager)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client, manager, factory

    for process in factory.processes:
        if process.returncode is None:
            process.finish(0)
    await asyncio.sleep(0.02)


@pytest.mark.anyio
async def test_crawl_start_defaults_to_five_pages_and_current_db(
    crawl_client: tuple[httpx.AsyncClient, CrawlManager, FakeSubprocessFactory],
    db_path: Path,
) -> None:
    client, manager, factory = crawl_client

    response = await client.post("/api/crawl", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "running"
    assert payload["pages"] == 5
    assert payload["db_path"] == str(db_path)
    assert payload["progress"] is None

    command, kwargs = factory.commands[0]
    assert command[:7] == (
        "uv",
        "run",
        "--package",
        "wxc-cfzh-crawler",
        "scrapy",
        "crawl",
        "cfzh",
    )
    assert "pages=5" in command
    assert f"database_url=sqlite:///{db_path.as_posix()}" in command
    assert kwargs["cwd"]
    assert kwargs["env"]["WXC_PROGRESS"] == "off"

    factory.processes[0].finish(0)
    await wait_for_crawl_state(manager, "succeeded")


@pytest.mark.anyio
async def test_crawl_rejects_duplicate_start(
    crawl_client: tuple[httpx.AsyncClient, CrawlManager, FakeSubprocessFactory],
) -> None:
    client, manager, factory = crawl_client

    first_response = await client.post("/api/crawl", json={"pages": 12})
    second_response = await client.post("/api/crawl", json={"pages": 1})

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json()["detail"]["state"] == "running"
    assert len(factory.processes) == 1

    factory.processes[0].finish(0)
    await wait_for_crawl_state(manager, "succeeded")


@pytest.mark.anyio
async def test_crawl_pages_are_limited_to_600(
    crawl_client: tuple[httpx.AsyncClient, CrawlManager, FakeSubprocessFactory],
) -> None:
    client, _, factory = crawl_client

    response = await client.post("/api/crawl", json={"pages": 601})

    assert response.status_code == 422
    assert factory.processes == []


@pytest.mark.anyio
async def test_crawl_stop_reports_stopping_until_process_exits(
    crawl_client: tuple[httpx.AsyncClient, CrawlManager, FakeSubprocessFactory],
) -> None:
    client, manager, factory = crawl_client

    await client.post("/api/crawl", json={"pages": 10})
    stop_response = await client.post("/api/crawl/stop")

    assert stop_response.status_code == 200
    assert stop_response.json()["state"] == "stopping"
    assert factory.processes[0].terminated is True

    status_response = await client.get("/api/crawl/status")
    assert status_response.json()["state"] == "stopping"

    factory.processes[0].finish(-15)
    await wait_for_crawl_state(manager, "stopped")
    final_response = await client.get("/api/crawl/status")

    assert final_response.json()["state"] == "stopped"
    assert final_response.json()["return_code"] == -15


def test_crawl_websocket_sends_initial_status(
    monkeypatch: pytest.MonkeyPatch,
    db_path: Path,
) -> None:
    monkeypatch.setenv("WXC_INSPECT_DB", str(db_path))
    manager = CrawlManager(subprocess_factory=FakeSubprocessFactory())
    monkeypatch.setattr("app.main.crawl_manager", manager)

    with TestClient(app) as client:
        with client.websocket_connect("/api/crawl/ws") as websocket:
            payload = websocket.receive_json()

    assert payload["state"] == "idle"
    assert payload["db_path"] == str(db_path)


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
async def test_results_include_posts_and_replies_with_root_metadata(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/api/results")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 5
    assert result_ids(payload["items"]) == [
        ("reply", "201"),
        ("post", "200"),
        ("reply", "102"),
        ("reply", "101"),
        ("post", "100"),
    ]

    reply = payload["items"][0]
    assert reply["root_post_id"] == "200"
    assert reply["post_id"] == "200"
    assert reply["root_title"] == "Beta rotation"
    assert reply["root_author"] == "Bob"
    assert reply["root_url"] == "https://bbs.wenxuecity.com/cfzh/200.html"
    assert reply["excerpt"] == "Another root reply"


@pytest.mark.anyio
async def test_results_support_author_filter_per_selected_record_type(
    client: httpx.AsyncClient,
) -> None:
    combined = await client.get("/api/results", params={"author": "Alice"})
    posts_only = await client.get(
        "/api/results",
        params={"author": "Alice", "include_replies": "false"},
    )
    replies_only = await client.get(
        "/api/results",
        params={"author": "Alice", "include_posts": "false"},
    )

    assert combined.status_code == 200
    assert result_ids(combined.json()["items"]) == [
        ("reply", "102"),
        ("post", "100"),
    ]

    assert posts_only.status_code == 200
    assert [(item["record_type"], item["post_id"]) for item in posts_only.json()["items"]] == [
        ("post", "100")
    ]

    assert replies_only.status_code == 200
    assert [(item["record_type"], item["reply_id"]) for item in replies_only.json()["items"]] == [
        ("reply", "102")
    ]


@pytest.mark.anyio
async def test_results_support_reply_search_and_pagination(client: httpx.AsyncClient) -> None:
    search_response = await client.get("/api/results", params={"search": "nested"})
    page_response = await client.get("/api/results", params={"limit": 2, "offset": 1})
    empty_scope_response = await client.get(
        "/api/results",
        params={"include_posts": "false", "include_replies": "false"},
    )

    assert search_response.status_code == 200
    assert reply_result_ids(search_response.json()["items"]) == [("reply", "102")]

    assert page_response.status_code == 200
    page_payload = page_response.json()
    assert page_payload["total"] == 5
    assert page_payload["limit"] == 2
    assert page_payload["offset"] == 1
    assert result_ids(page_payload["items"]) == [
        ("post", "200"),
        ("reply", "102"),
    ]

    assert empty_scope_response.status_code == 200
    assert empty_scope_response.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


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
