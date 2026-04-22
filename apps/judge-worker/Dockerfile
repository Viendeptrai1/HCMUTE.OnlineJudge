# syntax=docker/dockerfile:1.7

# ============================================================
# Build stage
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

RUN uv sync --frozen --no-dev --package oj-judge-worker

COPY apps/judge-worker/worker ./apps/judge-worker/worker


# ============================================================
# Runtime — cần g++ để compile C++ submissions + python3
# ============================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=prod \
    PATH="/app/.venv/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
      g++ tini ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r oj && useradd -r -g oj -d /home/oj -m oj

WORKDIR /app/apps/judge-worker
COPY --from=builder /app /app
RUN chown -R oj:oj /app

USER oj

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "worker.main"]
