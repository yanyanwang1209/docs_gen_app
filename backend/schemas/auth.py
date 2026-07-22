"""认证 Schema"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=256)


class AuthResponse(BaseModel):
    ok: bool = True
    token: str = ""
    user_id: str = ""
    username: str = ""
    is_admin: bool = False


class UserInfo(BaseModel):
    user_id: str = ""
    username: str = ""
    is_admin: bool = False
    has_llm_config: bool = False  # 是否已配置个人 LLM


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=256)