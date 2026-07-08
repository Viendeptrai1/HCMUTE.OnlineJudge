"""FastAPI entrypoint.

Trách nhiệm: khởi tạo app, mount static, gắn middleware, đăng ký router từ các module.
Không chứa business logic — các module tự xử lý bên trong `app.modules.*`.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.modules.contests.router import router as contests_router
from app.modules.courses.router import router as courses_router
from app.modules.problems.router import router as problems_router
from app.modules.submissions.router import router as submissions_router
from app.modules.testcases.router import router as testcases_router
from app.modules.users.profile_router import router as profile_router
from app.modules.users.router import router as auth_router
from app.shared.observability import RequestIDMiddleware, configure_logging, metrics_endpoint
from app.shared.ratelimit import DEFAULT_RULES, RateLimitConfig, RateLimitMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.is_local)

    app = FastAPI(
        title="HCMUTE Online Judge API",
        version="0.1.0",
        debug=settings.is_local,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate-limit middleware phải được add SAU SessionMiddleware để có quyền đọc session.
    # Trong test / khi disable cờ → rules=() → middleware pass-through.
    rl_rules = DEFAULT_RULES if settings.ratelimit_enabled else ()
    app.add_middleware(RateLimitMiddleware, config=RateLimitConfig(rules=rl_rules))
    app.add_middleware(RequestIDMiddleware)

    @app.get("/", include_in_schema=False)
    async def index() -> RedirectResponse:
        return RedirectResponse(url="/problems")

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return metrics_endpoint()

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception):  # type: ignore[no-untyped-def]
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    app.include_router(auth_router)
    app.include_router(problems_router)
    # Router testcases đăng ký SAU problems để tránh match nhầm "/problems/{id}"
    # (FastAPI resolve theo thứ tự đăng ký).
    app.include_router(testcases_router)
    app.include_router(submissions_router)
    app.include_router(courses_router)
    app.include_router(contests_router)
    app.include_router(profile_router)

    return app


app = create_app()
handler = Mangum(app)
