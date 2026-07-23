"""文档生成 API 路由（含 WebSocket 进度推送）"""
import json
import os
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database import get_db, async_session
from backend.models.document import GenerationTask
from backend.models.file import ManagedFile, FileCategory
from backend.models.user import User
from backend.schemas.document import (
    GenerationStartRequest, GenerationTaskOut, GenerationTaskListItem, GenerationTaskList,
    RetryChapterRequest,
)
from backend.services.generation import GenerationEngine
from backend.services.word_builder import WordBuilder
from backend.utils.chapter_tree import flatten_tree, get_all_chapter_ids, count_chapters
from backend.config import settings
from backend.models.template import DocumentTemplate, ChapterNode

router = APIRouter(prefix="/api/generation", tags=["文档生成"])

# 存储活跃的生成引擎
_active_engines: dict[str, GenerationEngine] = {}
# 存储后台 Task 引用，防止 GC 回收
_active_tasks: dict[str, asyncio.Task] = {}


async def _get_user_llm_config(db: AsyncSession, user_id: str | None) -> dict:
    """获取用户的 LLM 配置"""
    if not user_id:
        return {}
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        # 只要用户设置了任意一项 LLM 配置，就使用个人配置（未设置的用系统默认值）
        has_personal = user.llm_api_key or user.llm_base_url or user.llm_model
        if has_personal:
            return {
                "base_url": user.llm_base_url or settings.llm_base_url,
                "api_key": user.llm_api_key or settings.llm_api_key,
                "model": user.llm_model or settings.llm_model,
            }
    return {}


def _on_generation_done(task: asyncio.Task):
    """后台任务完成回调：记录异常并清理引用"""
    task_id = task.get_name()
    _active_tasks.pop(task_id, None)
    exc = task.exception()
    if exc:
        logging.error(
            "生成任务 %s 异常退出: %s", task_id, exc,
            exc_info=(type(exc), exc, exc.__traceback__),
        )


