from __future__ import annotations

import asyncio
import socket
import sqlite3
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from app._db_connection import resolve_repo_root
from app._image_proxy import MAX_IMAGE_BYTES, ImageProxyFetchError, ProxiedImage, fetch_image_bytes
from app.crawl import CrawlManager, fetch_crawl_progress
from app.main import app
from app.settings import display_db_path


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


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.sent: list[dict[str, object]] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload: dict[str, object]) -> None:
        self.sent.append(payload)

    async def receive(self) -> dict[str, str]:
        return {"type": "websocket.disconnect"}


class FakeImageResponse:
    def __init__(self, content: bytes, content_type: str) -> None:
        self.headers = {"Content-Type": content_type}
        self._content = content

    def read(self, size: int = -1) -> bytes:
        return self._content if size < 0 else self._content[:size]

    def __enter__(self) -> FakeImageResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeImageOpener:
    def __init__(self, response: FakeImageResponse) -> None:
        self.response = response

    def open(
        self,
        fullurl: object,
        data: bytes | None = None,
        timeout: float | object = object(),
    ) -> FakeImageResponse:
        return self.response


async def wait_for_crawl_state(manager: CrawlManager, state: str) -> None:
    for _ in range(50):
        if manager.status().state == state:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"Crawl state did not become {state}.")


