"""LLM 客户端抽象层 — 支持 OpenAI 兼容 API"""
import httpx
from typing import Optional, AsyncIterator
from backend.config import settings


class LLMClient:
    """统一的 LLM 调用接口"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
    ) -> str:
        """调用 LLM 生成文本（非流式）"""
        content, _, _ = await self.generate_with_usage(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return content

    async def generate_with_usage(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
    ):
        """调用 LLM 生成文本，返回 (content, usage_dict, finish_reason)"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            finish_reason = data["choices"][0].get("finish_reason", "stop")
            return content, usage, finish_reason

    async def generate_messages(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
    ):
        """多轮对话生成，返回 (content, usage_dict, finish_reason)"""
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            finish_reason = data["choices"][0].get("finish_reason", "stop")
            return content, usage, finish_reason

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
    ) -> AsyncIterator[str]:
        """调用 LLM 生成文本（流式）"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        import json
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def test_connection(self) -> dict:
        """测试 LLM 连接是否正常"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # 尝试列出模型
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers(),
                )
                if response.status_code == 200:
                    return {"ok": True, "message": "连接正常", "models_available": True}
                # 尝试聊天接口
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "Hello"}],
                        "max_tokens": 5,
                    },
                )
                if response.status_code == 200:
                    return {"ok": True, "message": "连接正常", "models_available": False}
                return {"ok": False, "message": f"API 返回错误: {response.status_code}"}
        except httpx.ConnectError:
            return {"ok": False, "message": "无法连接到 LLM 服务，请检查 base_url"}
        except Exception as e:
            return {"ok": False, "message": f"连接测试失败: {str(e)}"}


# 全局 LLM 客户端实例（延迟初始化，默认使用 settings 配置）
_llm_client: Optional[LLMClient] = None


def get_llm_client(
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> LLMClient:
    """获取 LLM 客户端。

    如果提供了 base_url/api_key/model，使用提供的值（per-user 配置）；
    否则使用全局 settings 的默认值。
    """
    global _llm_client
    if base_url is None and api_key is None and model is None:
        # 使用全局默认客户端
        if _llm_client is None:
            _llm_client = LLMClient()
        if model and model != _llm_client.model:
            return LLMClient(model=model)
        return _llm_client
    # 使用自定义配置（per-user 或临时覆盖）
    return LLMClient(base_url=base_url, api_key=api_key, model=model)


async def get_llm_config_for_user(db, user_id: str) -> dict:
    """从数据库读取用户的 LLM 配置，未设置则返回全局默认值"""
    if user_id:
        from backend.models.user import User
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            has_personal = user.llm_api_key or user.llm_base_url or user.llm_model
            if has_personal:
                return {
                    "base_url": user.llm_base_url or settings.llm_base_url,
                    "api_key": user.llm_api_key or settings.llm_api_key,
                    "model": user.llm_model or settings.llm_model,
                }
    return {
        "base_url": settings.llm_base_url,
        "api_key": settings.llm_api_key,
        "model": settings.llm_model,
    }


def reset_llm_client():
    """重置全局 LLM 客户端（配置变更后调用）"""
    global _llm_client
    _llm_client = None