@router.post("/start", response_model=GenerationTaskOut)
async def start_generation(data: GenerationStartRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """启动文档生成任务"""
    user_id = getattr(request.state, "user_id", None)

    # 验证模板存在
    template = await db.get(DocumentTemplate, data.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 计算章节总数
    chapters_q = select(ChapterNode).where(
        ChapterNode.template_id == template.id
    ).order_by(ChapterNode.sort_order)
    result = await db.execute(chapters_q)
    all_chapters = result.scalars().all()

    chapter_map = {}
    roots = []
    for ch in all_chapters:
        node = {
            "id": ch.id, "title": ch.title, "level": ch.level,
            "sort_order": ch.sort_order, "parent_id": ch.parent_id,
            "title_only": ch.title_only, "children": [],
        }
        chapter_map[ch.id] = node
    for ch in all_chapters:
        if ch.parent_id and ch.parent_id in chapter_map:
            chapter_map[ch.parent_id]["children"].append(chapter_map[ch.id])
        else:
            roots.append(chapter_map[ch.id])

    total_chapters = count_chapters(roots)
    # 自定义模板无章节时，total_chapters 设为 1（生成一次全文）
    if total_chapters == 0:
        total_chapters = 1

    # 生成默认文件名
    output_filename = data.output_filename
    if not output_filename:
        from backend.services.template_presets import DOC_TYPE_LABELS
        doc_name = DOC_TYPE_LABELS.get(data.doc_type, data.doc_type)
        output_filename = f"{doc_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 创建任务
    task = GenerationTask(
        doc_type=data.doc_type,
        output_filename=output_filename,
        global_requirements=data.global_requirements,
        template_id=data.template_id,
        reference_file_ids=json.dumps(data.reference_file_ids, ensure_ascii=False),
        status="pending",
        total_chapters=total_chapters,
        owner_id=user_id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 异步启动生成（后台任务，使用独立 session，传入 per-user LLM 配置）
    llm_config = await _get_user_llm_config(db, user_id)
    engine = GenerationEngine(task.id, llm_config=llm_config)
    _active_engines[task.id] = engine

    task_obj = asyncio.create_task(_run_generation(engine, task.id), name=task.id)
    _active_tasks[task.id] = task_obj
    task_obj.add_done_callback(_on_generation_done)

    return GenerationTaskOut.model_validate(task)


async def _run_generation(engine: GenerationEngine, task_id: str):
    """后台执行生成任务（使用独立的数据库 session）"""
    import traceback
    try:
        async with async_session() as bg_db:
            await engine.run(bg_db)
    except BaseException as e:
        traceback.print_exc()
        error_msg = str(e)
        logging.error("生成任务 %s 失败: %s", task_id, error_msg)
        # 用全新 session 更新状态，避免原 session 失效导致静默失败
        try:
            async with async_session() as fresh_db:
                task = await fresh_db.get(GenerationTask, task_id)
                if task:
                    task.status = "failed"
                    task.error_message = error_msg
                    await fresh_db.commit()
        except Exception as ex:
            logging.error("无法更新任务 %s 失败状态: %s", task_id, ex)
        # 推送失败事件到进度队列（可能还没有 WebSocket 连接）
        try:
            await engine._push_progress({
                "task_id": task_id,
                "status": "failed",
                "total_chapters": 0,
                "completed_chapters": 0,
                "message": f"生成失败: {error_msg}",
            })
        except Exception:
            pass
    finally:
        # 延迟清理，给 WebSocket 足够时间连接和读取
        await asyncio.sleep(60)
        if task_id in _active_engines:
            del _active_engines[task_id]
        _active_tasks.pop(task_id, None)


@router.websocket("/{task_id}/progress")
async def generation_progress(websocket: WebSocket, task_id: str):
    """WebSocket 端点：推送生成进度"""
    await websocket.accept()

    engine = _active_engines.get(task_id)
    if not engine:
        # 任务可能已完成或失败，查询数据库获取真实状态
        async with async_session() as db:
            task = await db.get(GenerationTask, task_id)
            if task:
                await websocket.send_json({
                    "task_id": task_id,
                    "status": task.status,
                    "message": task.error_message or f"任务状态: {task.status}",
                })
            else:
                await websocket.send_json({
                    "task_id": task_id,
                    "status": "not_found",
                    "message": "任务不存在",
                })
        await websocket.close()
        return

    try:
        while True:
            try:
                progress = await asyncio.wait_for(engine.progress_queue.get(), timeout=30)
                await websocket.send_json(progress)
                if progress.get("status") in ("completed", "failed"):
                    break
            except asyncio.TimeoutError:
                # 发送心跳
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@router.post("/{task_id}/retry-chapter/{chapter_id}")
async def retry_chapter(task_id: str, chapter_id: str, data: RetryChapterRequest = RetryChapterRequest(), db: AsyncSession = Depends(get_db)):
    """重新生成单个章节"""
    engine = GenerationEngine(task_id)
    try:
        content = await engine.retry_chapter(chapter_id, db, retry_reason=data.retry_reason)
        return {"ok": True, "content": content}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{task_id}/preview")
async def preview_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """获取任务的 Markdown 预览内容"""
    task = await db.get(GenerationTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "id": task.id,
        "output_filename": task.output_filename,
        "status": task.status,
        "markdown": task.generated_md or "",
    }


@router.get("/{task_id}")
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """获取任务详情"""
    task = await db.get(GenerationTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 构建章节列表（从模板中获取）
    chapter_list = None
    if task.template_id:
        template = await db.get(DocumentTemplate, task.template_id)
        if template:
            chapters_q = select(ChapterNode).where(
                ChapterNode.template_id == template.id
            ).order_by(ChapterNode.sort_order)
            result = await db.execute(chapters_q)
            all_chapters = result.scalars().all()
            if all_chapters:
                chapter_map = {}
                roots = []
                for ch in all_chapters:
                    node = {
                        "id": ch.id, "title": ch.title, "level": ch.level,
                        "sort_order": ch.sort_order, "parent_id": ch.parent_id,
                        "title_only": ch.title_only, "children": [],
                    }
                    chapter_map[ch.id] = node
                for ch in all_chapters:
                    if ch.parent_id and ch.parent_id in chapter_map:
                        chapter_map[ch.parent_id]["children"].append(chapter_map[ch.id])
                    else:
                        roots.append(chapter_map[ch.id])
                flat_queue = flatten_tree(roots)
                chapter_list = [
                    {"id": ch["id"], "title": ch["title"], "title_only": ch.get("title_only", False)}
                    for ch in flat_queue
                ]

    out = GenerationTaskOut.model_validate(task)
    response = out.model_dump()
    if chapter_list is not None:
        response["chapter_list"] = chapter_list
    return response


@router.get("", response_model=GenerationTaskList)
async def list_tasks(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取历史任务列表（仅显示当前用户的任务）"""
    subquery = select(GenerationTask)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        subquery = subquery.where(GenerationTask.owner_id == user_id)

    count_q = select(func.count()).select_from(subquery.subquery())
    total = (await db.execute(count_q)).scalar()

    query = subquery.order_by(GenerationTask.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return GenerationTaskList(
        items=[GenerationTaskListItem.model_validate(t) for t in tasks],
        total=total,
    )


@router.post("/{task_id}/build-word")
async def build_word(task_id: str, db: AsyncSession = Depends(get_db)):
    """将生成结果构建为 Word 文档并返回下载"""
    task = await db.get(GenerationTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    if not task.generated_md:
        raise HTTPException(status_code=400, detail="没有生成内容")

    # 生成 Word
    os.makedirs(settings.generated_dir, exist_ok=True)

    word_bytes = WordBuilder.build_from_markdown(task.generated_md, doc_title=task.output_filename)

    # 保存 Word 文件
    word_filename = f"{task.output_filename}.docx"
    word_path = os.path.join(settings.generated_dir, f"{task.id}_{word_filename}")
    with open(word_path, "wb") as f:
        f.write(word_bytes)

    task.generated_word_path = word_path

    # 保存到文件管理表（"生成文件"标签页可见）
    existing = await db.execute(
        select(ManagedFile).where(ManagedFile.storage_path == word_path)
    )
    if not existing.scalar_one_or_none():
        managed_file = ManagedFile(
            filename=word_filename,
            original_name=word_filename,
            file_type="docx",
            category=FileCategory.generated,
            file_size=len(word_bytes),
            storage_path=word_path,
            owner_id=task.owner_id,
        )
        db.add(managed_file)

    await db.commit()

    from fastapi.responses import FileResponse
    return FileResponse(
        word_path,
        filename=word_filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.delete("/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """删除生成任务"""
    task = await db.get(GenerationTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 取消正在进行的生成
    if task_id in _active_engines:
        _active_engines[task_id].cancel()
        del _active_engines[task_id]
    if task_id in _active_tasks:
        _active_tasks[task_id].cancel()
        del _active_tasks[task_id]

    await db.delete(task)
    await db.commit()
    return {"ok": True, "message": "任务已删除"}


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """终止正在进行的生成任务"""
    task = await db.get(GenerationTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ("generating", "pending"):
        raise HTTPException(status_code=400, detail="任务不在生成中")

    # 取消引擎
    if task_id in _active_engines:
        _active_engines[task_id].cancel()
        del _active_engines[task_id]
    if task_id in _active_tasks:
        _active_tasks[task_id].cancel()
        del _active_tasks[task_id]

    task.status = "failed"
    task.error_message = "用户取消生成"
    await db.commit()

    return {"ok": True, "message": "任务已终止"}