def create_progress_db(path: Path, *, include_suppressed_at: bool) -> None:
    suppressed_column = ", suppressed_at TEXT" if include_suppressed_at else ""
    conn = sqlite3.connect(path)
    conn.executescript(
        f"""
        CREATE TABLE posts (post_id TEXT PRIMARY KEY);
        CREATE TABLE replies (reply_id TEXT PRIMARY KEY);
        CREATE TABLE frontier (
            post_id TEXT PRIMARY KEY,
            record_type TEXT NOT NULL,
            status TEXT NOT NULL
            {suppressed_column}
        );
        INSERT INTO posts VALUES ('100');
        INSERT INTO replies VALUES ('101');
        """
    )
    if include_suppressed_at:
        conn.executemany(
            """
            INSERT INTO frontier (post_id, record_type, status, suppressed_at)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("100", "post", "failed", None),
                ("200", "post", "failed", "2026-05-09T00:00:00+00:00"),
                ("101", "reply", "done", None),
            ],
        )
    else:
        conn.executemany(
            "INSERT INTO frontier (post_id, record_type, status) VALUES (?, ?, ?)",
            [
                ("100", "post", "failed"),
                ("101", "reply", "done"),
            ],
        )
    conn.commit()
    conn.close()


def test_fetch_crawl_progress_separates_suppressed_failures(tmp_path: Path) -> None:
    path = tmp_path / "crawler.sqlite3"
    create_progress_db(path, include_suppressed_at=True)

    progress = fetch_crawl_progress(path)

    assert progress is not None
    assert progress.saved_posts == 1
    assert progress.saved_replies == 1
    assert progress.frontier["post"]["failed"] == 1
    assert progress.frontier["post"]["suppressed"] == 1
    assert progress.frontier["reply"]["done"] == 1


def test_fetch_crawl_progress_supports_databases_without_suppression_column(
    tmp_path: Path,
) -> None:
    path = tmp_path / "crawler.sqlite3"
    create_progress_db(path, include_suppressed_at=False)

    progress = fetch_crawl_progress(path)

    assert progress is not None
    assert progress.frontier["post"]["failed"] == 1
    assert progress.frontier["post"]["suppressed"] == 0


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

        CREATE VIRTUAL TABLE posts_fts USING fts5(
            post_id UNINDEXED,
            title,
            author,
            body_text,
            tokenize = 'trigram'
        );

        CREATE VIRTUAL TABLE replies_fts USING fts5(
            reply_id UNINDEXED,
            root_post_id UNINDEXED,
            title,
            author,
            body_text,
            tokenize = 'trigram'
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
                "Apple PE and market structure notes.",
                (
                    "<div id=\"msgbodyContent\"><p>Apple PE<br>and market structure notes.</p>"
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
                "Nested PE reply body",
                "<p>Nested PE reply body</p>",
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
    conn.execute(
        """
        INSERT INTO posts_fts(rowid, post_id, title, author, body_text)
        SELECT CAST(post_id AS INTEGER), post_id, title, author, body_text FROM posts
        """
    )
    conn.execute(
        """
        INSERT INTO replies_fts(rowid, reply_id, root_post_id, title, author, body_text)
        SELECT CAST(reply_id AS INTEGER), reply_id, root_post_id, title, author, body_text
        FROM replies
        """
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


@pytest.fixture()
async def public_client(
    monkeypatch: pytest.MonkeyPatch,
    db_path: Path,
) -> AsyncIterator[httpx.AsyncClient]:
    monkeypatch.setenv("WXC_INSPECT_DB", str(db_path))
    monkeypatch.setenv("WXC_INSPECT_PUBLIC", "1")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client


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
    assert payload["all_pages"] is False
    assert payload["db_path"] == display_db_path(str(db_path))
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
async def test_crawl_start_supports_manual_all_pages(
    crawl_client: tuple[httpx.AsyncClient, CrawlManager, FakeSubprocessFactory],
) -> None:
    client, manager, factory = crawl_client

    response = await client.post("/api/crawl", json={"all_pages": True})

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "running"
    assert payload["pages"] == 5
    assert payload["all_pages"] is True

    command, _ = factory.commands[0]
    assert "pages=all" in command

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


@pytest.mark.anyio
async def test_crawl_websocket_sends_initial_status(
    monkeypatch: pytest.MonkeyPatch,
    db_path: Path,
) -> None:
    monkeypatch.setenv("WXC_INSPECT_DB", str(db_path))
    manager = CrawlManager(subprocess_factory=FakeSubprocessFactory())
    websocket = FakeWebSocket()

    await manager.subscribe(websocket)  # type: ignore[arg-type]

    payload = websocket.sent[0]
    assert websocket.accepted is True
    assert payload["state"] == "idle"
    assert payload["db_path"] == display_db_path(str(db_path))


@pytest.mark.anyio
async def test_public_mode_hides_db_path_and_blocks_crawl_controls(
    public_client: httpx.AsyncClient,
    db_path: Path,
) -> None:
    health_response = await public_client.get("/api/health")
    summary_response = await public_client.get("/api/summary")
    status_response = await public_client.get("/api/crawl/status")
    start_response = await public_client.post("/api/crawl", json={})
    stop_response = await public_client.post("/api/crawl/stop")

    assert health_response.status_code == 200
    assert health_response.json()["public_mode"] is True
    assert health_response.json()["db_path"] == "SQLite database"
    assert str(db_path) not in health_response.text

    assert summary_response.status_code == 200
    assert summary_response.json()["db_path"] == "SQLite database"
    assert str(db_path) not in summary_response.text

    assert status_response.status_code == 404
    assert start_response.status_code == 404
    assert stop_response.status_code == 404


def test_display_db_path_uses_relative_repo_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WXC_INSPECT_PUBLIC", raising=False)

    db_path = resolve_repo_root() / "data" / "crawler.sqlite3"

    assert display_db_path(str(db_path)) == "data/crawler.sqlite3"


def test_display_db_path_hides_external_parent_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("WXC_INSPECT_PUBLIC", raising=False)

    assert display_db_path(str(tmp_path / "private.sqlite3")) == "private.sqlite3"


@pytest.mark.anyio
async def test_summary_counts(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["posts"] == 2
    assert payload["replies"] == 3
    assert payload["authors"] == 3
    assert payload["latest_crawl_at"] == "2026-04-25T10:02:30"
    assert payload["latest_post_published_at"] == "2026-04-25T09:30:00-07:00"


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
async def test_post_list_supports_published_date_filter(client: httpx.AsyncClient) -> None:
    exact_response = await client.get(
        "/api/posts",
        params={"published_from": "2026-04-25", "published_to": "2026-04-25"},
    )
    before_response = await client.get("/api/posts", params={"published_to": "2026-04-24"})
    author_response = await client.get(
        "/api/posts",
        params={"author": "Bob", "published_from": "2026-04-25"},
    )

    assert exact_response.status_code == 200
    assert [item["post_id"] for item in exact_response.json()["items"]] == ["200", "100"]

    assert before_response.status_code == 200
    assert before_response.json()["items"] == []

    assert author_response.status_code == 200
    assert [item["post_id"] for item in author_response.json()["items"]] == ["200"]


@pytest.mark.anyio
async def test_undated_records_sort_after_dated_records(
    client: httpx.AsyncClient,
    db_path: Path,
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO posts (
                post_id, url, forum, title, author, author_profile_url, published_at, edited_at,
                body_text, body_html, byte_count, read_count, reply_count, crawled_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "999",
                "https://bbs.wenxuecity.com/cfzh/999.html",
                "cfzh",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "2026-04-25T11:00:00",
            ),
        )
        conn.commit()

    posts_response = await client.get("/api/posts", params={"limit": 3})
    results_response = await client.get(
        "/api/results",
        params={"include_posts": "true", "include_replies": "false", "limit": 3},
    )

    assert posts_response.status_code == 200
    assert [item["post_id"] for item in posts_response.json()["items"]] == [
        "200",
        "100",
        "999",
    ]

    assert results_response.status_code == 200
    assert result_ids(results_response.json()["items"]) == [
        ("post", "200"),
        ("post", "100"),
        ("post", "999"),
    ]


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
    assert reply["published_at"] == "2026-04-25T09:35:00-07:00"
    assert reply["excerpt"] == "Another root reply"


@pytest.mark.anyio
async def test_results_exclude_root_post_ids(client: httpx.AsyncClient) -> None:
    response = await client.get(
        "/api/results",
        params=[("exclude_root_post_id", "100")],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert result_ids(payload["items"]) == [
        ("reply", "201"),
        ("post", "200"),
    ]


@pytest.mark.anyio
async def test_published_date_filter_uses_requested_timezone(
    client: httpx.AsyncClient,
    db_path: Path,
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE posts SET published_at = '2026-04-25T23:30:00' WHERE post_id = '100'")

    eastern_response = await client.get(
        "/api/results",
        params={
            "include_replies": "false",
            "published_from": "2026-04-26",
            "published_to": "2026-04-26",
            "published_timezone": "America/New_York",
        },
    )
    default_response = await client.get(
        "/api/results",
        params={
            "include_replies": "false",
            "published_from": "2026-04-26",
            "published_to": "2026-04-26",
        },
    )

    assert eastern_response.status_code == 200
    assert result_ids(eastern_response.json()["items"]) == [("post", "100")]
    assert eastern_response.json()["items"][0]["published_at"] == "2026-04-25T23:30:00-07:00"

    assert default_response.status_code == 200
    assert default_response.json()["items"] == []


@pytest.mark.anyio
async def test_published_date_filter_rejects_invalid_timezone(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get(
        "/api/results",
        params={
            "published_from": "2026-04-25",
            "published_timezone": "No/SuchZone",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown timezone: No/SuchZone"


@pytest.mark.anyio
async def test_results_support_published_date_filter(client: httpx.AsyncClient) -> None:
    exact_response = await client.get(
        "/api/results",
        params={"published_from": "2026-04-25", "published_to": "2026-04-25"},
    )
    before_response = await client.get("/api/results", params={"published_to": "2026-04-24"})
    after_response = await client.get("/api/results", params={"published_from": "2026-04-26"})

    assert exact_response.status_code == 200
    assert result_ids(exact_response.json()["items"]) == [
        ("reply", "201"),
        ("post", "200"),
        ("reply", "102"),
        ("reply", "101"),
        ("post", "100"),
    ]

    assert before_response.status_code == 200
    assert before_response.json()["items"] == []

    assert after_response.status_code == 200
    assert after_response.json()["items"] == []


@pytest.mark.anyio
async def test_results_published_date_filter_composes_and_excludes_undated(
    client: httpx.AsyncClient,
    db_path: Path,
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE posts SET published_at = NULL WHERE post_id = '100'")
        conn.execute(
            "UPDATE replies SET published_at = '2026-04-24T09:05:00' WHERE reply_id = '101'"
        )

    unfiltered_posts = await client.get("/api/results", params={"include_replies": "false"})
    dated_posts = await client.get(
        "/api/results",
        params={
            "include_replies": "false",
            "published_from": "2026-04-25",
            "published_to": "2026-04-25",
        },
    )
    filtered_replies = await client.get(
        "/api/results",
        params={
            "author": "Carol",
            "include_posts": "false",
            "published_from": "2026-04-25",
            "published_to": "2026-04-25",
        },
    )

    assert unfiltered_posts.status_code == 200
    assert result_ids(unfiltered_posts.json()["items"]) == [("post", "200"), ("post", "100")]

    assert dated_posts.status_code == 200
    assert result_ids(dated_posts.json()["items"]) == [("post", "200")]

    assert filtered_replies.status_code == 200
    assert result_ids(filtered_replies.json()["items"]) == [("reply", "201")]


@pytest.mark.anyio
async def test_results_reject_invalid_published_date_ranges(client: httpx.AsyncClient) -> None:
    reversed_response = await client.get(
        "/api/results",
        params={"published_from": "2026-04-26", "published_to": "2026-04-25"},
    )
    invalid_response = await client.get("/api/posts", params={"published_from": "not-a-date"})

    assert reversed_response.status_code == 422
    assert invalid_response.status_code == 422


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
async def test_search_supports_two_character_terms(client: httpx.AsyncClient) -> None:
    results_response = await client.get("/api/results", params={"search": "PE"})
    posts_response = await client.get("/api/posts", params={"search": "PE"})
    replies_only_response = await client.get(
        "/api/results",
        params={"search": "PE", "include_posts": "false"},
    )
    mixed_term_response = await client.get("/api/results", params={"search": "PE apple"})

    assert results_response.status_code == 200
    assert result_ids(results_response.json()["items"]) == [("reply", "102"), ("post", "100")]

    assert posts_response.status_code == 200
    assert [item["post_id"] for item in posts_response.json()["items"]] == ["100"]

    assert replies_only_response.status_code == 200
    assert reply_result_ids(replies_only_response.json()["items"]) == [("reply", "102")]

    assert mixed_term_response.status_code == 200
    assert result_ids(mixed_term_response.json()["items"]) == [("post", "100")]


@pytest.mark.anyio
async def test_two_character_search_treats_wildcards_literally(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/api/results", params={"search": "P%"})

    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.anyio
async def test_search_rejects_one_character_terms(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/results", params={"search": "P"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Search terms must be at least 2 characters."


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
    assert payload["published_at"] == "2026-04-25T09:00:00-07:00"
    assert "<br>" in payload["body_html"]
    assert "/upload/alpha.jpeg" in payload["body_html"]
    assert payload["replies"][0]["reply_id"] == "101"
    assert payload["replies"][0]["published_at"] == "2026-04-25T09:05:00-07:00"
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


@pytest.mark.anyio
async def test_post_image_proxy_returns_stored_post_image(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetched_urls: list[str] = []

    def fake_fetch(url: str) -> ProxiedImage:
        fetched_urls.append(url)
        return ProxiedImage(content=b"png-bytes", media_type="image/png")

    monkeypatch.setattr("app.main.fetch_image_bytes", fake_fetch)

    response = await client.get("/api/posts/100/image", params={"src": "/upload/alpha.jpeg"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"png-bytes"
    assert fetched_urls == ["https://bbs.wenxuecity.com/upload/alpha.jpeg"]


@pytest.mark.anyio
async def test_post_image_proxy_rejects_images_outside_post_body(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch(url: str) -> ProxiedImage:
        raise AssertionError(f"Unexpected image fetch for {url}")

    monkeypatch.setattr("app.main.fetch_image_bytes", fake_fetch)

    response = await client.get("/api/posts/100/image", params={"src": "/upload/reply.jpeg"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Image URL is not part of the requested post."


@pytest.mark.anyio
async def test_post_image_proxy_rejects_private_network_image(
    client: httpx.AsyncClient,
    db_path: Path,
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO posts (
                post_id, url, forum, title, author, author_profile_url, published_at, edited_at,
                body_text, body_html, byte_count, read_count, reply_count, crawled_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "300",
                "https://bbs.wenxuecity.com/cfzh/300.html",
                "cfzh",
                "Private image",
                "Dana",
                None,
                "2026-04-25T10:00:00",
                None,
                "Private image body",
                '<p><img src="http://127.0.0.1/private.png"></p>',
                18,
                1,
                0,
                "2026-04-25T10:03:00",
            ),
        )

    response = await client.get(
        "/api/posts/300/image",
        params={"src": "http://127.0.0.1/private.png"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Image host resolves to a private or local network address."
    )


def test_fetch_image_bytes_rejects_non_image_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app._image_proxy.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )
    opener = FakeImageOpener(FakeImageResponse(b"<html></html>", "text/html; charset=utf-8"))

    with pytest.raises(ImageProxyFetchError, match="not a supported image"):
        fetch_image_bytes("https://example.com/chart.png", opener=opener)


def test_fetch_image_bytes_rejects_oversized_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app._image_proxy.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )
    opener = FakeImageOpener(FakeImageResponse(b"x" * (MAX_IMAGE_BYTES + 1), "image/png"))

    with pytest.raises(ImageProxyFetchError, match="too large"):
        fetch_image_bytes("https://example.com/chart.png", opener=opener)
