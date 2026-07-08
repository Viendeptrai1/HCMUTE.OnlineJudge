"""Auth routes: register / login / logout / me + profile public."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError
from app.shared.security import create_access_token
from app.modules.users.schemas import UserCreate
from app.shared.exceptions import DomainError, EntityNotFoundError

from app.modules.users.dependencies import get_user_service, require_user
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserCreate
from app.modules.users.service import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserService,
)

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    identifier: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/login")
async def login(
    data: LoginRequest,
    service: UserService = Depends(get_user_service),
) -> dict:
    try:
        # Gọi xuống tầng Service để xác thực người dùng
        user = await service.authenticate(data.identifier, data.password)
    except InvalidCredentialsError:
        # Nếu sai thông tin đăng nhập, trả về lỗi
        raise HTTPException(status_code=400, detail="Tài khoản hoặc mật khẩu không đúng")
    
    # Nếu xác thực thành công, tạo JWT token chứa User ID
    token = create_access_token({"sub": str(user.id)})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user.id)
    }


@router.post("/register")
async def register(
    data: UserCreate,
    service: UserService = Depends(get_user_service),
) -> dict:
    try:
        user = await service.register(data)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
    # Trả về thông tin User
    return {
        "message": "Đăng ký thành công",
        "user_id": str(user.id),
        "email": user.email
    }



@router.get("/me")
async def me(
    current_user: User = Depends(require_user)
) -> dict:
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "role": current_user.role.value
    }

@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    service: UserService = Depends(get_user_service)

) -> dict:
    token = service.generate_reset_token(data.email)
    reset_url = f"http://localhost:3000/reset-password?token={token}"

    return {
        "message": "Vui lòng kiểm tra email để đặt lại mật khẩu",
        "reset_url_debug": reset_url
    }

@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    service: UserService = Depends(get_user_service)
) -> dict:
    try:
        await service.reset_password(data.token, data.new_password)
    except (DomainError, EntityNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"message": "Đặt lại mật khẩu thành công"}