# syntax=docker/dockerfile:1.7

# ============================================================
# Build stage — cài uv, sync dependencies vào .venv cache
# ============================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.4 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY apps/web/pyproject.toml apps/web/pyproject.toml
COPY apps/judge-worker/pyproject.toml apps/judge-worker/pyproject.toml

RUN uv sync --frozen --no-dev --package oj-web

COPY apps/web/app ./apps/web/app
COPY apps/web/alembic ./apps/web/alembic
COPY apps/web/alembic.ini ./apps/web/alembic.ini
COPY apps/web/static ./apps/web/static


# ============================================================
# Runtime stage — chỉ cần Python + venv đã build sẵn
# ============================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=prod \
    PATH="/app/.venv/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl tini ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r oj && useradd -r -g oj -d /home/oj -m oj

WORKDIR /app
COPY --from=builder /app /app
RUN chown -R oj:oj /app

USER oj
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fs http://127.0.0.1:8000/healthz || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--app-dir", "apps/web"]
