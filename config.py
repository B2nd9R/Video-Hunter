import os
from pathlib import Path
from typing import Dict, Any, List, Pattern, ClassVar
import re
from pydantic_settings import BaseSettings
from pydantic import AnyUrl, field_validator

class Settings(BaseSettings):
    # إعدادات التطبيق الأساسية
    API_SECRET_KEY: str = "pJPwuoXl&DkyPNbED3FRmfP@P&KmAj^p9NodvZMUdOYa!63b"
    ENV: str = "dev"  # or "prod"
    BASE_DIR: Path = Path(__file__).parent
    
    # إعدادات Telegram
    TELEGRAM_TOKEN: str
    WEBHOOK_URL: AnyUrl | None = None
    
    # إعدادات قاعدة البيانات
    DATABASE_URL: str = "sqlite:///video_bot.db"
    
    # إعدادات API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # إعدادات الفيديو
    DEFAULT_QUALITY: str = "best"
    MAX_FILE_SIZE_MB: int = 50
    
    # أنماط الروابط المدعومة
    SUPPORTED_PLATFORMS: ClassVar[Dict[str, List[str]]] = {
        "tiktok": [
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+',
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+\?lang=\w+',
            r'https?://(www\.)?tiktok\.com/[\w\.-]+/video/\d+',
            r'https?://(www\.|vm\.)?tiktok\.com/.*/@[\w\.-]+/video/\d+',
            r'https?://vt\.tiktok\.com/\w+'
        ],
    
        "youtube": [
            r'https?://(www\.)?youtube\.com/(watch\?v=|shorts/)[\w\-]+',
            r'https?://(www\.)?youtube\.com/v/[\w\-]+',
            r'https?://(www\.)?youtube\.com/embed/[\w\-]+',
            r'https?://(www\.)?youtube\.com/playlist\?list=[\w\-]+',
            r'https?://youtu\.be/[\w\-]+'
        ],

        "instagram": [
            r'https?://(www\.)?instagram\.com/(p|reel|reels)/[\w\-]+',
            r'https?://(www\.)?instagram\.com/p/[\w\-]+',
            r'https?://(www\.)?instagram\.com/tv/[\w\-]+',
            r'https?://(www\.)?instagram\.com/stories/[\w\-]+/[\w\-]+',
            r'https?://(www\.)?instagram\.com/stories/[\w\-]+/[\w\-]+/[\w\-]+',
            r'https?://(www\.)?instagram\.com/([\w\-]+/)*story_reel/[\w\-]+'
        ],

        "twitter": [
            r'https?://(www\.)?(twitter\.com|x\.com)/[\w\-]+/status/\d+',
            r'https?://(www\.)?(twitter\.com|x\.com)/[a-zA-Z0-9_]+/status/\d+',
            r'https?://(www\.)?(twitter\.com|x\.com)/i/status/\d+',
            r'https?://(www\.)?(twitter\.com|x\.com)/[a-zA-Z0-9_]+/video/\d+',
            r'https?://(www\.)?(twitter\.com|x\.com)/[a-zA-Z0-9_]+/video/\d+\?lang=\w+',
            r'https?://(www\.)?(twitter\.com|x\.com)/[a-zA-Z0-9_]+/video/\d+\?ref_src=twsrc\%5Etfw',
            r'https?://(www\.)?(twitter\.com|x\.com)/[a-zA-Z0-9_]+/video/\d+\?ref_src=twsrc\%5Etfw\&amp;'
        ],

        "facebook": [
            r'https?://(www\.)?facebook\.com/[\w\-\.]+/(videos|reel)/\d+',
            r'https?://(www\.)?facebook\.com/[\w\-\.]+/videos/\d+',
            r'https?://(www\.)?facebook\.com/watch/?v=\d+'
        ]
    }
    
    # نظام المكافآت
    REWARDS: Dict[int, Dict[str, Any]] = {
        50: {"name": "إزالة انتظار التحويل", "duration": 7, "type": "feature"},
        100: {"name": "تحميل فيديوهات أطول", "duration": 7, "type": "feature"},
        200: {"name": "جودة VIP (4K)", "duration": 7, "type": "feature"},
        500: {"name": "مساحة تخزين 100MB", "duration": 7, "type": "storage"},
        1000: {"name": "عضوية ذهبية", "duration": 7, "type": "badge"}
    }

    # تحويل أنماط الروابط إلى regex patterns
    @property
    def SUPPORTED_PATTERNS(self) -> List[Pattern]:
        return [re.compile(pattern) for patterns in self.SUPPORTED_PLATFORMS.values() for pattern in patterns]
    
    # تحقق من صحة إعدادات الجودة
    @field_validator('DEFAULT_QUALITY')
    @classmethod
    def validate_quality(cls, v: str) -> str:
        if v not in ['best', 'medium', 'worst']:
            raise ValueError('الجودة يجب أن تكون واحدة من: best, medium, worst')
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True

# تهيئة الإعدادات
config = Settings()