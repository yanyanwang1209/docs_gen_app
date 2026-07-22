"""章节模板模型"""
import uuid
from datetime import datetime
from typing import Optional, Union
from sqlalchemy import String, Integer, DateTime, Text, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class DocumentTemplate(Base):
    """文档模板：包含文档类型、名称和章节树"""
    __tablename__ = "document_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="模板名称")
    doc_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="文档类型: srs/hld/dd/dbd/tp/ts/tc/tr/trep"
    )
    description: Mapped[str] = mapped_column(Text, default="", comment="模板描述")
    is_preset: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为预设模板")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联章节
    chapters: Mapped[list["ChapterNode"]] = relationship(
        "ChapterNode", back_populates="template",
        cascade="all, delete-orphan",
        order_by="ChapterNode.sort_order"
    )


class ChapterNode(Base):
    """章节树节点"""
    __tablename__ = "chapter_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_templates.id"), nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("chapter_nodes.id"), nullable=True, default=None)

    title: Mapped[str] = mapped_column(String(500), nullable=False, comment="章节标题")
    level: Mapped[int] = mapped_column(Integer, default=1, comment="层级深度")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="同级排序")
    title_only: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否仅生成标题")
    content_type: Mapped[str] = mapped_column(
        String(20), default="text",
        comment="内容类型: text/table/mixed"
    )
    content_prompt: Mapped[str] = mapped_column(Text, default="", comment="该章节的内容生成提示")
    table_config: Mapped[str] = mapped_column(Text, default="{}", comment="表格配置 JSON")
    content_blocks: Mapped[str] = mapped_column(Text, default="[]", comment="内容块排列 JSON")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    template: Mapped["DocumentTemplate"] = relationship("DocumentTemplate", back_populates="chapters")
    parent: Mapped[Optional["ChapterNode"]] = relationship(
        "ChapterNode", back_populates="children", remote_side=[id],
        foreign_keys=[parent_id],
    )
    children: Mapped[list["ChapterNode"]] = relationship(
        "ChapterNode", back_populates="parent",
        cascade="all, delete-orphan",
        order_by="ChapterNode.sort_order"
    )