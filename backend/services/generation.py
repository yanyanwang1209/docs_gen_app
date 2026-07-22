"""逐章节文档生成引擎"""
import json
import asyncio
from typing import Optional, AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config import settings
from backend.models.document import GenerationTask, GlobalConfig
from backend.models.template import DocumentTemplate, ChapterNode
from backend.models.file import ManagedFile
from backend.services.llm_client import get_llm_client, LLMClient
from backend.utils.chapter_tree import flatten_tree, get_node_path, count_chapters
from backend.utils.text_utils import extract_summary


class GenerationEngine:
    """文档生成引擎：逐章节生成"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._progress_queue: asyncio.Queue = asyncio.Queue()
        self._cancelled = False

    @property
    def progress_queue(self) -> asyncio.Queue:
        return self._progress_queue

    def cancel(self):
        self._cancelled = True

    async def run(self, db: AsyncSession) -> str:
        """执行生成任务，返回完整的 Markdown 文档"""
        print(f"[DEBUG] GenerationEngine.run() started for task {self.task_id}")
        task = await db.get(GenerationTask, self.task_id)
        if not task:
            raise ValueError(f"任务不存在: {self.task_id}")

        try:
            task.status = "generating"
            await db.commit()

            # 1. 加载模板章节树（提前加载，确保首次推送就包含章节列表）
            print(f"[DEBUG] 加载模板: template_id={task.template_id}")
            template = await db.get(DocumentTemplate, task.template_id)
            if not template:
                raise ValueError("模板不存在")

            chapters_q = select(ChapterNode).where(
                ChapterNode.template_id == template.id
            ).order_by(ChapterNode.sort_order)
            result = await db.execute(chapters_q)
            all_chapters = result.scalars().all()
            print(f"[DEBUG] 加载到 {len(all_chapters)} 个章节节点")

            chapter_map = {}
            roots = []
            for ch in all_chapters:
                node = {
                    "id": ch.id,
                    "title": ch.title,
                    "level": ch.level,
                    "sort_order": ch.sort_order,
                    "parent_id": ch.parent_id,
                    "title_only": ch.title_only,
                    "content_type": ch.content_type,
                    "content_prompt": ch.content_prompt,
                    "table_config": ch.table_config,
                    "content_blocks": ch.content_blocks,
                    "children": [],
                }
                chapter_map[ch.id] = node

            for ch in all_chapters:
                if ch.parent_id and ch.parent_id in chapter_map:
                    chapter_map[ch.parent_id]["children"].append(chapter_map[ch.id])
                else:
                    roots.append(chapter_map[ch.id])

            flat_queue = flatten_tree(roots)

            # 2. 加载参考文件
            ref_file_ids = json.loads(task.reference_file_ids or "[]")
            ref_contents = await self._load_reference_files(db, ref_file_ids)

            # 3. 全局写作要求
            global_req = task.global_requirements or ""
            global_config = await db.execute(
                select(GlobalConfig).where(GlobalConfig.key == "global_requirements")
            )
            global_config_row = global_config.scalar_one_or_none()
            if global_config_row and not global_req:
                global_req = global_config_row.value

            # 4. LLM 客户端
            llm = get_llm_client(model=settings.get_model_for_doc_type(task.doc_type))

            # 5. 需要生成内容的章节数
            generating_chapters = [ch for ch in flat_queue if not ch["title_only"]]
            total = len(generating_chapters)

            # 章节摘要列表（供前端展示）
            chapter_list = [
                {"id": ch["id"], "title": ch["title"], "title_only": ch["title_only"]}
                for ch in flat_queue
            ]
            print(f"[DEBUG] 章节列表已构建: {len(chapter_list)} 个章节, 需生成 {total} 个")

            # 首次推送进度 — 此时已包含完整的章节列表
            await self._push_progress({
                "task_id": self.task_id,
                "status": "generating",
                "total_chapters": total,
                "completed_chapters": 0,
                "current_chapter_id": None,
                "current_chapter_title": None,
                "message": "正在准备生成...",
                "chapter_list": chapter_list,
                "chapter_results": {},
            })

            # 6. 自定义模板：无章节时，根据写作要求直接生成全文
            chapter_results = {}
            generated_summaries = []
            completed = 0

            if not flat_queue:
                # 自定义文档路径：无章节结构，一次性生成全文
                system_prompt = self._build_system_prompt(task.doc_type, global_req)
                user_prompt = self._build_custom_document_prompt(
                    global_requirements=global_req,
                    ref_contents=ref_contents,
                )

                # 为自定义文档创建虚拟章节
                custom_chapter_id = f"custom_{self.task_id}"
                chapter_list = [{"id": custom_chapter_id, "title": "自定义文档", "title_only": False}]
                total = 1

                # 先标记为 "generating"，让前端显示旋转图标
                chapter_results[custom_chapter_id] = {
                    "status": "generating",
                    "content": "",
                    "retry_count": 0,
                }
                await self._push_progress({
                    "task_id": self.task_id,
                    "status": "generating",
                    "total_chapters": total,
                    "completed_chapters": 0,
                    "current_chapter_id": custom_chapter_id,
                    "current_chapter_title": "自定义文档",
                    "message": "正在生成自定义文档...",
                    "chapter_list": chapter_list,
                    "chapter_results": chapter_results,
                })

                try:
                    content = await self._generate_with_continuation(
                        llm=llm,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        max_tokens=settings.generation_max_tokens,
                    )

                    chapter_results[custom_chapter_id] = {
                        "status": "completed",
                        "content": content,
                        "retry_count": 0,
                    }
                    completed = 1

                    await self._push_progress({
                        "task_id": self.task_id,
                        "status": "generating",
                        "total_chapters": total,
                        "completed_chapters": completed,
                        "current_chapter_id": custom_chapter_id,
                        "current_chapter_title": "自定义文档",
                        "message": "已完成: 自定义文档",
                        "chapter_list": chapter_list,
                        "chapter_results": chapter_results,
                    })

                except Exception as e:
                    chapter_results[custom_chapter_id] = {
                        "status": "failed",
                        "content": "",
                        "retry_count": 0,
                        "error_message": str(e),
                    }

                task.chapter_results = json.dumps(chapter_results, ensure_ascii=False)
                await db.commit()

            else:
                # 7. 逐章节生成
                for i, chapter in enumerate(flat_queue):
                    if self._cancelled:
                        task.status = "failed"
                        task.error_message = "用户取消生成"
                        await db.commit()
                        return ""

                    # 根据章节层级计算 Markdown 标题前缀（level 1 → #, level 2 → ##, ...）
                    heading_marker = "#" * chapter.get("level", 1)

                    if chapter["title_only"]:
                        chapter_results[chapter["id"]] = {
                            "status": "completed",
                            "content": f"{heading_marker} {chapter['title']}\n\n",
                            "retry_count": 0,
                        }
                        continue

                    # 先标记当前章节为 "generating" 状态，让前端立即显示旋转图标
                    chapter_results[chapter["id"]] = {
                        "status": "generating",
                        "content": "",
                        "retry_count": 0,
                    }
                    # 持久化到数据库，确保 HTTP 轮询回退也能看到
                    task.chapter_results = json.dumps(chapter_results, ensure_ascii=False)
                    await db.commit()
                    print(f"[DEBUG] 开始生成章节: {chapter['title']} (id={chapter['id']}), 已完成 {completed}/{total}")
                    await self._push_progress({
                        "task_id": self.task_id,
                        "status": "generating",
                        "total_chapters": total,
                        "completed_chapters": completed,
                        "current_chapter_id": chapter["id"],
                        "current_chapter_title": chapter["title"],
                        "message": f"正在生成: {chapter['title']}",
                        "chapter_list": chapter_list,
                        "chapter_results": chapter_results,
                    })

                    system_prompt = self._build_system_prompt(task.doc_type, global_req)
                    user_prompt = self._build_chapter_prompt(
                        chapter=chapter,
                        ref_contents=ref_contents,
                        generated_summaries=generated_summaries,
                        heading_marker=heading_marker,
                    )

                    try:
                        content = await self._generate_with_continuation(
                            llm=llm,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            max_tokens=settings.generation_max_tokens,
                        )

                        chapter_results[chapter["id"]] = {
                            "status": "completed",
                            "content": content,
                            "retry_count": 0,
                        }
                        generated_summaries.append({
                            "title": chapter["title"],
                            "summary": extract_summary(content, settings.chapter_summary_max_length),
                        })
                        completed += 1
                        print(f"[DEBUG] 章节完成: {chapter['title']}, 内容长度={len(content)}, 已完成 {completed}/{total}")

                        # 每章完成后推送进度，确保进度条能到 100%
                        await self._push_progress({
                            "task_id": self.task_id,
                            "status": "generating",
                            "total_chapters": total,
                            "completed_chapters": completed,
                            "current_chapter_id": chapter["id"],
                            "current_chapter_title": chapter["title"],
                            "message": f"已完成: {chapter['title']}",
                            "chapter_list": chapter_list,
                            "chapter_results": chapter_results,
                        })

                    except Exception as e:
                        import traceback
                        print(f"[ERROR] 章节生成失败: {chapter['title']}, 错误: {e}")
                        traceback.print_exc()
                        chapter_results[chapter["id"]] = {
                            "status": "failed",
                            "content": "",
                            "retry_count": 0,
                            "error_message": str(e),
                        }
                        # 推送失败状态，让前端显示红色图标
                        await self._push_progress({
                            "task_id": self.task_id,
                            "status": "generating",
                            "total_chapters": total,
                            "completed_chapters": completed,
                            "current_chapter_id": chapter["id"],
                            "current_chapter_title": chapter["title"],
                            "message": f"生成失败: {chapter['title']} — {str(e)}",
                            "chapter_list": chapter_list,
                            "chapter_results": chapter_results,
                        })

                    task.chapter_results = json.dumps(chapter_results, ensure_ascii=False)
                    await db.commit()

            # 8. 检查是否所有需生成的章节都失败了
            if not flat_queue:
                # 自定义模板路径：从 chapter_results 中提取内容
                pass
            else:
                generating_chapters = [ch for ch in flat_queue if not ch["title_only"]]
                if generating_chapters:
                    failed_count = sum(
                        1 for ch in generating_chapters
                        if chapter_results.get(ch["id"], {}).get("status") == "failed"
                    )
                    if failed_count == len(generating_chapters):
                        error_msg = f"所有 {len(generating_chapters)} 个章节生成失败"
                        task.status = "failed"
                        task.error_message = error_msg
                        await db.commit()
                        await self._push_progress({
                            "task_id": self.task_id,
                            "status": "failed",
                            "total_chapters": total,
                            "completed_chapters": completed,
                            "message": error_msg,
                            "chapter_list": chapter_list,
                            "chapter_results": chapter_results,
                        })
                        return ""

            # 9. 组装完整 Markdown
            md_content = self._assemble_markdown(flat_queue, chapter_results)
            task.generated_md = md_content
            task.status = "completed"
            await db.commit()

            await self._push_progress({
                "task_id": self.task_id,
                "status": "completed",
                "total_chapters": total,
                "completed_chapters": completed,
                "current_chapter_id": None,
                "current_chapter_title": None,
                "message": "文档生成完成！",
                "chapter_list": chapter_list,
                "chapter_results": chapter_results,
            })

            return md_content

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            await db.commit()
            await self._push_progress({
                "task_id": self.task_id,
                "status": "failed",
                "total_chapters": 0,
                "completed_chapters": 0,
                "message": f"生成失败: {str(e)}",
            })
            raise

    async def retry_chapter(self, chapter_id: str, db: AsyncSession, retry_reason: str = "") -> str:
        """重新生成单个章节"""
        task = await db.get(GenerationTask, self.task_id)
        if not task:
            raise ValueError("任务不存在")

        chapter_results = json.loads(task.chapter_results or "{}")
        if chapter_id not in chapter_results:
            raise ValueError("章节不存在")

        # 累积历史重试原因
        prev_result = chapter_results.get(chapter_id, {})
        prev_retry_reasons = prev_result.get("retry_reasons", [])
        all_retry_reasons = list(prev_retry_reasons)
        if retry_reason:
            all_retry_reasons.append(retry_reason)

        chapter_node = await db.get(ChapterNode, chapter_id)
        if chapter_node:
            chapter_info = {
                "id": chapter_node.id,
                "title": chapter_node.title,
                "level": chapter_node.level,
                "content_type": chapter_node.content_type,
                "content_prompt": chapter_node.content_prompt,
                "table_config": chapter_node.table_config,
                "title_only": chapter_node.title_only,
            }
        else:
            chapter_info = {
                "id": chapter_id,
                "title": chapter_id,
                "level": 1,
                "content_type": "text",
                "content_prompt": "",
                "table_config": "{}",
                "title_only": False,
            }

        heading_marker = "#" * chapter_info.get("level", 1)

        ref_file_ids = json.loads(task.reference_file_ids or "[]")
        ref_contents = await self._load_reference_files(db, ref_file_ids)

        global_req = task.global_requirements or ""
        llm = get_llm_client(model=settings.get_model_for_doc_type(task.doc_type))

        system_prompt = self._build_system_prompt(task.doc_type, global_req)

        # 自定义模板的章节重试：使用自定义文档 prompt 生成器
        if chapter_id.startswith("custom_") and task.doc_type == "custom":
            user_prompt = self._build_custom_document_prompt(
                global_requirements=global_req,
                ref_contents=ref_contents,
            )
            if all_retry_reasons:
                retry_note = f"\n\n⚠️ 请注意：这是第 {len(all_retry_reasons)} 次重新生成，请综合以下所有修改要求进行调整：\n"
                retry_note += "\n".join(f"  {i}. {reason}" for i, reason in enumerate(all_retry_reasons, 1))
                user_prompt = user_prompt.replace(
                    "请直接生成文档的 Markdown 内容",
                    f"请重新生成文档的 Markdown 内容{retry_note}"
                )
        else:
            # 构建上下文摘要（目标章节之前的已完成章节）
            generated_summaries = []
            template = await db.get(DocumentTemplate, task.template_id)
            if template:
                chapters_q = select(ChapterNode).where(
                    ChapterNode.template_id == template.id
                ).order_by(ChapterNode.sort_order)
                result = await db.execute(chapters_q)
                all_chapters = result.scalars().all()
                for ch in all_chapters:
                    if ch.id == chapter_id:
                        break
                    if ch.id in chapter_results:
                        prev_result = chapter_results[ch.id]
                        if prev_result.get("status") == "completed":
                            prev_content = prev_result.get("content", "")
                            if prev_content and not ch.title_only:
                                generated_summaries.append({
                                    "title": ch.title,
                                    "summary": extract_summary(prev_content, settings.chapter_summary_max_length),
                                })

            # 注入用户的重试原因（累积所有历史修改要求）
            if all_retry_reasons:
                chapter_info = dict(chapter_info)
                chapter_info["retry_reasons"] = all_retry_reasons

            user_prompt = self._build_chapter_prompt(
                chapter=chapter_info,
                ref_contents=ref_contents,
                generated_summaries=generated_summaries,
                heading_marker=heading_marker,
            )

        content = await self._generate_with_continuation(
            llm=llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=settings.generation_max_tokens,
        )

        chapter_results[chapter_id] = {
            "status": "completed",
            "content": content,
            "retry_count": (chapter_results.get(chapter_id, {}).get("retry_count", 0) + 1),
            "retry_reasons": all_retry_reasons,
        }

        task.chapter_results = json.dumps(chapter_results, ensure_ascii=False)

        # 重新组装完整 Markdown
        task.generated_md = await self._assemble_markdown_from_results(task, db, chapter_results)

        await db.commit()

        return content

    async def _load_reference_files(self, db: AsyncSession, file_ids: list) -> list[dict]:
        """加载参考文件的解析内容"""
        contents = []
        for file_id in file_ids:
            file_record = await db.get(ManagedFile, file_id)
            if file_record and file_record.parsed_content:
                contents.append({
                    "filename": file_record.original_name,
                    "content": file_record.parsed_content,
                })
        return contents

    def _build_system_prompt(self, doc_type: str, global_requirements: str) -> str:
        """构建系统提示词"""
        from backend.services.template_presets import DOC_TYPE_LABELS
        doc_name = DOC_TYPE_LABELS.get(doc_type, doc_type)

        if doc_type == "custom":
            return f"""你是一位专业的文档撰写专家。你的任务是根据用户提供的写作要求和参考文件内容，撰写一份高质量的文档。

