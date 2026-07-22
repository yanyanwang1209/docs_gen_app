"""文本处理工具"""
import re


def truncate_text(text: str, max_length: int = 500) -> str:
    """截断文本，保留前后部分"""
    if len(text) <= max_length:
        return text
    half = max_length // 2
    return text[:half] + f"\n\n... (省略 {len(text) - max_length} 字符) ...\n\n" + text[-half:]


def extract_summary(text: str, max_length: int = 300) -> str:
    """提取文本摘要（取开头部分）"""
    text = text.strip()
    if len(text) <= max_length:
        return text
    # 尽量在句子边界截断
    truncated = text[:max_length]
    last_period = max(truncated.rfind("。"), truncated.rfind("."), truncated.rfind("\n"))
    if last_period > max_length // 2:
        return text[:last_period + 1] + "\n\n(已省略后续内容...)"
    return truncated + "...\n\n(已省略后续内容...)"


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    # 移除 Windows 文件名非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 移除首尾空格和点
    filename = filename.strip().strip('.')
    return filename or "untitled"


def build_md_from_chapters(chapter_results: dict, flat_order: list) -> str:
    """从章节生成结果组装 Markdown 文档"""
    lines = []
    for chapter_id in flat_order:
        result = chapter_results.get(chapter_id, {})
        content = result.get("content", "")
        if content:
            lines.append(content.strip())
            lines.append("")
    return "\n".join(lines)


def mask_api_key(key: str) -> str:
    """脱敏 API Key"""
    if not key or len(key) <= 8:
        return "****"
    return key[:4] + "*" * (len(key) - 8) + key[-4:]