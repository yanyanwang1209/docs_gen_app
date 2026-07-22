"""认证中间件 — 从请求头提取 JWT token，注入当前用户信息"""
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from backend.utils.auth import decode_access_token

logger = logging.getLogger(__name__)

# 不需要认证的 API 路径
PUBLIC_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/register",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT 认证中间件：将解析后的用户信息注入 request.state.user"""

    async def dispatch(self, request: Request, call_next):
        request.state.user = None
        request.state.user_id = None

        # 跳过公开路径
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # 提取 token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = decode_access_token(token)
            if payload:
                request.state.user = payload
                request.state.user_id = payload.get("sub")
            else:
                logger.debug("Invalid or expired token: %s...", token[:20])
        else:
            logger.debug("No Authorization header for: %s", request.url.path)

        return await call_next(request)


def get_current_user_id(request: Request) -> str | None:
    """从请求中获取当前用户 ID（路由中调用）"""
    return getattr(request.state, "user_id", None)


def require_auth(request: Request):
    """要求认证：如果未登录则抛出 401"""
    if not getattr(request.state, "user", None):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="请先登录")