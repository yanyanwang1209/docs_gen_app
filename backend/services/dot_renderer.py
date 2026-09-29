"""DOT (Graphviz) 渲染器 — 通过 subprocess 调用 dot 命令将 DOT 源码渲染为 PNG"""
import subprocess
import os
import tempfile
from backend.config import settings


class DotRenderer:
    """将 DOT 源码渲染为 PNG 图像"""

    def __init__(self, dot_command: str | None = None, dpi: int | None = None):
        self.dot_command = dot_command or settings.diagram_dot_command
        self.dpi = dpi or settings.diagram_default_dpi
        self._available: bool | None = None  # 缓存检测结果

    def is_available(self) -> bool:
        """检查 dot 是否可用（结果缓存，仅首次运行 dot -V）"""
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

    def render(self, dot_source: str) -> bytes | None:
        """渲染 DOT 为 PNG 字节。不可用或失败时返回 None。"""
        if not settings.diagram_enabled:
            return None
        if not self.is_available():
            return None

        dot_path = None
        png_path = None
        try:
            # 写入 DOT 临时文件
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".dot", delete=False, encoding="utf-8"
            ) as f:
                dot_path = f.name
                f.write(dot_source)

            png_path = dot_path + ".png"

            # -Nfontname 覆盖节点字体，-Efontname 覆盖边字体
            # 即便 DOT 源码中有 fontname 声明也会被命令行参数覆盖
            result = subprocess.run(
                [self.dot_command, "-Tpng",
                 f"-Nfontname={settings.diagram_font_name}",
                 f"-Efontname={settings.diagram_font_name}",
                 f"-Gdpi={self.dpi}",
                 "-o", png_path, dot_path],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                print(f"[DOT RENDER ERROR] {result.stderr[:500]}")
                return None
            with open(png_path, "rb") as f:
                return f.read()
        except subprocess.TimeoutExpired:
            print("[DOT RENDER ERROR] 渲染超时（30秒）")
            return None
        except Exception as e:
            print(f"[DOT RENDER ERROR] {e}")
            return None
        finally:
            for path in (dot_path, png_path):
                if path:
                    try:
                        os.unlink(path)
                    except OSError:
                        pass


# 模块级单例
_renderer: DotRenderer | None = None


def get_dot_renderer() -> DotRenderer:
    """获取 DotRenderer 单例"""
    global _renderer
    if _renderer is None:
        _renderer = DotRenderer()
    return _renderer