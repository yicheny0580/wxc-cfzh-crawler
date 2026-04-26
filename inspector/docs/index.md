# Inspector Index

The inspector provides a read-only browser UI over the crawler SQLite database.

## Source Map

- [../backend/app/main.py](../backend/app/main.py): FastAPI routes and static frontend serving.
- [../backend/app/db.py](../backend/app/db.py): read-only SQLite connection and query helpers.
- [../backend/app/schemas.py](../backend/app/schemas.py): API response schemas.
- [../frontend/src/App.tsx](../frontend/src/App.tsx): primary React UI.
- [../frontend/src/api.ts](../frontend/src/api.ts): frontend API client.
- [../backend/pyproject.toml](../backend/pyproject.toml): backend dependencies and tests.
- [../frontend/package.json](../frontend/package.json): frontend scripts and dependencies.

## Startup

From the repository root:

```bash
uv run wxc inspect
```

Useful options:

```bash
uv run wxc inspect --db data/crawler.sqlite3
uv run wxc inspect --host 127.0.0.1 --port 8765
uv run wxc inspect --skip-ui-build
```

`wxc inspect` refreshes frontend dependencies when `package.json` or `package-lock.json`
changes, rebuilds `../frontend`, then serves the UI and API through FastAPI.

## API

- `GET /api/health`
- `GET /api/summary`
- `GET /api/authors`
- `GET /api/results`
- `GET /api/posts`
- `GET /api/posts/{post_id}`

`GET /api/results` is the primary inspector list endpoint. It supports `search`,
`author`, `include_posts`, `include_replies`, `limit`, and `offset`. Reply results
include root post metadata so the frontend can open the original post and focus the
matching reply in context.

The backend opens SQLite with `mode=ro` and `PRAGMA query_only = ON`.

## Checks

```bash
uv run --project inspector/backend pytest inspector/backend/tests
npm --prefix inspector/frontend run build
```
