"""验收文档生成器 — FastAPI 主入口"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时：初始化数据库、创建存储目录
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.generated_dir, exist_ok=True)
    await init_db()
    yield
    # 关闭时清理


app = FastAPI(
    title="验收文档生成器",
    description="根据参考文件自动生成验收文档，支持 MD 转 Word",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from backend.routers import files, templates, generation, md2word, llm_config

app.include_router(files.router)
app.include_router(templates.router)
app.include_router(generation.router)
app.include_router(md2word.router)
app.include_router(llm_config.router)


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "1.0.0"}


# 开发模式下挂载前端静态文件（生产环境由 Nginx 处理）
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FRONTEND_DIST = os.path.join(_BASE_DIR, "frontend", "dist")
if os.path.exists(_FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=9090, reload=True)