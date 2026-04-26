from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
    HealthResponse,
    PostDetail,
    PostListResponse,
    ResultListResponse,
    SummaryResponse,
)

app = FastAPI(title="WXC CFZH SQLite Inspector")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

Connection = Annotated[sqlite3.Connection, Depends(get_connection)]


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    db_path = resolve_db_path()
    if not db_path.exists():
        return HealthResponse(
            ok=False,
            db_path=str(db_path),
            db_exists=False,
            detail="SQLite database does not exist.",
        )

    try:
        conn = connect_readonly(db_path)
        conn.execute("SELECT 1").fetchone()
    except sqlite3.Error as exc:
        return HealthResponse(
            ok=False,
            db_path=str(db_path),
            db_exists=True,
            detail=str(exc),
        )
    finally:
        if "conn" in locals():
            conn.close()

    return HealthResponse(ok=True, db_path=str(db_path), db_exists=True)


@app.get("/api/summary", response_model=SummaryResponse)
async def summary(conn: Connection) -> dict[str, object]:
    return fetch_summary(conn)


@app.get("/api/authors", response_model=list[AuthorSummary])
async def authors(conn: Connection) -> list[dict[str, object]]:
    return fetch_authors(conn)


@app.get("/api/posts", response_model=PostListResponse)
async def posts(
    conn: Connection,
    search: str | None = Query(default=None, max_length=200),
    author: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    return fetch_posts(conn, search=search, author=author, limit=limit, offset=offset)


@app.get("/api/results", response_model=ResultListResponse)
async def results(
    conn: Connection,
    search: str | None = Query(default=None, max_length=200),
    author: str | None = Query(default=None, max_length=200),
    include_posts: bool = Query(default=True),
    include_replies: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    return fetch_results(
        conn,
        search=search,
        author=author,
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
