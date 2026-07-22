"""模板管理 Pydantic schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ---------- 表格配置 ----------
class TableColumn(BaseModel):
    name: str = ""
    width: str = "auto"  # 如 "30%", "100px", "auto"


class FixedCell(BaseModel):
    row: int
    col: int
    value: str


class TableConfig(BaseModel):
    rows: int = 3
    cols: int = 3
    columns: Optional[List[TableColumn]] = None  # 保留向后兼容，新模板不再使用
    fixed_cells: List[FixedCell] = []
    header: Optional[str] = None  # 表格说明/标题


# ---------- 内容块 ----------
class ContentBlock(BaseModel):
    type: str = "text"  # "text" | "table"
    order: int = 0
    prompt: str = ""  # 该块的生成提示
    table_config: Optional[TableConfig] = None


# ---------- 章节节点 ----------
class ChapterNodeBase(BaseModel):
    title: str = ""
    level: int = 1
    sort_order: int = 0
    parent_id: Optional[str] = None
    title_only: bool = False
    content_type: str = "text"
    content_prompt: str = ""
    table_config: Optional[TableConfig] = None
    content_blocks: List[ContentBlock] = []


class ChapterNodeCreate(ChapterNodeBase):
    children: List["ChapterNodeCreate"] = []


class ChapterNodeUpdate(BaseModel):
    title: Optional[str] = None
    level: Optional[int] = None
    sort_order: Optional[int] = None
    parent_id: Optional[str] = None
    title_only: Optional[bool] = None
    content_type: Optional[str] = None
    content_prompt: Optional[str] = None
    table_config: Optional[TableConfig] = None
    content_blocks: Optional[List[ContentBlock]] = None


class ChapterNodeOut(ChapterNodeBase):
    id: str = ""
    template_id: str = ""
    children: List["ChapterNodeOut"] = []
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------- 模板 ----------
class TemplateCreate(BaseModel):
    name: str
    doc_type: str
    description: str = ""
    chapters: List[ChapterNodeCreate] = []


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    chapters: Optional[List[ChapterNodeCreate]] = None


class TemplateOut(BaseModel):
    id: str
    name: str
    doc_type: str
    description: str
    is_preset: bool
    chapters: List[ChapterNodeOut] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TemplateListItem(BaseModel):
    id: str
    name: str
    doc_type: str
    description: str
    is_preset: bool
    chapter_count: int = 0
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TemplateList(BaseModel):
    items: List[TemplateListItem]
    total: int