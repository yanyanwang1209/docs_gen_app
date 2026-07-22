"""应用配置管理，从 .env 文件加载"""
import os
from pydantic_settings import BaseSettings
from typing import Optional

# 计算 .env 文件的绝对路径（backend 的上级目录）
_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    """应用配置"""
    # LLM 配置
    llm_base_url: str = "http://localhost:8000/v1"
    llm_api_key: str = ""
    llm_model: str = "default-model"

    # 可选：不同文档类型专用模型
    llm_model_srs: Optional[str] = None
    llm_model_hld: Optional[str] = None
    llm_model_dd: Optional[str] = None
    llm_model_dbd: Optional[str] = None
    llm_model_tp: Optional[str] = None
    llm_model_ts: Optional[str] = None
    llm_model_tc: Optional[str] = None
    llm_model_tr: Optional[str] = None
    llm_model_trep: Optional[str] = None
    llm_model_custom: Optional[str] = None

    # 应用配置
    app_secret_key: str = "change-this"
    database_url: str = f"sqlite+aiosqlite:///{_PROJECT_DIR}/storage/docs_gen.db"
    storage_dir: str = os.path.join(_PROJECT_DIR, "storage")
    max_upload_size_mb: int = 50
    cors_origins: str = "*"

    # 生成配置
    generation_temperature: float = 0.7
    generation_max_tokens: int = 4096
    chapter_summary_max_length: int = 500
    max_prompt_chars: int = 12000  # 单次请求 prompt 最大字符数（防止请求体过大）

    model_config = {
        "env_file": _ENV_FILE,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def upload_dir(self) -> str:
        return os.path.join(self.storage_dir, "uploads")

    @property
    def generated_dir(self) -> str:
        return os.path.join(self.storage_dir, "generated")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    def get_model_for_doc_type(self, doc_type: str) -> str:
        """根据文档类型获取对应的模型名称"""
        model_map = {
            "srs": self.llm_model_srs,
            "hld": self.llm_model_hld,
            "dd": self.llm_model_dd,
            "dbd": self.llm_model_dbd,
            "tp": self.llm_model_tp,
            "ts": self.llm_model_ts,
            "tc": self.llm_model_tc,
            "tr": self.llm_model_tr,
            "trep": self.llm_model_trep,
            "custom": self.llm_model_custom,
        }
        return model_map.get(doc_type) or self.llm_model


settings = Settings()