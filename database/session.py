from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import config
import logging
import os

logger = logging.getLogger(__name__)

# إعداد محرك قاعدة البيانات غير المتزامن
DATABASE_URL = os.getenv("DATABASE_URL", config.DATABASE_URL).replace(
    "postgresql", "postgresql+asyncpg", 1
)

async_engine = create_async_engine(
    DATABASE_URL,
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

async def get_db() -> AsyncSession:
    """جلسة قاعدة البيانات غير المتزامنة"""
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
    """تهيئة الجداول مع التحقق الشامل"""
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ تم إنشاء الجداول الأساسية")

            # التحقق من وجود الجداول المطلوبة
            inspector = await conn.run_sync(inspect)
            required_tables = [
                'users', 
                'downloads', 
                'user_points', 
                'claimed_rewards'
            ]
            
            missing_tables = [
                table 
                for table in required_tables 
                if not inspector.has_table(table)
            ]
            
            if missing_tables:
                error_msg = f"الجداول الناقصة: {', '.join(missing_tables)}"
                logger.critical(error_msg)
                raise RuntimeError(error_msg)

    except Exception as e:
        logger.critical(f"فشل التهيئة: {str(e)}", exc_info=True)
        raise

__all__ = [
    'Base',
    'async_engine',
    'AsyncSessionLocal',
    'get_db',
    'init_db'
]