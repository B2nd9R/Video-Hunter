import logging
from pathlib import Path
from datetime import datetime
import os
import sys
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler

# إعدادات أساسية للـ Logger
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """
    إنشاء وتكوين كائن Logger مع إعدادات متقدمة
    
    Args:
        name (str, optional): اسم الـ Logger. Defaults to None.
    
    Returns:
        logging.Logger: كائن الـ Logger المكون
    """
    # إنشاء مجلد اللوجات إذا لم يكن موجوداً
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # إنشاء كائن Logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # إعداد Formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    
    # Handler للكتابة في ملف مع تدوير الملفات
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # Handler للعرض في الكونسول
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # إضافة الـ Handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # منع إرسال اللوجات إلى الـ Handlers الأصلية
    logger.propagate = False
    
    return logger

# إنشاء الـ Logger الرئيسي
logger = setup_logger(__name__)

# وظائف مساعدة للـ Logger
def log_system_info() -> None:
    """تسجيل معلومات النظام عند بدء التشغيل"""
    import platform
    system_info = {
        "System": platform.system(),
        "Version": platform.version(),
        "Processor": platform.processor(),
        "Python Version": platform.python_version()
    }
    logger.info("System Information: %s", system_info)

def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    تسجيل الأخطاء مع معلومات السياق
    
    Args:
        error (Exception): كائن الخطأ
        context (dict, optional): معلومات إضافية. Defaults to None.
    """
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {}
    }
    logger.error("Error occurred: %s", error_info, exc_info=True)

def log_database_operation(operation: str, details: Dict[str, Any]) -> None:
    """تسجيل عمليات قاعدة البيانات"""
    logger.info(
        "Database Operation: %s - Details: %s",
        operation,
        details,
        extra={'operation': operation}
    )

# تصدير الـ Logger والوظائف المساعدة
__all__ = [
    'logger',
    'log_system_info',
    'log_error',
    'log_database_operation',
    'setup_logger'
]

# مثال للاستخدام
if __name__ == "__main__":
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    
    try:
        1 / 0
    except Exception as e:
        log_error(e, {"additional": "info"})
    
    log_system_info()
    log_database_operation("INSERT", {"table": "users", "count": 5})