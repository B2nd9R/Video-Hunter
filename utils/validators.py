import re
import logging
from datetime import datetime
from typing import Union, Optional, Dict, Any
from urllib.parse import urlparse
from config import config
from utils.logger import logger

class Validator:
    """نظام تحقق مركزي لجميع مدخلات التطبيق"""
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """التحقق من صحة الرابط وتوافقه مع المنصات المدعومة"""
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return False
                
            return any(
                re.fullmatch(pattern, url)
                for pattern in config.SUPPORTED_PATTERNS
            )
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False

    @staticmethod
    def validate_quality(quality: str) -> bool:
        """التحقق من صحة إعدادات الجودة"""
        valid_qualities = ['best', 'medium', 'low', '4k']
        return quality.lower() in valid_qualities

    @staticmethod
    def validate_file_size(size: Union[int, float]) -> bool:
        """التحقق من صحة حجم الملف"""
        return 1 <= size <= config.MAX_FILE_SIZE_MB

    @staticmethod
    def validate_user_input(text: str, max_length: int = 200) -> bool:
        """التحقق من صحة المدخلات النصية للمستخدم"""
        return 1 <= len(text.strip()) <= max_length

    @staticmethod
    def validate_date_format(date_str: str, fmt: str = "%Y-%m-%d") -> bool:
        """التحقق من تنسيق التاريخ"""
        try:
            datetime.strptime(date_str, fmt)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_reward_id(reward_id: int) -> bool:
        """التحقق من وجود المكافأة في القائمة"""
        return reward_id in config.REWARDS

    @staticmethod
    def validate_points(points: Union[int, float]) -> bool:
        """التحقق من صحة قيم النقاط"""
        return isinstance(points, (int, float)) and points >= 0

    @staticmethod
    def validate_platform(platform: str) -> bool:
        """التحقق من المنصة المدعومة"""
        return platform.lower() in [
            'youtube',
            'tiktok',
            'instagram',
            'twitter',
            'facebook'
        ]

    @staticmethod
    def validate_user_permissions(user_data: Dict[str, Any]) -> bool:
        """التحقق من صلاحيات المستخدم"""
        return user_data.get('is_admin', False) or user_data.get('is_vip', False)

    @staticmethod
    def validate_download_params(params: Dict[str, Any]) -> bool:
        """التحقق الشامل لمعاملات التحميل"""
        return all([
            Validator.validate_url(params.get('url', '')),
            Validator.validate_quality(params.get('quality', '')),
            Validator.validate_file_size(params.get('file_size', 0))
        ])

    @staticmethod
    def validate_filename(filename: str) -> bool:
        """التحقق من صحة اسم الملف"""
        pattern = r'^[a-zA-Z0-9_\-\u0600-\u06FF ]+\.[a-zA-Z0-9]{3,4}$'
        return re.match(pattern, filename) is not None

# اختبارات التوافق
if __name__ == "__main__":
    v = Validator()
    
    # اختبار التحقق من الروابط
    print(v.validate_url("https://youtu.be/abc123"))  # True
    print(v.validate_url("invalid.url"))  # False
    
    # اختبار التحقق من الجودة
    print(v.validate_quality("best"))  # True
    print(v.validate_quality("invalid"))  # False
    
    # اختبار التحقق من حجم الملف
    print(v.validate_file_size(25))  # True (إذا كان MAX_FILE_SIZE=50)
    print(v.validate_file_size(100))  # False