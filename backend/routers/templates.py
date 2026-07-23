"""模板管理 API 路由"""
import json
import logging
import os
import tempfile
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from backend.database import get_db
from backend.models.template import DocumentTemplate, ChapterNode
from backend.models.user import User
from backend.schemas.template import (
    TemplateOut, TemplateCreate, TemplateUpdate, TemplateList, TemplateListItem,
    ChapterNodeOut, ChapterNodeCreate,
)
from backend.services.file_parser import FileParser
from backend.services.llm_client import LLMClient, get_llm_config_for_user
from backend.utils.chapter_tree import auto_number
from backend.config import settings

logger = logging.getLogger(__name__)

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
    request: Request,
    doc_type: str = Query(None, description="按文档类型筛选"),
    is_preset: bool = Query(None, description="按预设/自定义筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取模板列表（预设模板全部可见，自定义模板仅显示自己的）"""
    query = select(DocumentTemplate)
    if doc_type:
        query = query.where(DocumentTemplate.doc_type == doc_type)
    if is_preset is not None:
        query = query.where(DocumentTemplate.is_preset == is_preset)

    user_id = getattr(request.state, "user_id", None)
    if user_id:
        # 预设模板全部可见 + 自己的自定义模板
        query = query.where(
            or_(
                DocumentTemplate.is_preset == True,
                DocumentTemplate.owner_id == user_id,
            )
        )
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
async def create_template(data: TemplateCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """创建模板"""
    user_id = getattr(request.state, "user_id", None)
    template = DocumentTemplate(
        name=data.name,
        doc_type=data.doc_type,
        description=data.description,
        owner_id=user_id,
    )
    db.add(template)
    await db.flush()

    if data.chapters:
        _save_chapter_tree(db, template.id, [c.model_dump() for c in data.chapters])

    await db.commit()
    await db.refresh(template)
    return await _get_template_with_chapters(template.id, db)


@router.post("/extract-word", response_model=TemplateOut)
async def extract_word_toc(
    request: Request,
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

    user_id = getattr(request.state, "user_id", None)
    template = DocumentTemplate(
        name=template_name,
        doc_type=doc_type,
        description=f"从 {file.filename} 提取的目录结构",
        owner_id=user_id,
    )
    db.add(template)
    await db.flush()

    await db.refresh(template)
    return await _get_template_with_chapters(template.id, db)


@router.post("/ai-analyze")
async def ai_analyze_document(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """上传文档，用 AI 分析内容自动生成章节结构"""
    # 1. 校验文件类型
    ext = os.path.splitext(file.filename or "")[1].lower().lstrip(".")
    allowed = {"docx", "pdf", "txt", "md"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"仅支持 {', '.join(allowed)} 文件")

    content_bytes = await file.read()

    # 2. 解析文件内容
    try:
        doc_text = FileParser.parse_from_bytes(content_bytes, ext)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")

    if not doc_text or not doc_text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空，无法分析")

    # 3. 获取用户 LLM 配置
    user_id = getattr(request.state, "user_id", None)
    llm_cfg = await get_llm_config_for_user(db, user_id)
    llm = LLMClient(
        base_url=llm_cfg["base_url"],
        api_key=llm_cfg["api_key"],
        model=llm_cfg["model"],
    )

    # 3.1 快速连接预检，避免 LLM 配置错误时长时间等待
    conn_test = await llm.test_connection()
    if not conn_test.get("ok"):
        raise HTTPException(
            status_code=502,
            detail=f"LLM 连接失败: {conn_test.get('message', '未知错误')}。请检查 LLM 配置（base_url、api_key、model）是否正确。",
        )

    # 4. 截断过长文本（保留前 8000 字符 + 后 2000 字符）
    max_chars = settings.max_prompt_chars
    if len(doc_text) > max_chars:
        half = (max_chars - 2000) // 2
        doc_text = doc_text[:half] + "\n\n...(文档中间部分已省略)...\n\n" + doc_text[-half:]

    # 5. 构建 prompt
    system_prompt = """你是一位专业的文档结构分析师。你的任务是根据文档内容，分析出合理的章节结构。

请返回一个 JSON 数组，每个元素代表一个章节节点，包含以下字段：
- title: 章节标题（字符串）
- level: 层级（1=一级标题, 2=二级标题, 3=三级标题）
- content_type: 内容类型，可选 "text"（纯文字）、"table"（表格）、"mixed"（文字+表格）
- content_prompt: 内容提示语，告诉生成引擎该章节应该写什么内容，要具体、有指导性
- title_only: 是否仅生成标题，默认 false
- children: 子章节数组（可选，结构与父节点相同）

规则：
1. 章节层级最多 3 级
2. 每个章节的 content_prompt 要具体，说明该章节包含什么信息、从文档的哪些部分提取
3. 如果文档中某些部分适合用表格展示（如参数列表、配置项、测试用例），content_type 设为 "table"
4. 章节结构应覆盖文档的主要内容，但不要过度拆分
5. 只返回纯 JSON 数组，不要包含任何 markdown 标记或额外说明"""

    user_prompt = f"""请分析以下文档内容，生成合理的章节结构。

文档内容：
---
{doc_text}
---

请直接返回 JSON 数组，不要包含 ```json``` 等标记。"""

    # 6. 调用 LLM
    try:
        raw = await llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=4096,
            timeout=180,
        )
    except Exception as e:
        logger.error("AI 分析调用失败: %s", str(e))
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {str(e)}")

    # 7. 解析 JSON 响应
    chapters = _parse_ai_chapters(raw)
    if not chapters:
        raise HTTPException(status_code=500, detail="AI 未能生成有效的章节结构，请重试")

    return {"chapters": chapters}


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """获取模板详情（含章节树）"""
    return await _get_template_with_chapters(template_id, db)


@router.put("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: str, data: TemplateUpdate, request: Request, db: AsyncSession = Depends(get_db)
):
    """更新模板。编辑系统模板时自动创建个人副本"""
    template = await db.get(DocumentTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    user_id = getattr(request.state, "user_id", None)

    # 系统模板：创建个人副本，不修改原模板
    if template.is_preset:
        copy_template = DocumentTemplate(
            name=data.name if data.name is not None else template.name + " (个人副本)",
            doc_type=template.doc_type,
            description=data.description if data.description is not None else template.description,
            is_preset=False,
            owner_id=user_id,
        )
        db.add(copy_template)
        await db.flush()

        # 复制原模板的章节
        old_chapters = await db.execute(
            select(ChapterNode).where(ChapterNode.template_id == template.id).order_by(ChapterNode.sort_order)
        )
        old_chapters_list = old_chapters.scalars().all()

        # 构建章节树副本
        chapter_tree = _build_chapter_tree(old_chapters_list)

        # 如果请求中有新章节，使用新章节
        if data.chapters is not None:
            chapter_tree = [c.model_dump() for c in data.chapters]

        _save_chapter_tree(db, copy_template.id, chapter_tree)

        await db.commit()
        await db.refresh(copy_template)
        return await _get_template_with_chapters(copy_template.id, db)

    # 个人模板：直接修改
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
    """删除模板（系统模板不可删除）"""
    template = await db.get(DocumentTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    if template.is_preset:
        raise HTTPException(status_code=403, detail="系统模板不可删除，编辑系统模板会自动创建个人副本")

    await db.delete(template)
    await db.commit()
    return {"ok": True, "message": "模板已删除"}


def _parse_ai_chapters(raw: str) -> list[dict]:
    """解析 LLM 返回的章节 JSON，做基本校验和清洗"""
    # 尝试提取 JSON 数组
    text = raw.strip()
    # 去掉可能的 markdown 代码块标记
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        chapters = json.loads(text)
    except json.JSONDecodeError:
        # 尝试找到第一个 [ 和最后一个 ]
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            try:
                chapters = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                return []
        else:
            return []

    if not isinstance(chapters, list):
        return []

    # 清洗和校验每个章节节点
    def clean_node(node: dict, default_level: int = 1) -> dict | None:
        if not isinstance(node, dict):
            return None
        title = (node.get("title") or "").strip()
        if not title:
            return None

        level = node.get("level", default_level)
        if not isinstance(level, int) or level < 1:
            level = default_level
        level = min(level, 3)

        content_type = node.get("content_type", "text")
        if content_type not in ("text", "table", "mixed"):
            content_type = "text"

        result = {
            "title": title,
            "level": level,
            "title_only": bool(node.get("title_only", False)),
            "content_type": content_type,
            "content_prompt": (node.get("content_prompt") or "").strip(),
            "children": [],
        }

        children = node.get("children", [])
        if isinstance(children, list):
            for child in children:
                cleaned = clean_node(child, min(level + 1, 3))
                if cleaned:
                    result["children"].append(cleaned)

        return result

    cleaned = []
    for node in chapters:
        c = clean_node(node)
        if c:
            cleaned.append(c)

    return cleaned


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