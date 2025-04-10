from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import config
import os
import logging

logger = logging.getLogger(__name__)

def get_async_db_url() -> str:
    """
    يحصل على رابط اتصال قاعدة البيانات مع التحقق من:
    - منع استخدام SQLite في الإنتاج
    - إضافة asyncpg إذا لم تكن موجودة
    """
    db_url = os.getenv("DATABASE_URL", config.DATABASE_URL)
    
    # التحقق من أن الإنتاج يستخدم PostgreSQL
    if config.ENV == "prod" and "postgresql" not in db_url:
        logger.critical("محاولة استخدام SQLite في بيئة الإنتاج!")
        raise ValueError("يجب استخدام PostgreSQL في بيئة الإنتاج")
    
    # إضافة asyncpg إذا لم تكن موجودة
    if "postgresql" in db_url and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql", "postgresql+asyncpg", 1)
    
    return db_url

# إنشاء محرك غير متزامن مع إدارة الأخطاء
try:
    async_engine = create_async_engine(
        get_async_db_url(),
        pool_size=20,
        max_overflow=10,
        echo=True if config.ENV == "dev" else False,
        pool_pre_ping=True  # للكشف عن الاتصالات المنقطعة
    )
except Exception as e:
    logger.critical(f"فشل في إنشاء محرك قاعدة البيانات: {str(e)}")
    raise

# إعداد جلسة العمل
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    """مولد جلسة قاعدة البيانات مع معالجة الأخطاء"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"خطأ في الجلسة: {str(e)}", exc_info=True)
            raise
        finally:
            await session.close()

async def init_db():
    """تهيئة الجداول مع التحقق الشامل"""
    try:
        async with async_engine.begin() as conn:
            # إنشاء جميع الجداول
            await conn.run_sync(Base.metadata.create_all)
            
            # التحقق من وجود الجداول الأساسية
            inspector = await conn.run_sync(inspect)
            required_tables = ['users', 'downloads', 'user_points', 'claimed_rewards']
            
            missing_tables = [
                table for table in required_tables 
                if not inspector.has_table(table)
            ]
            
            if missing_tables:
                error_msg = f"جداول مفقودة: {', '.join(missing_tables)}"
                logger.critical(error_msg)
                raise RuntimeError(error_msg)
            
        logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")
    except Exception as e:
        logger.critical(f"فشل في تهيئة الجداول: {str(e)}", exc_info=True)
        raise

__all__ = [
    'Base',
    'async_engine',
    'AsyncSessionLocal',
    'get_db',
    'init_db'
]