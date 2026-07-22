"""日志配置"""
import logging
import logging.handlers
import os
import sys

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "logs")


def setup_logging(level: str = "INFO") -> logging.Logger:
    """初始化日志系统，返回 root logger"""
    os.makedirs(LOG_DIR, exist_ok=True)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-5s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 控制台
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    # 文件轮转（10MB * 5）
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # 错误日志单独文件
    err_handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, "error.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(fmt)
    root.addHandler(err_handler)

    return root


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)