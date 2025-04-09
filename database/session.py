import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Union, Dict, Any
from datetime import datetime
import logging
from config import config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """مدير قاعدة البيانات مع إدارة الاتصال الآمن"""
    
    def __init__(self):
        self.db_path = config.BASE_DIR / "database" / "video_bot.db"
        self._ensure_db_directory()
        
    def _ensure_db_directory(self):
        """تأكد من وجود مجلد قاعدة البيانات"""
        self.db_path.parent.mkdir(exist_ok=True)
    
    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """الحصول على اتصال آمن بقاعدة البيانات"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            logger.error(f"خطأ في قاعدة البيانات: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def initialize_database(self):
        """تهيئة قاعدة البيانات وإنشاء الجداول"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # جدول المستخدمين
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                join_date TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                total_downloads INTEGER DEFAULT 0,
                CONSTRAINT unique_user UNIQUE (user_id)
            )
            ''')
            
            # جدول التحميلات
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                platform TEXT NOT NULL,
                download_date TEXT NOT NULL,
                file_size REAL,
                status TEXT DEFAULT 'completed',
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CONSTRAINT unique_download UNIQUE (user_id, url, download_date)
            )
            ''')
            
            # جدول النقاط
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_points (
                user_id INTEGER PRIMARY KEY,
                points INTEGER DEFAULT 0 CHECK(points >= 0),
                last_daily_bonus DATE,
                streak_count INTEGER DEFAULT 0 CHECK(streak_count >= 0),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            ''')
            
            conn.commit()
            logger.info("تم تهيئة قاعدة البيانات بنجاح")

    async def register_user(self, user_data: Dict[str, Any]):
        """تسجيل مستخدم جديد"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, join_date, last_activity)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_data['id'],
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name'),
                now,
                now
            ))
            
            conn.commit()
            logger.info(f"تم تسجيل/تحديث المستخدم: {user_data['id']}")

# تهيئة مدير قاعدة البيانات
db_manager = DatabaseManager()

# وظائف مساعدة للاستيراد المباشر
@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """الحصول على اتصال بقاعدة البيانات (للاستخدام المباشر)"""
    with db_manager.get_connection() as conn:
        yield conn

async def init_db():
    """تهيئة قاعدة البيانات (للاستخدام في بدء التشغيل)"""
    db_manager.initialize_database()