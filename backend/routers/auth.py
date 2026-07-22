"""认证 API 路由 — 登录、注册"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.user import User
from backend.schemas.auth import LoginRequest, RegisterRequest, AuthResponse, UserInfo, ChangePasswordRequest
from backend.utils.auth import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/api/auth", tags=["认证"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="用户名已存在")

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.username, user.is_admin)
    logger.info("用户注册成功: %s", user.username)
    return AuthResponse(
        token=token,
        user_id=user.id,
        username=user.username,
        is_admin=user.is_admin,
    )


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(user.id, user.username, user.is_admin)
    logger.info("用户登录成功: %s", user.username)
    return AuthResponse(
        token=token,
        user_id=user.id,
        username=user.username,
        is_admin=user.is_admin,
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """获取当前用户信息"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return UserInfo(
        user_id=user.id,
        username=user.username,
        is_admin=user.is_admin,
        has_llm_config=bool(user.llm_api_key),
    )


@router.get("/check")
async def check_auth(request: Request):
    """检查当前登录状态（用于前端初始化）"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return {"authenticated": False}

    token = auth_header[7:]
    payload = decode_access_token(token)
    if not payload:
        return {"authenticated": False}

    return {
        "authenticated": True,
        "user_id": payload.get("sub"),
        "username": payload.get("username"),
        "is_admin": payload.get("is_admin", False),
    }


@router.post("/change-password")
async def change_password(data: ChangePasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """用户自主修改密码"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")

    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")

    user.password_hash = hash_password(data.new_password)
    await db.commit()
    logger.info("用户 %s 修改了密码", user.username)
    return {"ok": True, "message": "密码修改成功"}