"""文件管理 API 路由"""
import os
import uuid
import json
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from backend.database import get_db
from backend.config import settings
from backend.models.file import ManagedFile, FileCategory
from backend.schemas.file import FileOut, FileUpdate, FileList
from backend.services.file_parser import FileParser
from backend.utils.text_utils import sanitize_filename

router = APIRouter(prefix="/api/files", tags=["文件管理"])


@router.get("", response_model=FileList)
async def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str = Query(None, description="reference/generated"),
    search: str = Query(None, description="搜索文件名或标签"),
    file_type: str = Query(None, description="文件类型筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取文件列表"""
    query = select(ManagedFile)

    if category:
        query = query.where(ManagedFile.category == category)
    if file_type:
        query = query.where(ManagedFile.file_type == file_type)
    if search:
        query = query.where(
            or_(
                ManagedFile.original_name.contains(search),
                ManagedFile.tags.contains(search),
                ManagedFile.notes.contains(search),
            )
        )

    # 计数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # 分页
    query = query.order_by(ManagedFile.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    files = result.scalars().all()

    return FileList(
        items=[FileOut.model_validate(f) for f in files],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/upload", response_model=list[FileOut])
async def upload_files(
    files: list[UploadFile] = File(...),
    category: str = "reference",
    tags: str = "",
    notes: str = "",
    db: AsyncSession = Depends(get_db),
):
    """上传文件（支持多文件）"""
    if not files:
        raise HTTPException(status_code=400, detail="请选择要上传的文件")

    results = []
    os.makedirs(settings.upload_dir, exist_ok=True)

    for upload_file in files:
        # 验证文件类型
        ext = upload_file.filename.rsplit(".", 1)[-1].lower() if "." in upload_file.filename else ""
        if ext not in ("docx", "pdf", "txt", "md", "xlsx"):
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

        # 检查大小
        content = await upload_file.read()
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(status_code=400, detail=f"文件过大: {upload_file.filename}")

        # 保存文件
        stored_name = f"{uuid.uuid4().hex}_{sanitize_filename(upload_file.filename)}"
        storage_path = os.path.join(settings.upload_dir, stored_name)
        with open(storage_path, "wb") as f:
            f.write(content)

        # 解析文件内容
        try:
            parsed_content = await FileParser.parse(storage_path, ext)
        except Exception as e:
            parsed_content = f"[解析失败: {str(e)}]"

        # 创建数据库记录
        file_record = ManagedFile(
            filename=stored_name,
            original_name=upload_file.filename,
            file_type=ext,
            category=FileCategory(category),
            file_size=len(content),
            tags=tags,
            notes=notes,
            storage_path=storage_path,
            parsed_content=parsed_content,
        )
        db.add(file_record)
        results.append(file_record)

    await db.commit()
    for r in results:
        await db.refresh(r)

    return [FileOut.model_validate(r) for r in results]


@router.get("/{file_id}", response_model=FileOut)
async def get_file(file_id: str, db: AsyncSession = Depends(get_db)):
    """获取文件详情"""
    file_record = await db.get(ManagedFile, file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileOut.model_validate(file_record)


@router.put("/{file_id}", response_model=FileOut)
async def update_file(file_id: str, data: FileUpdate, db: AsyncSession = Depends(get_db)):
    """更新文件元数据"""
    file_record = await db.get(ManagedFile, file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")

    if data.filename is not None:
        file_record.original_name = data.filename
    if data.tags is not None:
        file_record.tags = data.tags
    if data.notes is not None:
        file_record.notes = data.notes

    await db.commit()
    await db.refresh(file_record)
    return FileOut.model_validate(file_record)


@router.delete("/{file_id}")
async def delete_file(file_id: str, db: AsyncSession = Depends(get_db)):
    """删除文件"""
    file_record = await db.get(ManagedFile, file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 删除物理文件
    if os.path.exists(file_record.storage_path):
        os.remove(file_record.storage_path)

    await db.delete(file_record)
    await db.commit()
    return {"ok": True, "message": "文件已删除"}


@router.post("/batch-delete")
async def batch_delete_files(
    file_ids: list[str],
    db: AsyncSession = Depends(get_db),
):
    """批量删除文件"""
    if not file_ids:
        raise HTTPException(status_code=400, detail="请选择要删除的文件")

    deleted_count = 0
    for file_id in file_ids:
        file_record = await db.get(ManagedFile, file_id)
        if file_record:
            if os.path.exists(file_record.storage_path):
                os.remove(file_record.storage_path)
            await db.delete(file_record)
            deleted_count += 1

    await db.commit()
    return {"ok": True, "message": f"已删除 {deleted_count} 个文件", "deleted_count": deleted_count}


@router.get("/{file_id}/download")
async def download_file(file_id: str, db: AsyncSession = Depends(get_db)):
    """下载文件"""
    file_record = await db.get(ManagedFile, file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")

    if not os.path.exists(file_record.storage_path):
        raise HTTPException(status_code=404, detail="文件不存在于磁盘")

    return FileResponse(
        file_record.storage_path,
        filename=file_record.original_name,
        media_type="application/octet-stream",
    )


@router.get("/{file_id}/content")
async def get_file_content(file_id: str, db: AsyncSession = Depends(get_db)):
    """获取文件解析后的文本内容"""
    file_record = await db.get(ManagedFile, file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="文件不存在")

    return {
        "filename": file_record.original_name,
        "content": file_record.parsed_content,
    }