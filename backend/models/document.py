"""文档生成任务模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


class GenerationTask(Base):
    """文档生成任务"""
    __tablename__ = "generation_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="文档类型: srs/hld/dd/dbd/tp/ts/tc/tr/trep"
    )
    output_filename: Mapped[str] = mapped_column(String(255), default="", comment="输出文件名")
    status: Mapped[str] = mapped_column(
        String(20), default="pending",
        comment="状态: pending/generating/completed/failed"
    )
    global_requirements: Mapped[str] = mapped_column(Text, default="", comment="全局写作要求")
    template_id: Mapped[str] = mapped_column(String(36), nullable=True, comment="关联模板ID")
    reference_file_ids: Mapped[str] = mapped_column(Text, default="[]", comment="参考文件ID列表 JSON")
    chapter_results: Mapped[str] = mapped_column(Text, default="{}", comment="各章节生成结果 JSON")
    total_chapters: Mapped[int] = mapped_column(Integer, default=0, comment="章节总数（不含 title_only）")
    generated_md: Mapped[str] = mapped_column(Text, default="", comment="生成的完整 Markdown")
    generated_word_path: Mapped[str] = mapped_column(String(500), default="", comment="生成的 Word 文件路径")
    error_message: Mapped[str] = mapped_column(Text, default="", comment="错误信息")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(),
        comment="最后更新时间"
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def dict_for_list(self) -> dict:
        return {
            "id": self.id,
            "doc_type": self.doc_type,
            "output_filename": self.output_filename,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class GlobalConfig(Base):
    """全局配置：写作要求、LLM 设置等"""
    __tablename__ = "global_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())