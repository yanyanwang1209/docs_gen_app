"""LLM 配置管理 API"""
import os
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.document import GlobalConfig
from backend.services.llm_client import get_llm_client, reset_llm_client
from backend.utils.text_utils import mask_api_key
from backend.config import settings

router = APIRouter(prefix="/api/llm", tags=["LLM配置"])

# .env 文件路径
_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")


def _update_env_file(key: str, value: str):
    """更新 .env 文件中的配置项"""
    if not os.path.exists(_ENV_FILE):
        return
    with open(_ENV_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    # 匹配 key=xxx 的行，保留注释
    pattern = rf"^{key}\s*=.*$"
    replacement = f"{key}={value}"
    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        content += f"\n{replacement}"
    with open(_ENV_FILE, "w", encoding="utf-8") as f:
        f.write(content)


class LLMConfigOut(BaseModel):
    base_url: str = ""
    api_key: str = ""  # 脱敏后的 Key
    model: str = ""
    models: dict = {}  # 各文档类型专用模型
    global_requirements: str = ""


class LLMConfigUpdate(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    models: dict | None = None
    global_requirements: str | None = None


@router.get("/config", response_model=LLMConfigOut)
async def get_config(db: AsyncSession = Depends(get_db)):
    """获取 LLM 配置（API Key 脱敏）"""
    global_req = ""
    result = await db.execute(
        select(GlobalConfig).where(GlobalConfig.key == "global_requirements")
    )
    row = result.scalar_one_or_none()
    if row:
        global_req = row.value

    return LLMConfigOut(
        base_url=settings.llm_base_url,
        api_key=mask_api_key(settings.llm_api_key),
        model=settings.llm_model,
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
    )


@router.put("/config", response_model=LLMConfigOut)
async def update_config(data: LLMConfigUpdate, db: AsyncSession = Depends(get_db)):
    """更新 LLM 配置（同时持久化到 .env 文件）"""
    if data.base_url is not None:
        settings.llm_base_url = data.base_url
        _update_env_file("LLM_BASE_URL", data.base_url)
    if data.api_key is not None and data.api_key != mask_api_key(settings.llm_api_key):
        settings.llm_api_key = data.api_key
        _update_env_file("LLM_API_KEY", data.api_key)
    if data.model is not None:
        settings.llm_model = data.model
        _update_env_file("LLM_MODEL", data.model)
    if data.models is not None:
        for doc_type, model in data.models.items():
            if model is None:
                continue
            attr = f"llm_model_{doc_type}"
            env_key = f"LLM_MODEL_{doc_type.upper()}"
            if hasattr(settings, attr):
                setattr(settings, attr, model or None)
                _update_env_file(env_key, model)

    # 保存全局写作要求
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
    return await get_config(db)


@router.post("/test")
async def test_connection():
    """测试 LLM 连接"""
    client = get_llm_client()
    return await client.test_connection()