撰写要求：
1. 语言专业、正式、准确，使用中文撰写
2. 内容详细、具体，符合实际项目情况
3. 使用 Markdown 格式输出
4. 表格使用 Markdown 表格格式
5. 如果参考文件中有相关内容，必须引用参考文件中的信息
6. 如果参考文件信息不足，根据专业知识进行合理补充
7. 文档结构合理，层级清晰，每个部分都要有实质性内容
8. 严格按照用户的写作要求来组织文档结构和内容

{global_requirements}"""

        return f"""你是一位专业的软件文档撰写专家。你的任务是根据参考文件内容，生成一份符合国家标准的{doc_name}。

撰写要求：
1. 语言专业、正式、准确，使用中文撰写
2. 内容详细、具体，符合实际项目情况
3. 使用 Markdown 格式输出
4. 表格使用 Markdown 表格格式
5. 如果参考文件中有相关内容，必须引用参考文件中的信息
6. 如果参考文件信息不足，根据专业知识进行合理补充
7. 每个章节都要有实质性内容，不能空洞

{global_requirements}"""

    def _build_custom_document_prompt(
            self,
            global_requirements: str,
            ref_contents: list,
    ) -> str:
        """构建自定义文档的生成提示词（无章节结构，根据写作要求全文生成）"""
        parts = []

        if global_requirements.strip():
            parts.append("请根据以下写作要求生成一份完整的文档：")
            parts.append(global_requirements)
        else:
            parts.append("请根据参考文件内容，生成一份结构完整、内容详实的文档。")

        base_chars = len("\n".join(parts))
        max_prompt = settings.max_prompt_chars
        remaining = max_prompt - base_chars - 500

        # 参考文件内容
        if ref_contents and remaining > 0:
            per_file_limit = max(500, remaining // len(ref_contents))
            parts.append(f"\n参考文件内容（共{len(ref_contents)}个文件）：")
            for ref in ref_contents:
                content = ref['content']
                file_limit = min(per_file_limit, remaining)
                if len(content) > file_limit:
                    half = file_limit // 2
                    content = content[:half] + "\n...(省略中间部分)...\n" + content[-half:]
                parts.append(f"\n--- 文件: {ref['filename']} ---")
                parts.append(content)
                remaining -= len(content)

        parts.append("\n请直接生成文档的 Markdown 内容，确保结构清晰、内容完整，不要包含其他说明文字。")
        return "\n".join(parts)

    def _build_chapter_prompt(
            self,
            chapter: dict,
            ref_contents: list,
            generated_summaries: list,
            heading_marker: str = "##",
    ) -> str:
        """构建单个章节的生成提示词（控制总长度，防止请求体过大）"""
        parts = []
        parts.append(f"请生成以下章节的内容：")
        parts.append(f"{heading_marker} {chapter['title']}")
        parts.append(f"内容类型: {chapter.get('content_type', 'text')}")
        if chapter.get('content_prompt'):
            parts.append(f"内容要求: {chapter['content_prompt']}")
        if chapter.get('retry_reasons'):
            parts.append(f"\n⚠️ 请注意：这是第 {len(chapter['retry_reasons'])} 次重新生成，请综合以下所有修改要求进行调整：")
            for i, reason in enumerate(chapter['retry_reasons'], 1):
                parts.append(f"  {i}. {reason}")
            parts.append(f"请根据以上所有要求重新生成该章节内容，特别注意改进所有指出的问题。")
        table_config = chapter.get('table_config', '{}')
        if isinstance(table_config, str):
            try:
                table_config = json.loads(table_config)
            except json.JSONDecodeError:
                table_config = {}
        content_type = chapter.get('content_type', 'text')
        if content_type in ('table', 'mixed') and table_config and (table_config.get("rows") or table_config.get("cols")):
            rows = table_config.get("rows", 3)
            cols = table_config.get("cols", 3)
            fixed_cells = table_config.get("fixed_cells", [])
            header_text = table_config.get("header", "")

            # 构建固定单元格查找表
            fixed_map = {}
            for cell in fixed_cells:
                fixed_map[(cell["row"], cell["col"])] = cell["value"]

            # 构建表头
            header_cells = []
            for c in range(cols):
                header_cells.append(fixed_map.get((0, c), ""))
            header_line = f"| {' | '.join(header_cells)} |"
            separator = f"| {' | '.join(['---'] * cols)} |"

            # 整理固定单元格（按行分组，排除表头行）
            fixed_by_row = {}
            for cell in fixed_cells:
                r = cell["row"]
                if r == 0:
                    continue  # 表头已处理
                if r not in fixed_by_row:
                    fixed_by_row[r] = {}
                fixed_by_row[r][cell["col"]] = cell["value"]

            # 构建一个预填了固定值的表格骨架，让 LLM 一目了然地看到每行每列的对应关系
            def _build_table_skeleton():
                """构建部分预填的表格骨架，固定值直接填入，空单元格留空"""
                skeleton_lines = [header_line, separator]
                for r in range(1, rows):
                    row_cells = []
                    for c in range(cols):
                        val = fixed_by_row.get(r, {}).get(c)
                        if val is not None:
                            row_cells.append(val)
                        else:
                            row_cells.append("")
                    skeleton_lines.append(f"| {' | '.join(row_cells)} |")
                return "\n".join(skeleton_lines)

            table_skeleton = _build_table_skeleton()

            # 检测 content_prompt 中是否包含子章节意图
            content_prompt = chapter.get('content_prompt', '')
            sub_chapter_keywords = ["章节", "子章节", "每个功能点", "每个模块", "分别", "逐一", "按功能", "一个功能点建一个"]
            has_sub_chapter_intent = content_prompt and any(
                kw in content_prompt for kw in sub_chapter_keywords
            )

            if content_type == "table":
                if has_sub_chapter_intent:
                    # 允许生成子章节标题 + 表格
                    parts.append(f"\n本章节需要按功能点组织内容，每个功能点作为一个子章节，子章节标题格式为 ### 2.X 功能点名称，每个子章节下包含一个测试用例表格。")
                    if header_text:
                        parts.append(f"表格标题：{header_text}")
                    parts.append(f"\n表格表头格式（必须严格一致，不可修改列名和顺序，不可增删列）：")
                    parts.append(header_line)
                    parts.append(separator)
                    parts.append(f"\n每行数据 {cols} 列，列含义依次为：{'、'.join(header_cells) if header_cells else '自行理解'}。")
                    parts.append(f"\n以下表格骨架中，已填好的值必须保持不变，空单元格请用实际数据填充：")
                    parts.append(table_skeleton)
                    parts.append(f"\n请根据以上骨架生成子章节和完整表格，确保每个固定值出现在正确的行和列中，"
                                 f"注意：表格骨架中留空的单元格也需要填入实际内容，不要留空。")
                else:
                    parts.append(f"\n⚠️ 本章节为纯表格内容，请先输出章节标题 {heading_marker} {chapter['title']}，然后输出表格，不要添加任何文字说明。")
                    if header_text:
                        parts.append(f"表格标题：{header_text}")
                    parts.append(f"\n表头格式（必须严格一致，不可修改列名和顺序，不可增删列）：")
                    parts.append(header_line)
                    parts.append(separator)
                    parts.append(f"\n每行数据 {cols} 列，列含义依次为：{'、'.join(header_cells)}。")
                    if fixed_by_row:
                        # 有固定值时也用表格骨架，比文字描述更直观
                        parts.append(f"\n以下表格骨架中，已填好的值必须保持不变，空单元格请用实际数据填充：")
                        parts.append(table_skeleton)
                        parts.append(f"\n请确保每个固定值出现在正确的行和列中。")
                    parts.append(f"\n请生成至少 {rows} 行数据（含表头），不够可根据专业知识补充。")
            else:  # mixed
                parts.append(f"\n本章节需包含一个表格，请按以下表头格式生成：")
                if header_text:
                    parts.append(f"表格标题：{header_text}")
                parts.append(f"\n表头：")
                parts.append(header_line)
                parts.append(separator)
                parts.append(f"\n每行数据 {cols} 列，列含义依次为：{'、'.join(header_cells)}。")
                if fixed_by_row:
                    parts.append(f"\n以下表格骨架中，已填好的值必须保持不变，空单元格请用实际数据填充：")
                    parts.append(table_skeleton)
                    parts.append(f"\n请确保每个固定值出现在正确的行和列中。")
                parts.append(f"\n请先生成必要的文字说明，再插入表格，表格至少 {rows} 行（含表头）。")
        elif content_type == "text" and chapter.get('content_prompt'):
            # 纯文字章节：明确要求不要使用表格
            parts.append(f"\n请以纯文字段落形式撰写，不要使用表格。")
        # 计算已使用的字符数（基础部分 + 系统提示词预留）
        base_chars = len("\n".join(parts))
        max_prompt = settings.max_prompt_chars
        remaining = max_prompt - base_chars - 500  # 预留 500 给系统提示词和边界
        # === 参考文件内容（动态分配空间） ===
        if ref_contents and remaining > 0:
            # 先计算每个文件能分到的配额
            per_file_limit = max(500, remaining // len(ref_contents))
            parts.append(f"\n参考文件内容（共{len(ref_contents)}个文件）：")
            for ref in ref_contents:
                content = ref['content']
                file_limit = min(per_file_limit, remaining)
                if len(content) > file_limit:
                    # 截取开头和结尾
                    half = file_limit // 2
                    content = content[:half] + "\n...(省略中间部分)...\n" + content[-half:]
                parts.append(f"\n--- 文件: {ref['filename']} ---")
                parts.append(content)
                remaining -= len(content)
        # === 前面章节摘要（只保留最近 N 轮） ===
        # 摘要最多保留 3 条，且总字符数不超过剩余空间的一半
        if generated_summaries and remaining > 200:
            summary_limit = max(200, remaining // 2)
            parts.append(f"\n前面已生成章节的摘要：")
            summary_chars = 0
            for s in reversed(generated_summaries[-3:]):  # 最近 3 章
                line = f"\n## {s['title']}\n{s['summary']}"
                if summary_chars + len(line) > summary_limit:
                    break
                parts.append(f"\n## {s['title']}")
                parts.append(s['summary'])
                summary_chars += len(line)
        parts.append(f"\n请直接生成该章节的 Markdown 内容（以 {heading_marker} 开头），不要包含章节标题外的其他说明。")
        return "\n".join(parts)

    def _assemble_markdown(self, flat_queue: list, chapter_results: dict) -> str:
        """组装完整的 Markdown 文档"""
        lines = []
        for chapter in flat_queue:
            result = chapter_results.get(chapter["id"], {})
            content = result.get("content", "")
            if content:
                lines.append(content.strip())
                lines.append("")

        # 自定义模板：flat_queue 为空时，从 chapter_results 中提取内容
        if not flat_queue and chapter_results:
            for chapter_id, result in chapter_results.items():
                content = result.get("content", "")
                if content:
                    lines.append(content.strip())
                    lines.append("")

        return "\n".join(lines)

    async def _push_progress(self, data: dict):
        await self._progress_queue.put(data)

    async def _generate_with_continuation(
            self,
            llm: LLMClient,
            system_prompt: str,
            user_prompt: str,
            max_tokens: int,
            max_rounds: int = 10,
    ) -> str:
        """生成内容，如果返回内容量接近上限则自动续写"""
        # 第一轮
        content, usage, finish_reason = await llm.generate_with_usage(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=settings.generation_temperature,
            max_tokens=max_tokens,
        )
        full_content = content
        completion_tokens = (usage or {}).get("completion_tokens", 0)

        print(f"[DEBUG] 续写判断: completion_tokens={completion_tokens}, max_tokens={max_tokens}, "
              f"finish_reason={finish_reason}, content_len={len(content)}")

        # 续写条件：
        # 1. API 明确返回 finish_reason="length" → 一定被截断
        # 2. token 用量 >= 95% → 即使 API 说 stop，也很可能内容没写完
        need_continuation = (
            (finish_reason == "length") or
            (completion_tokens >= max_tokens * 0.95)
        )
        if not need_continuation:
            return full_content

        # 需要续写
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": content},
            {"role": "user", "content": "请继续上面的内容，从断点处接着写，不要重复已写的内容。"},
        ]

        for round_num in range(1, max_rounds):
            content, usage, finish_reason = await llm.generate_messages(
                messages=messages,
                temperature=settings.generation_temperature,
                max_tokens=max_tokens,
            )
            if not content:
                break
            full_content += content

            completion_tokens = (usage or {}).get("completion_tokens", 0)
            print(f"[DEBUG] 续写第{round_num}轮: completion_tokens={completion_tokens}, "
                  f"finish_reason={finish_reason}, content_len={len(content)}")

            need_continuation = (
                (finish_reason == "length") or
                (completion_tokens >= max_tokens * 0.95)
            )
            if not need_continuation:
                break

            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": "请继续上面的内容，从断点处接着写，不要重复已写的内容。",
            })

        return full_content

    async def _assemble_markdown_from_results(self, task, db, chapter_results: dict) -> str:
        """根据章节结果重新组装 Markdown 文档"""
        template = await db.get(DocumentTemplate, task.template_id)
        if not template:
            return ""

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
                "title_only": ch.title_only, "content_type": ch.content_type,
                "content_prompt": ch.content_prompt, "table_config": ch.table_config,
                "content_blocks": ch.content_blocks, "children": [],
            }
            chapter_map[ch.id] = node
        for ch in all_chapters:
            if ch.parent_id and ch.parent_id in chapter_map:
                chapter_map[ch.parent_id]["children"].append(chapter_map[ch.id])
            else:
                roots.append(chapter_map[ch.id])

        flat_queue = flatten_tree(roots)
        return self._assemble_markdown(flat_queue, chapter_results)