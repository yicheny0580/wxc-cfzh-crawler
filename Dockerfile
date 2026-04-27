FROM node:22-slim AS frontend-build
WORKDIR /app/inspector/frontend
COPY inspector/frontend/package.json inspector/frontend/package-lock.json ./
RUN npm ci
COPY inspector/frontend ./
RUN npm run build

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}" \
    WXC_INSPECT_PUBLIC=1 \
    WXC_INSPECT_DB=/data/crawler.sqlite3 \
    WXC_ADMIN_DB=/data/crawler.sqlite3 \
    WXC_ADMIN_DATA_DIR=/data

WORKDIR /app
RUN pip install --no-cache-dir uv
COPY . .
COPY --from=frontend-build /app/inspector/frontend/dist /app/inspector/frontend/dist
RUN uv sync --frozen --no-dev

EXPOSE 8765
CMD ["uvicorn", "app.main:app", "--app-dir", "inspector/backend", "--host", "0.0.0.0", "--port", "8765"]
