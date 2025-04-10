from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from config import config
import os
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

def get_db_url() -> str:
    """
    يحصل على رابط اتصال قاعدة البيانات الأساسي
    """
    return os.getenv("DATABASE_URL", config.DATABASE_URL)

def is_sqlite_url(url: str) -> bool:
    """
    تحديد ما إذا كان رابط قاعدة البيانات يستخدم SQLite
    """
    return "sqlite" in url.lower()

# تحديد نوع قاعدة البيانات
db_url = get_db_url()
using_sqlite = is_sqlite_url(db_url)

if using_sqlite:
    # إعداد SQLite المتزامن
    logger.info("استخدام SQLite المتزامن")
    
    sync_engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=True if config.ENV == "dev" else False,
    )
    
    SessionLocal = sessionmaker(
        bind=sync_engine,
        class_=Session,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    def get_db():
        """مولد جلسة قاعدة البيانات المتزامنة مع معالجة الأخطاء"""
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"خطأ في الجلسة: {str(e)}", exc_info=True)
            raise
        finally:
            session.close()
    
    # تعريف توافقي للمتغيرات غير المتزامنة
    async_engine = sync_engine
    AsyncSessionLocal = SessionLocal
    
    async def init_db():
        """تهيئة الجداول مع التحقق الشامل"""
        try:
            # إنشاء جميع الجداول
            Base.metadata.create_all(bind=sync_engine)
            
            # التحقق من وجود الجداول الأساسية
            inspector = inspect(sync_engine)
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
    
else:
    # إعداد PostgreSQL غير المتزامن
    logger.info("استخدام PostgreSQL غير المتزامن")
    
    # إضافة asyncpg إذا لم تكن موجودة
    if "postgresql" in db_url and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql", "postgresql+asyncpg", 1)
    
    # إنشاء محرك غير متزامن
    try:
        async_engine = create_async_engine(
            db_url,
            pool_size=20,
            max_overflow=10,
            echo=True if config.ENV == "dev" else False,
            pool_pre_ping=True  # للكشف عن الاتصالات المنقطعة
        )
    except Exception as e:
        logger.critical(f"فشل في إنشاء محرك قاعدة البيانات: {str(e)}")
        raise
    
    # إعداد جلسة العمل غير المتزامنة
    AsyncSessionLocal = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    async def get_db() -> AsyncSession:
        """مولد جلسة قاعدة البيانات غير المتزامنة مع معالجة الأخطاء"""
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

# يجب أيضًا تحديث ملف seed.py ليتوافق مع التغييرات
__all__ = [
    'Base',
    'async_engine',
    'AsyncSessionLocal',
    'get_db',
    'init_db',
    'using_sqlite'  # إضافة متغير جديد لمعرفة نوع قاعدة البيانات
]