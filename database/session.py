from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import config
import os
import logging

logger = logging.getLogger(__name__)

def get_database_url() -> str:
    """الحصول على رابط قاعدة البيانات مع التحقق من البيئة"""
    db_url = os.getenv("DATABASE_URL", config.DATABASE_URL)
    
    if config.ENV == "prod" and not db_url.startswith("postgresql"):
        raise ValueError("يجب استخدام PostgreSQL في بيئة الإنتاج")
    
    if db_url.startswith("postgresql") and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql", "postgresql+asyncpg", 1)
    
    return db_url

async_engine = create_async_engine(
    get_database_url(),
    pool_size=20,
    max_overflow=10,
    echo=True if config.ENV == "dev" else False
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"خطأ في الجلسة: {str(e)}")
            raise
        finally:
            await session.close()

async def init_db():
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
            inspector = await conn.run_sync(inspect)
            required_tables = ['users', 'downloads', 'user_points', 'claimed_rewards']
            
            missing = [tbl for tbl in required_tables if not inspector.has_table(tbl)]
            if missing:
                raise RuntimeError(f"جداول مفقودة: {', '.join(missing)}")
            
        logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")
    except Exception as e:
        logger.critical(f"فشل التهيئة: {str(e)}")
        raise

__all__ = ['Base', 'async_engine', 'AsyncSessionLocal', 'get_db', 'init_db']