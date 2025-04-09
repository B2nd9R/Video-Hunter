from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from config import config
import logging

logger = logging.getLogger(__name__)

# تعريف Base هنا لتجنب الاستيراد الدائري
Base = declarative_base()

# تهيئة محرك قاعدة البيانات
engine = create_engine(config.DATABASE_URL)

# إنشاء جلسة مخصصة
SessionLocal = scoped_session(sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
))

# تعريف الدوال الأساسية
def get_db():
    """الحصول على جلسة قاعدة البيانات"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def init_db():
    """تهيئة الجداول في قاعدة البيانات مع معالجة الأخطاء"""
    try:
        # تأخير استيراد النماذج إلى داخل الدالة لتجنب الاعتماد الدائري
        from .models import User, UserSettings, Download, UserPoints, ClaimedReward, SystemLog
        
        logger.info("جارٍ إنشاء الجداول...")
        Base.metadata.create_all(bind=engine)
        
        # التحقق من وجود كل جدول
        with engine.connect() as conn:
            for table in Base.metadata.tables.values():
                if not conn.dialect.has_table(conn, table.name):
                    logger.warning(f"الجدول {table.name} غير موجود!")
        
        logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")
    except Exception as e:
        logger.critical(f"فشل في تهيئة قاعدة البيانات: {str(e)}")
        raise

# تصدير Base للمستخدم في ملفات أخرى
__all__ = [
    'get_db',
    'init_db',
    'Base',
    'SessionLocal',
    'engine'
]