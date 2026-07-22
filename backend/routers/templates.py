"""模板管理 API 路由"""
import json
import os
import tempfile
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database import get_db
from backend.models.template import DocumentTemplate, ChapterNode
from backend.schemas.template import (
    TemplateOut, TemplateCreate, TemplateUpdate, TemplateList, TemplateListItem,
    ChapterNodeOut, ChapterNodeCreate,
)
from backend.services.file_parser import FileParser
from backend.utils.chapter_tree import auto_number

router = APIRouter(prefix="/api/templates", tags=["模板管理"])


def _chapter_to_dict(ch: ChapterNode) -> dict:
    """将 ChapterNode 转为字典，解析 JSON 字段"""
    table_config = {}
    try:
        table_config = json.loads(ch.table_config) if isinstance(ch.table_config, str) else (ch.table_config or {})
    except (json.JSONDecodeError, TypeError):
        table_config = {}

    content_blocks = []
    try:
        content_blocks = json.loads(ch.content_blocks) if isinstance(ch.content_blocks, str) else (ch.content_blocks or [])
    except (json.JSONDecodeError, TypeError):
        content_blocks = []

    return {
        "id": ch.id,
        "template_id": ch.template_id,
        "title": ch.title,
        "level": ch.level,
        "sort_order": ch.sort_order,
        "parent_id": ch.parent_id,
        "title_only": ch.title_only,
        "content_type": ch.content_type,
        "content_prompt": ch.content_prompt,
        "table_config": table_config,
        "content_blocks": content_blocks,
        "children": [],
    }


def _build_chapter_tree(chapters: list[ChapterNode]) -> list[dict]:
    """将扁平章节列表构建为树结构"""
    node_map = {}
    roots = []
    for ch in chapters:
        node_map[ch.id] = _chapter_to_dict(ch)

    for ch in chapters:
        if ch.parent_id and ch.parent_id in node_map:
            node_map[ch.parent_id]["children"].append(node_map[ch.id])
        else:
            roots.append(node_map[ch.id])

    return roots


def _save_chapter_tree(
    db: AsyncSession,
    template_id: str,
    chapters: list[dict],
    parent_id: str | None = None,
    sort_start: int = 0,
):
    """递归保存章节树到数据库"""
    for i, ch_data in enumerate(chapters):
        node = ChapterNode(
            id=ch_data.get("id", str(uuid.uuid4())),
            template_id=template_id,
            parent_id=parent_id,
            title=ch_data.get("title", ""),
            level=ch_data.get("level", 1),
            sort_order=sort_start + i,
            title_only=ch_data.get("title_only", False),
            content_type=ch_data.get("content_type", "text"),
            content_prompt=ch_data.get("content_prompt", ""),
            table_config=json.dumps(ch_data.get("table_config") or {}, ensure_ascii=False),
            content_blocks=json.dumps(ch_data.get("content_blocks") or [], ensure_ascii=False),
        )
        db.add(node)

        children = ch_data.get("children", [])
        if children:
            _save_chapter_tree(db, template_id, children, node.id, 0)


@router.get("", response_model=TemplateList)
async def list_templates(
    doc_type: str = Query(None, description="按文档类型筛选"),
    is_preset: bool = Query(None, description="按预设/自定义筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取模板列表"""
    query = select(DocumentTemplate)
    if doc_type:
        query = query.where(DocumentTemplate.doc_type == doc_type)
    if is_preset is not None:
        query = query.where(DocumentTemplate.is_preset == is_preset)
    query = query.order_by(DocumentTemplate.updated_at.desc())

    result = await db.execute(query)
    templates = result.scalars().all()

    items = []
    for t in templates:
        count_q = select(func.count()).select_from(ChapterNode).where(
            ChapterNode.template_id == t.id
        )
        count = (await db.execute(count_q)).scalar()
        items.append(TemplateListItem(
            id=t.id,
            name=t.name,
            doc_type=t.doc_type,
            description=t.description,
            is_preset=t.is_preset,
            chapter_count=count,
            created_at=t.created_at,
        ))

    return TemplateList(items=items, total=len(items))


@router.post("", response_model=TemplateOut)
async def create_template(data: TemplateCreate, db: AsyncSession = Depends(get_db)):
    """创建模板"""
    template = DocumentTemplate(
        name=data.name,
        doc_type=data.doc_type,
        description=data.description,
    )
    db.add(template)
    await db.flush()

    if data.chapters:
        _save_chapter_tree(db, template.id, [c.model_dump() for c in data.chapters])

    await db.commit()
    await db.refresh(template)
    return await _get_template_with_chapters(template.id, db)


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """获取模板详情（含章节树）"""
    return await _get_template_with_chapters(template_id, db)


@router.put("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: str, data: TemplateUpdate, db: AsyncSession = Depends(get_db)
):
    """更新模板"""
    template = await db.get(DocumentTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    if data.name is not None:
        template.name = data.name
    if data.description is not None:
        template.description = data.description

    if data.chapters is not None:
        old_chapters = await db.execute(
            select(ChapterNode).where(ChapterNode.template_id == template.id)
        )
        for ch in old_chapters.scalars().all():
            await db.delete(ch)
        await db.flush()

        _save_chapter_tree(db, template.id, [c.model_dump() for c in data.chapters])

    await db.commit()
    await db.refresh(template)
    return await _get_template_with_chapters(template.id, db)


@router.delete("/{template_id}")
async def delete_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """删除模板（预设模板不可删除）"""
    template = await db.get(DocumentTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    if template.is_preset:
        raise HTTPException(status_code=403, detail="预设模板不可删除，但可以编辑调整")

    await db.delete(template)
    await db.commit()
    return {"ok": True, "message": "模板已删除"}


@router.post("/extract-word", response_model=TemplateOut)
async def extract_word_toc(
    file: UploadFile = File(...),
    template_name: str = Query("提取的模板"),
    doc_type: str = Query("srs"),
    db: AsyncSession = Depends(get_db),
):
    """上传 Word 文档，提取目录结构生成模板"""
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="仅支持 .docx 文件")

    content = await file.read()

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        chapters = FileParser.extract_docx_toc(tmp_path)
    finally:
        os.unlink(tmp_path)

    if not chapters:
        raise HTTPException(status_code=400, detail="未能从文档中提取到目录结构。请确保文档使用了标题样式（Heading 1/2/3）")

    chapters = auto_number(chapters)

    template = DocumentTemplate(
        name=template_name,
        doc_type=doc_type,
        description=f"从 {file.filename} 提取的目录结构",
    )
    db.add(template)
    await db.flush()

    _save_chapter_tree(db, template.id, chapters)

    await db.commit()
    await db.refresh(template)
    return await _get_template_with_chapters(template.id, db)


async def _get_template_with_chapters(template_id: str, db: AsyncSession) -> TemplateOut:
    """获取模板及其章节树"""
    template = await db.get(DocumentTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    chapters_q = await db.execute(
        select(ChapterNode)
        .where(ChapterNode.template_id == template_id)
        .order_by(ChapterNode.sort_order)
    )
    chapters = chapters_q.scalars().all()
    chapter_tree = _build_chapter_tree(chapters)

    return TemplateOut(
        id=template.id,
        name=template.name,
        doc_type=template.doc_type,
        description=template.description,
        is_preset=template.is_preset,
        chapters=chapter_tree,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )