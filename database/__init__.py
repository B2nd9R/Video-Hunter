from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import Base
from config import config

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
    Base.metadata.create_all(bind=engine)

__all__ = [
    'get_db',
    'init_db',
    'Base',
    'SessionLocal'
]