"""从生成的章节内容构建 Word 文档"""
import io
import json
import re
from typing import Optional
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from backend.services.md2word import Md2WordConverter


class WordBuilder:
    """从章节结果构建 Word 文档"""

    @staticmethod
    def build_from_markdown(markdown_text: str, doc_title: str = "", output_path: Optional[str] = None) -> bytes:
        """从 Markdown 构建 Word 文档"""
        converter = Md2WordConverter(doc_title=doc_title)
        converter.convert(markdown_text)
        if output_path:
            converter.save(output_path)
        return converter.save_to_bytes()

    @staticmethod
    def build_from_chapters(
        chapter_results: dict,
        flat_order: list,
        output_path: Optional[str] = None,
    ) -> bytes:
        """从章节生成结果构建 Word 文档"""
        lines = []
        for chapter_id in flat_order:
            result = chapter_results.get(chapter_id, {})
            content = result.get("content", "")
            if content:
                lines.append(content.strip())
                lines.append("")

        md_text = "\n".join(lines)
        return WordBuilder.build_from_markdown(md_text, output_path)