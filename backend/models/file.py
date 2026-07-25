"""上传/参考文件与生成文件的元数据模型"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Text, Enum as SAEnum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base
import enum


class FileCategory(str, enum.Enum):
    reference = "reference"    # 上传的参考文件
    generated = "generated"    # 系统生成的文档
    converted = "converted"    # MD 转 Word 转换的文档


class ManagedFile(Base):
    __tablename__ = "managed_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="存储文件名")
    original_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    file_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="文件扩展名: docx/pdf/txt/md/xlsx")
    category: Mapped[FileCategory] = mapped_column(
        SAEnum(FileCategory, name="file_category"), nullable=False, default=FileCategory.reference
    )
    file_size: Mapped[int] = mapped_column(Integer, default=0, comment="文件大小（字节）")
    tags: Mapped[str] = mapped_column(Text, default="", comment="标签，逗号分隔")
    notes: Mapped[str] = mapped_column(Text, default="", comment="备注")
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="文件存储路径")
    parsed_content: Mapped[str] = mapped_column(Text, default="", comment="解析后的文本内容缓存")
    owner_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, comment="所有者")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())