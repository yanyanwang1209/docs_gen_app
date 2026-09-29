"""DOT (Graphviz) 渲染器 — 通过 subprocess 调用 dot 命令将 DOT 源码渲染为 SVG"""
import subprocess
import os
import re
import tempfile
from backend.config import settings


class DotRenderer:
    """将 DOT 源码渲染为 SVG 矢量图"""

    def __init__(self, dot_command: str | None = None, dpi: int | None = None):
        self.dot_command = dot_command or settings.diagram_dot_command
        self.dpi = dpi or settings.diagram_default_dpi
        self._available: bool | None = None

    def is_available(self) -> bool:
        """检查 dot 是否可用（结果缓存）"""
        if self._available is not None:
            return self._available
        try:
            result = subprocess.run(
                [self.dot_command, "-V"],
                capture_output=True, text=True, timeout=5,
            )
            self._available = (result.returncode == 0)
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            self._available = False
        return self._available

    def render(self, dot_source: str) -> str | None:
        """渲染 DOT 为 SVG 字符串。不可用或失败时返回 None。"""
        if not settings.diagram_enabled:
            return None
        if not self.is_available():
            return None

        # 移除 LLM 可能写入的 fontname 声明
        dot_source = re.sub(
            r'\bfontname\s*=\s*"[^"]*"\s*,?\s*',
            '', dot_source, flags=re.IGNORECASE,
        )
        dot_source = re.sub(
            r"\bfontname\s*=\s*'[^']*'\s*,?\s*",
            '', dot_source, flags=re.IGNORECASE,
        )
        dot_source = re.sub(r'\[,\s*', '[', dot_source)

        font = settings.diagram_font_name
        dot_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".dot", delete=False, encoding="utf-8"
            ) as f:
                dot_path = f.name
                f.write(dot_source)

            cmd = [
                self.dot_command, "-Tsvg",
                "-Gfontname=" + font,
                "-Nfontname=" + font,
                "-Efontname=" + font,
                dot_path,
            ]
            result = subprocess.run(
                cmd, capture_output=True, timeout=30,
            )
            if result.returncode != 0:
                err_msg = result.stderr.decode("utf-8", errors="replace")[:500]
                print(f"[DOT RENDER ERROR] {err_msg}")
                return None
            return result.stdout.decode("utf-8")
        except subprocess.TimeoutExpired:
            print("[DOT RENDER ERROR] 渲染超时（30秒）")
            return None
        except Exception as e:
            print(f"[DOT RENDER ERROR] {e}")
            return None
        finally:
            if dot_path:
                try:
                    os.unlink(dot_path)
                except OSError:
                    pass


_renderer: DotRenderer | None = None


def get_dot_renderer() -> DotRenderer:
    """获取 DotRenderer 单例"""
    global _renderer
    if _renderer is None:
        _renderer = DotRenderer()
    return _renderer