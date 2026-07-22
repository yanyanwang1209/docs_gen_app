"""管理员 API 路由 — 用户管理"""
import secrets
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from backend.database import get_db
from backend.models.user import User
from backend.models.template import DocumentTemplate, ChapterNode
from backend.models.file import ManagedFile
from backend.models.document import GenerationTask
from backend.utils.auth import hash_password

router = APIRouter(prefix="/api/admin", tags=["管理员"])
logger = logging.getLogger(__name__)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(default="", min_length=0, max_length=256)


def require_admin(request: Request):
    """要求管理员权限"""
    user = getattr(request.state, "user", None)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")


@router.get("/users")
async def list_users(request: Request, db: AsyncSession = Depends(get_db)):
    """列出所有用户（仅管理员）"""
    require_admin(request)

    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    return {
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "is_admin": u.is_admin,
                "has_llm_config": bool(u.llm_api_key),
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": len(users),
    }


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """删除用户及其所有关联数据（仅管理员）"""
    require_admin(request)

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.is_admin:
        raise HTTPException(status_code=403, detail="不能删除管理员账户")

    # 删除关联数据
    # 1. 用户的模板章节
    user_templates = await db.execute(
        select(DocumentTemplate.id).where(DocumentTemplate.owner_id == user_id)
    )
    template_ids = [row[0] for row in user_templates.fetchall()]
    for tid in template_ids:
        await db.execute(delete(ChapterNode).where(ChapterNode.template_id == tid))
        await db.execute(delete(DocumentTemplate).where(DocumentTemplate.id == tid))

    # 2. 用户的文件
    await db.execute(delete(ManagedFile).where(ManagedFile.owner_id == user_id))

    # 3. 用户的生成任务
    await db.execute(delete(GenerationTask).where(GenerationTask.owner_id == user_id))

    # 4. 删除用户
    await db.delete(user)
    await db.commit()

    logger.info("管理员删除了用户: %s", user.username)
    return {"ok": True, "message": f"用户 {user.username} 已删除"}


@router.post("/users/{user_id}/reset-password")
async def reset_password(user_id: str, request: Request, data: ResetPasswordRequest = ResetPasswordRequest(), db: AsyncSession = Depends(get_db)):
    """重置用户密码（仅管理员）。可指定新密码，否则随机生成"""
    require_admin(request)

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    new_password = data.new_password.strip() if data.new_password and data.new_password.strip() else secrets.token_hex(8)
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")

    user.password_hash = hash_password(new_password)
    await db.commit()

    logger.info("管理员重置了用户 %s 的密码", user.username)
    return {"ok": True, "new_password": new_password, "message": f"用户 {user.username} 密码已重置"}