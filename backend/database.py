"""SQLite 数据库连接管理，使用 SQLAlchemy 异步 + WAL 模式"""
import json
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select
from backend.config import settings


engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """初始化数据库：创建表 + 开启 WAL 模式 + 种子数据"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 开启 WAL 模式以支持并发读
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        # 迁移：添加 total_chapters 列（如果不存在）
        await _migrate_add_total_chapters(conn)
        # 迁移：添加 updated_at 列（如果不存在）
        await _migrate_add_updated_at(conn)

    # 种子数据：为每个文档类型创建默认模板
    await _seed_default_templates()


async def _migrate_add_total_chapters(conn):
    """迁移：为 generation_tasks 表添加 total_chapters 列"""
    try:
        await conn.exec_driver_sql(
            "ALTER TABLE generation_tasks ADD COLUMN total_chapters INTEGER DEFAULT 0"
        )
    except Exception:
        pass  # 列已存在，忽略


async def _migrate_add_updated_at(conn):
    """迁移：为 generation_tasks 表添加 updated_at 列"""
    try:
        await conn.exec_driver_sql(
            "ALTER TABLE generation_tasks ADD COLUMN updated_at DATETIME"
        )
    except Exception:
        pass  # 列已存在，忽略


async def _seed_default_templates():
    """检查并创建默认模板（每个文档类型一个）"""
    from backend.models.template import DocumentTemplate, ChapterNode
    from backend.services.template_presets import PRESET_TEMPLATES

    async with async_session() as db:
        seeded = False
        for doc_type, preset in PRESET_TEMPLATES.items():
            existing = await db.execute(
                select(DocumentTemplate).where(DocumentTemplate.doc_type == doc_type).limit(1)
            )
            if existing.scalar():
                continue
            # 创建模板
            template = DocumentTemplate(
                name=preset["name"],
                doc_type=doc_type,
                description=preset["description"],
            )
            db.add(template)
            await db.flush()
            # 递归创建章节
            _save_chapters(db, template.id, preset["chapters"])
            seeded = True

        if seeded:
            await db.commit()


def _save_chapters(db, template_id: str, chapters: list, parent_id: str | None = None):
    """递归保存章节树到数据库"""
    from backend.models.template import ChapterNode
    for i, ch_data in enumerate(chapters):
        node = ChapterNode(
            id=ch_data.get("id", str(uuid.uuid4())),
            template_id=template_id,
            parent_id=parent_id,
            title=ch_data.get("title", ""),
            level=ch_data.get("level", 1),
            sort_order=i,
            title_only=ch_data.get("title_only", False),
            content_type=ch_data.get("content_type", "text"),
            content_prompt=ch_data.get("content_prompt", ""),
            table_config=json.dumps(ch_data.get("table_config") or {}, ensure_ascii=False),
            content_blocks=json.dumps(ch_data.get("content_blocks") or [], ensure_ascii=False),
        )
        db.add(node)
        children = ch_data.get("children", [])
        if children:
            _save_chapters(db, template_id, children, node.id)


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()