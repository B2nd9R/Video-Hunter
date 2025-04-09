from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from config import config

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

def init_db():
    """تهيئة الجداول في قاعدة البيانات"""
    # تأخير استيراد النماذج إلى داخل الدالة لتجنب الاعتماد الدائري
    from .models import User, UserSettings, Download, UserPoints, ClaimedReward, SystemLog
    Base.metadata.create_all(bind=engine)

# تصدير Base للمستخدم في ملفات أخرى
__all__ = [
    'get_db',
    'init_db',
    'Base',
    'SessionLocal'
]