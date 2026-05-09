from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app._image_proxy import (
    ImageProxyFetchError,
    ImageProxyInputError,
    fetch_image_bytes,
    require_post_image_url,
)
from app._time import local_date_filter_bounds
from app.crawl import crawl_manager
from app.db import (
    build_reply_tree,
    connect_readonly,
    fetch_authors,
    fetch_post,
    fetch_posts,
    fetch_reply_rows,
    fetch_results,
    fetch_summary,
    get_connection,
    resolve_db_path,
)
from app.schemas import (
    AuthorSummary,
    CrawlStartRequest,
    CrawlStatusResponse,
    HealthResponse,
    PostDetail,
    PostListResponse,
    ResultListResponse,
    SummaryResponse,
)
from app.settings import display_db_path, inspect_public_mode

app = FastAPI(title="WXC CFZH SQLite Inspector")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

Connection = Annotated[sqlite3.Connection, Depends(get_connection)]
PublishedDateQuery = Annotated[date | None, Query()]
PublishedTimezoneQuery = Annotated[str | None, Query(max_length=100)]


def validate_published_filters(
    published_from: date | None,
    published_to: date | None,
    published_timezone: str | None,
) -> tuple[str | None, str | None]:
    if published_from and published_to and published_from > published_to:
        raise HTTPException(
            status_code=422,
            detail="published_from must be on or before published_to.",
        )
    try:
        return local_date_filter_bounds(
            published_from=published_from,
            published_to=published_to,
            timezone_name=published_timezone,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def validate_search(search: str | None) -> str | None:
    try:
        from app._db_helpers import fts_query

        fts_query(search)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return search


def require_crawl_controls_enabled() -> None:
    if inspect_public_mode():
        raise HTTPException(status_code=404, detail="Crawl controls are disabled.")


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    db_path = resolve_db_path()
    public_mode = inspect_public_mode()
    display_path = display_db_path(str(db_path))
    if not db_path.exists():
        return HealthResponse(
            ok=False,
            db_path=display_path,
            db_exists=False,
            public_mode=public_mode,
            detail="SQLite database does not exist.",
        )

    try:
        conn = connect_readonly(db_path)
        conn.execute("SELECT 1").fetchone()
    except sqlite3.Error as exc:
        return HealthResponse(
            ok=False,
            db_path=display_path,
            db_exists=True,
            public_mode=public_mode,
            detail=str(exc),
        )
    finally:
        if "conn" in locals():
            conn.close()

    return HealthResponse(
        ok=True,
        db_path=display_path,
        db_exists=True,
        public_mode=public_mode,
    )


@app.get("/api/summary", response_model=SummaryResponse)
async def summary(conn: Connection) -> dict[str, object]:
    payload = fetch_summary(conn)
    payload["db_path"] = display_db_path(str(payload["db_path"]))
    return payload


@app.get("/api/authors", response_model=list[AuthorSummary])
async def authors(conn: Connection) -> list[dict[str, object]]:
    return fetch_authors(conn)


@app.get("/api/posts", response_model=PostListResponse)
async def posts(
    conn: Connection,
    search: str | None = Query(default=None, max_length=200),
    author: str | None = Query(default=None, max_length=200),
    published_from: PublishedDateQuery = None,
    published_to: PublishedDateQuery = None,
    published_timezone: PublishedTimezoneQuery = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    search = validate_search(search)
    from_text, before_text = validate_published_filters(
        published_from,
        published_to,
        published_timezone,
    )
    return fetch_posts(
        conn,
        search=search,
        author=author,
        published_from=from_text,
        published_before=before_text,
        limit=limit,
        offset=offset,
    )


@app.get("/api/results", response_model=ResultListResponse)
async def results(
    conn: Connection,
    search: str | None = Query(default=None, max_length=200),
    author: str | None = Query(default=None, max_length=200),
    published_from: PublishedDateQuery = None,
    published_to: PublishedDateQuery = None,
    published_timezone: PublishedTimezoneQuery = None,
    include_posts: bool = Query(default=True),
    include_replies: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    search = validate_search(search)
    from_text, before_text = validate_published_filters(
        published_from,
        published_to,
        published_timezone,
    )
    return fetch_results(
        conn,
        search=search,
        author=author,
        published_from=from_text,
        published_before=before_text,
        include_posts=include_posts,
        include_replies=include_replies,
        limit=limit,
        offset=offset,
    )


@app.get("/api/posts/{post_id}", response_model=PostDetail)
async def post_detail(post_id: str, conn: Connection) -> dict[str, object]:
    post = fetch_post(conn, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail=f"Post {post_id} was not found.")
    post["replies"] = build_reply_tree(fetch_reply_rows(conn, post_id))
    return post


@app.get("/api/posts/{post_id}/image")
async def post_image(
    post_id: str,
    conn: Connection,
    src: str = Query(..., max_length=2048),
) -> Response:
    post = fetch_post(conn, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail=f"Post {post_id} was not found.")

    body_html = post.get("body_html")
    if not isinstance(body_html, str):
        body_html = None

    try:
        image_url = require_post_image_url(body_html, src)
        image = await run_in_threadpool(fetch_image_bytes, image_url)
    except ImageProxyInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ImageProxyFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return Response(
        content=image.content,
        media_type=image.media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/api/crawl/status", response_model=CrawlStatusResponse)
async def crawl_status() -> CrawlStatusResponse:
    require_crawl_controls_enabled()
    return crawl_manager.status()


@app.post("/api/crawl", response_model=CrawlStatusResponse)
async def start_crawl(request: CrawlStartRequest) -> CrawlStatusResponse:
    require_crawl_controls_enabled()
    started, status = await crawl_manager.start(pages=request.pages)
    if not started:
        raise HTTPException(status_code=409, detail=status.model_dump(mode="json"))
    return status


@app.post("/api/crawl/stop", response_model=CrawlStatusResponse)
async def stop_crawl() -> CrawlStatusResponse:
    require_crawl_controls_enabled()
    return await crawl_manager.stop()


@app.websocket("/api/crawl/ws")
async def crawl_websocket(websocket: WebSocket) -> None:
    if inspect_public_mode():
        await websocket.close(code=1008, reason="Crawl controls are disabled.")
        return
    await crawl_manager.subscribe(websocket)


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_frontend(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found.")
        candidate = FRONTEND_DIST / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
