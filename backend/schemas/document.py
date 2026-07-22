"""文档生成 Pydantic schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class GenerationStartRequest(BaseModel):
    doc_type: str = Field(..., description="文档类型")
    output_filename: str = Field(default="", description="输出文件名")
    global_requirements: str = Field(default="", description="全局写作要求")
    template_id: str = Field(..., description="模板ID")
    reference_file_ids: List[str] = Field(default=[], description="参考文件ID列表")


class ChapterResult(BaseModel):
    chapter_id: str
    status: str = "pending"  # pending / generating / completed / failed
    content: str = ""
    retry_count: int = 0
    error_message: str = ""


class GenerationProgress(BaseModel):
    task_id: str
    status: str
    total_chapters: int
    completed_chapters: int
    current_chapter_id: Optional[str] = None
    current_chapter_title: Optional[str] = None
    message: str = ""


class RetryChapterRequest(BaseModel):
    retry_reason: str = ""


class GenerationTaskOut(BaseModel):
    id: str
    doc_type: str
    output_filename: str
    status: str
    global_requirements: str = ""
    template_id: Optional[str] = None
    reference_file_ids: str = "[]"
    chapter_results: str = "{}"
    total_chapters: int = 0
    generated_md: str = ""
    error_message: str = ""
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class GenerationTaskListItem(BaseModel):
    id: str
    doc_type: str
    output_filename: str
    status: str
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class GenerationTaskList(BaseModel):
    items: List[GenerationTaskListItem]
    total: int