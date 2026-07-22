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
        # 迁移：将已有种子模板标记为 is_preset
        await _migrate_mark_preset_templates(conn)
        # 迁移：添加 owner_id 列（如果不存在）
        await _migrate_add_owner_id(conn)

    # 种子数据：为每个文档类型创建默认模板
    await _seed_default_templates()
    # 种子数据：创建默认 admin 用户
    await _seed_admin_user()


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


async def _migrate_mark_preset_templates(conn):
    """迁移：将已有种子模板的 is_preset 标记为 1（如果 is_preset 列不存在则先添加）"""
    try:
        await conn.exec_driver_sql(
            "ALTER TABLE document_templates ADD COLUMN is_preset BOOLEAN DEFAULT 0"
        )
    except Exception:
        pass  # 列已存在，忽略
    # 将 9 种预设类型的模板标记为预设（仅标记没有 owner_id 的，保护个人模板）
    from backend.services.template_presets import PRESET_TEMPLATES
    for doc_type in PRESET_TEMPLATES:
        await conn.exec_driver_sql(
            f"UPDATE document_templates SET is_preset = 1 WHERE doc_type = '{doc_type}' AND is_preset = 0 AND owner_id IS NULL"
        )
    # 删除旧的 "custom" 预设模板（不再作为预设类型）
    await conn.exec_driver_sql(
        "DELETE FROM document_templates WHERE doc_type = 'custom' AND is_preset = 1"
    )


async def _migrate_add_owner_id(conn):
    """迁移：为现有表添加 owner_id 列"""
    for table in ("managed_files", "generation_tasks", "document_templates"):
        try:
            await conn.exec_driver_sql(
                f"ALTER TABLE {table} ADD COLUMN owner_id VARCHAR(36) REFERENCES users(id)"
            )
        except Exception:
            pass  # 列已存在，忽略


async def _seed_default_templates():
    """检查并创建默认模板（每个文档类型一个预设模板）"""
    from backend.models.template import DocumentTemplate, ChapterNode
    from backend.services.template_presets import PRESET_TEMPLATES

    async with async_session() as db:
        seeded = False
        for doc_type, preset in PRESET_TEMPLATES.items():
            existing = await db.execute(
                select(DocumentTemplate).where(
                    DocumentTemplate.doc_type == doc_type,
                    DocumentTemplate.is_preset == True,
                ).limit(1)
            )
            if existing.scalar():
                continue
            # 创建模板
            template = DocumentTemplate(
                name=preset["name"],
                doc_type=doc_type,
                description=preset["description"],
                is_preset=True,
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


async def _seed_admin_user():
    """创建默认 admin 用户（如果不存在）"""
    import logging
    from backend.models.user import User
    from backend.utils.auth import hash_password

    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none():
            return  # admin 已存在

        admin = User(
            username="admin",
            password_hash=hash_password(settings.admin_default_password),
            is_admin=True,
        )
        db.add(admin)
        await db.commit()
        logging.getLogger(__name__).warning(
            "已创建默认 admin 用户（用户名: admin, 密码: %s），请尽快修改密码！",
            settings.admin_default_password,
        )


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()