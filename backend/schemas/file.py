"""文件管理 Pydantic schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FileOut(BaseModel):
    id: str
    filename: str
    original_name: str
    file_type: str
    category: str
    file_size: int
    tags: str = ""
    notes: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FileUpdate(BaseModel):
    filename: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None


class FileList(BaseModel):
    items: List[FileOut]
    total: int
    page: int
    page_size: int