"""FastAPI entrypoint.

Trách nhiệm: khởi tạo app, mount static, gắn middleware, đăng ký router từ các module.
Không chứa business logic — các module tự xử lý bên trong `app.modules.*`.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from mangum import Mangum
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.templating import templates
from app.modules.problems.router import router as problems_router
from app.modules.submissions.router import router as submissions_router
from app.modules.users.repository import SqlAlchemyUserRepository
from app.modules.users.router import router as auth_router
from app.modules.users.service import UserService
from app.shared.exceptions import EntityNotFoundError

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="HCMUTE Online Judge",
        version="0.1.0",
        debug=settings.is_local,
    )

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Thứ tự đăng ký quan trọng: starlette `add_middleware` insert vào đầu stack,
    # đồng thời stack được áp từ phải qua (ServerError → user_middleware[:]).
    # Kết quả là MW đăng ký SAU sẽ chạy TRƯỚC MW đăng ký trước.
    # => Muốn `inject_current_user` chạy SAU `SessionMiddleware` thì
    #    SessionMiddleware phải được add SAU.

    @app.middleware("http")
    async def inject_current_user(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Đọc user_id trong session → nạp User vào request.state để template dùng."""

        request.state.current_user = None
        user_id_str = request.session.get("user_id") if "session" in request.scope else None
        if user_id_str:
            try:
                async with SessionLocal() as db:
                    service = UserService(SqlAlchemyUserRepository(db))
                    request.state.current_user = await service.get_by_id(UUID(user_id_str))
            except (ValueError, EntityNotFoundError):
                request.session.pop("user_id", None)
        return await call_next(request)

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="oj_session",
        max_age=60 * 60 * 24 * 7,
        same_site="lax",
        https_only=not settings.is_local,
    )

    @app.get("/", include_in_schema=False)
    async def index() -> RedirectResponse:
        return RedirectResponse(url="/problems")

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception):  # type: ignore[no-untyped-def]
        return templates.TemplateResponse(
            request,
            "errors/404.html",
            {"path": request.url.path},
            status_code=404,
        )

    app.include_router(auth_router)
    app.include_router(problems_router)
    app.include_router(submissions_router)

    return app


app = create_app()
handler = Mangum(app)
