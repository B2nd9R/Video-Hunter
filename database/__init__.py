from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from config import config
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

engine = create_engine(config.DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def init_db():
    """تهيئة الجداول في قاعدة البيانات"""
    try:
        from .models import Base
        logger.info("جارٍ إنشاء الجداول...")
        
        # إنشاء جميع الجداول
        Base.metadata.create_all(bind=engine)
        
        # التحقق من وجود الجداول الأساسية
        required_tables = ['users', 'claimed_rewards', 'user_points', 'downloads']
        inspector = inspect(engine)
        
        for table in required_tables:
            if not inspector.has_table(table):
                logger.error(f"فشل في إنشاء جدول: {table}")
                raise RuntimeError(f"الجدول {table} لم يتم إنشاؤه")

        logger.info("✅ تم إنشاء جميع الجداول بنجاح")
    except Exception as e:
        logger.critical(f"فشل في تهيئة قاعدة البيانات: {str(e)}", exc_info=True)
        raise

__all__ = ['get_db',
            'init_db',
              'Base',
                'SessionLocal',
                  'engine']