"""LLM 配置管理 API — per-user 配置"""
import os
import re
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.document import GlobalConfig
from backend.models.user import User
from backend.services.llm_client import get_llm_client, reset_llm_client
from backend.utils.text_utils import mask_api_key
from backend.config import settings

router = APIRouter(prefix="/api/llm", tags=["LLM配置"])


class LLMConfigOut(BaseModel):
    base_url: str = ""
    api_key: str = ""  # 脱敏后的 Key
    model: str = ""
    models: dict = {}  # 各文档类型专用模型
    global_requirements: str = ""
    source: str = "default"  # "user" | "default"


class LLMConfigUpdate(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    models: dict | None = None
    global_requirements: str | None = None


def _get_user_llm(db: AsyncSession, user_id: str) -> tuple:
    """获取用户的 LLM 配置，返回 (base_url, api_key, model)"""
    # 暂未实现 per-user 查询时，使用 settings 默认值
    return settings.llm_base_url, settings.llm_api_key, settings.llm_model


async def _get_user_llm_async(db: AsyncSession, user_id: str) -> tuple:
    """异步获取用户的 LLM 配置"""
    if user_id:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            # 只要用户设置了任意一项，就使用个人配置（未设置的用默认值）
            has_personal = user.llm_api_key or user.llm_base_url or user.llm_model
            if has_personal:
                return (
                    user.llm_base_url or settings.llm_base_url,
                    user.llm_api_key or settings.llm_api_key,
                    user.llm_model or settings.llm_model,
                )
    return settings.llm_base_url, settings.llm_api_key, settings.llm_model


@router.get("/config", response_model=LLMConfigOut)
async def get_config(request: Request, db: AsyncSession = Depends(get_db)):
    """获取当前用户的 LLM 配置（API Key 脱敏）"""
    user_id = getattr(request.state, "user_id", None)
    base_url, api_key, model = await _get_user_llm_async(db, user_id)
    # 判断是否使用个人配置：用户设置了任意 LLM 字段即为个人配置
    source = "default"
    if user_id:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user and (user.llm_api_key or user.llm_base_url or user.llm_model):
            source = "user"

    # 全局写作要求（共享）
    global_req = ""
    result = await db.execute(
        select(GlobalConfig).where(GlobalConfig.key == "global_requirements")
    )
    row = result.scalar_one_or_none()
    if row:
        global_req = row.value

    return LLMConfigOut(
        base_url=base_url,
        api_key=mask_api_key(api_key),
        model=model,
        models={
            "srs": settings.llm_model_srs or "",
            "hld": settings.llm_model_hld or "",
            "dd": settings.llm_model_dd or "",
            "dbd": settings.llm_model_dbd or "",
            "tp": settings.llm_model_tp or "",
            "ts": settings.llm_model_ts or "",
            "tc": settings.llm_model_tc or "",
            "tr": settings.llm_model_tr or "",
            "trep": settings.llm_model_trep or "",
        },
        global_requirements=global_req,
        source=source,
    )


@router.put("/config", response_model=LLMConfigOut)
async def update_config(data: LLMConfigUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    """更新当前用户的 LLM 配置（保存到 User 表）"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if data.base_url is not None:
        user.llm_base_url = data.base_url
    if data.api_key is not None:
        # 如果 API key 包含脱敏占位符 *，说明用户没有修改 key，跳过更新
        if "*" not in data.api_key:
            user.llm_api_key = data.api_key
    if data.model is not None:
        user.llm_model = data.model
    # models 字段暂不支持 per-user（使用全局 settings），保留接口兼容性

    # 保存全局写作要求（共享）
    if data.global_requirements is not None:
        result = await db.execute(
            select(GlobalConfig).where(GlobalConfig.key == "global_requirements")
        )
        row = result.scalar_one_or_none()
        if row:
            row.value = data.global_requirements
        else:
            db.add(GlobalConfig(key="global_requirements", value=data.global_requirements))

    await db.commit()
    reset_llm_client()
    return await get_config(request, db)


class LLMTestRequest(BaseModel):
    base_url: str = ""
    api_key: str = ""
    model: str = ""


@router.post("/test")
async def test_connection(data: LLMTestRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """测试 LLM 连接（使用前端传入的配置值，不依赖已保存的配置）"""
    user_id = getattr(request.state, "user_id", None)
    # 优先使用前端传入的值，如果 api_key 是脱敏的（含 *），则从数据库读取真实值
    base_url = data.base_url
    api_key = data.api_key
    model = data.model
    if not api_key or "*" in api_key:
        # 用户未修改 key，使用已保存的真实 key 或系统默认值
        _, saved_key, _ = await _get_user_llm_async(db, user_id)
        api_key = saved_key
    if not base_url:
        base_url, _, _ = await _get_user_llm_async(db, user_id)
    if not model:
        _, _, model = await _get_user_llm_async(db, user_id)
    client = get_llm_client(base_url=base_url, api_key=api_key, model=model)
    return await client.test_connection()