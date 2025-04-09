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
    """تهيئة الجداول مع التحقق من وجودها"""
    try:
        from .models import Base
        Base.metadata.create_all(bind=engine)
        
        inspector = inspect(engine)
        required_tables = ['users', 'user_settings', 'downloads', 'user_points', 'claimed_rewards', 'system_logs']
        
        missing_tables = [table for table in required_tables if not inspector.has_table(table)]
        if missing_tables:
            logger.warning(f"الجداول الناقصة: {missing_tables}")
            
        logger.info("✅ تم تهيئة قاعدة البيانات")
    except Exception as e:
        logger.critical(f"فشل في تهيئة DB: {str(e)}", exc_info=True)
        raise

__all__ = ['get_db',
            'init_db',
              'Base',
                'SessionLocal',
                  'engine']