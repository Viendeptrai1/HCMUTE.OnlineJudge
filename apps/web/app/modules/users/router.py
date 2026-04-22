"""Auth routes: register / login / logout / me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.core.templating import templates
from app.modules.users.dependencies import get_user_service, require_user
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserCreate
from app.modules.users.service import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserService,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request) -> Response:
    return templates.TemplateResponse(request, "auth/login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    identifier: str = Form(...),
    password: str = Form(...),
    service: UserService = Depends(get_user_service),
) -> Response:
    try:
        user = await service.authenticate(identifier, password)
    except InvalidCredentialsError:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"error": "Email/username hoặc mật khẩu không đúng."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    request.session["user_id"] = str(user.id)
    return RedirectResponse(url="/problems", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request) -> Response:
    return templates.TemplateResponse(
        request,
        "auth/register.html",
        {"error": None, "roles": list(UserRole)},
    )


@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    role: UserRole = Form(UserRole.STUDENT),
    service: UserService = Depends(get_user_service),
) -> Response:
    try:
        data = UserCreate(
            email=email,
            username=username,
            password=password,
            full_name=full_name,
            role=role,
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            {"error": _format_validation_error(exc), "roles": list(UserRole)},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = await service.register(data)
    except UserAlreadyExistsError as exc:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            {"error": str(exc), "roles": list(UserRole)},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    request.session["user_id"] = str(user.id)
    return RedirectResponse(url="/problems", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
async def logout(request: Request) -> Response:
    request.session.pop("user_id", None)
    return RedirectResponse(url="/problems", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/me", response_class=HTMLResponse)
async def me(request: Request, user: User = Depends(require_user)) -> Response:
    return templates.TemplateResponse(request, "auth/me.html", {"current_user": user})


def _format_validation_error(exc: ValidationError) -> str:
    msgs = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        msgs.append(f"{loc}: {err['msg']}")
    return "; ".join(msgs)
