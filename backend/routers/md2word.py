"""MD 转 Word API 路由"""
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.config import settings
from backend.models.file import ManagedFile, FileCategory
from backend.services.md2word import Md2WordConverter
from backend.utils.text_utils import sanitize_filename

router = APIRouter(prefix="/api/md2word", tags=["MD转Word"])


@router.post("/convert")
async def convert_md_file(
    request: Request,
    file: UploadFile = File(...),
    output_filename: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """上传 MD 文件，转换为 Word 文档"""
    if not file.filename.endswith((".md", ".txt", ".markdown")):
        raise HTTPException(status_code=400, detail="仅支持 .md / .txt 文件")

    content_bytes = await file.read()
    content = None
    for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
        try:
            content = content_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if content is None:
        content = content_bytes.decode("utf-8", errors="ignore")

    user_id = getattr(request.state, "user_id", None)
    return await _convert_and_save(content, output_filename or file.filename, user_id, db)


@router.post("/convert-text")
async def convert_md_text(
    request: Request,
    content: str = Form(""),
    output_filename: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """粘贴 MD 文本，转换为 Word 文档"""
    if not content.strip():
        raise HTTPException(status_code=400, detail="请输入 Markdown 内容")

    filename = output_filename or "converted_document"
    user_id = getattr(request.state, "user_id", None)
    return await _convert_and_save(content, filename, user_id, db)


async def _convert_and_save(content: str, filename: str, user_id: str | None, db: AsyncSession):
    """执行转换并保存文件"""
    converter = Md2WordConverter()
    converter.convert(content)
    word_bytes = converter.save_to_bytes()

    os.makedirs(settings.generated_dir, exist_ok=True)
    base_name = sanitize_filename(filename.rsplit(".", 1)[0])
    word_filename = f"{base_name}.docx"
    word_path = os.path.join(settings.generated_dir, f"{uuid.uuid4().hex}_{word_filename}")

    with open(word_path, "wb") as f:
        f.write(word_bytes)

    # 注册到文件管理表
    managed_file = ManagedFile(
        filename=word_filename,
        original_name=word_filename,
        file_type="docx",
        category=FileCategory.generated,
        file_size=len(word_bytes),
        storage_path=word_path,
        owner_id=user_id,
    )
    db.add(managed_file)
    await db.commit()

    return FileResponse(
        word_path,
        filename=word_filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )