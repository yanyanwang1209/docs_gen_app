"""用户模型 — 包含个人 LLM 配置"""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="用户名")
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False, comment="密码哈希")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否管理员")

    # 个人 LLM 配置（为 NULL 时使用系统默认值）
    llm_base_url: Mapped[str] = mapped_column(String(500), nullable=True, comment="个人 LLM API 地址")
    llm_api_key: Mapped[str] = mapped_column(String(500), nullable=True, comment="个人 LLM API Key")
    llm_model: Mapped[str] = mapped_column(String(200), nullable=True, comment="个人 LLM 模型")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())