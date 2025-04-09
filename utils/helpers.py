import datetime
import re
import logging
from datetime import timedelta
from typing import Optional, Union, List, Dict, Any
from pathlib import Path
from urllib.parse import urlparse
from config import config
from utils.logger import logger  # تم تصحيح الاستيراد

def format_duration(seconds: Union[int, float]) -> str:
    """تحويل المدة من ثواني إلى تنسيق مقروء (HH:MM:SS)"""
    try:
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 \
            else f"{minutes:02d}:{seconds:02d}"
    except Exception as e:
        logger.error(f"خطأ في تنسيق المدة: {e}")
        return "00:00"

def format_file_size(size_bytes: Union[int, float]) -> str:
    """تحويل حجم الملف إلى تنسيق مقروء (مثل MB, GB)"""
    units = ['B', 'KB', 'MB', 'GB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units)-1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"

def validate_url(url: str) -> bool:
    """التحقق من صحة الرابط وموافقته للأنماط المدعومة"""
    try:
        parsed_url = urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            return False
            
        return any(
            re.fullmatch(pattern, url)
            for pattern in config.SUPPORTED_PATTERNS
        )
    except Exception as e:
        logger.error(f"خطأ في التحقق من الرابط: {e}")
        return False

def generate_progress_bar(percentage: float, length: int = 10) -> str:
    """إنشاء شريط تقدم مرئي"""
    filled = '█' * int(percentage / 100 * length)
    empty = '░' * (length - len(filled))
    return f"[{filled}{empty}] {percentage:.1f}%"

def clean_filename(filename: str) -> str:
    """تنظيف أسماء الملفات من الأحرف غير المسموحة"""
    cleaned = re.sub(r'[\\/*?:"<>|]', '', filename)
    return cleaned.strip()[:50]  # تحديد طول اسم الملف

def split_message(text: str, max_length: int = 4000) -> List[str]:
    """تقسيم الرسائل الطويلة لتتناسب مع حدود التليجرام"""
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

def create_inline_keyboard(buttons: List[Dict[str, str]], columns: int = 2):
    """إنشاء لوحة مفاتيح inline بشكل ديناميكي مع أعمدة"""
    keyboard = []
    row = []
    
    for idx, btn in enumerate(buttons, 1):
        row.append(InlineKeyboardButton(btn['text'], callback_data=btn['data']))
        if idx % columns == 0:
            keyboard.append(row)
            row = []
    
    if row:  # إضافة الصف الأخير إذا كان غير مكتمل
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def calculate_remaining_time(start_time: datetime) -> str:
    """حساب الوقت المنقضي منذ بدء المهمة"""
    delta = datetime.now() - start_time
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def get_platform_from_url(url: str) -> str:
    """استخراج اسم المنصة من الرابط"""
    domain = urlparse(url).netloc.lower()
    platform_map = {
        'youtube': ['youtube', 'youtu.be'],
        'tiktok': ['tiktok'],
        'instagram': ['instagram'],
        'twitter': ['twitter', 'x.com'],
        'facebook': ['facebook']
    }
    
    for platform, domains in platform_map.items():
        if any(d in domain for d in domains):
            return platform
    return 'other'

def format_rewards_list(rewards: List[Dict]) -> str:
    """تنسيق قائمة المكافآت لعرضها للمستخدم"""
    return "\n".join(
        f"🎁 {r['name']} - {r['cost']} نقطة (مدة: {r['duration']} أيام)"
        for r in rewards
    )

def safe_int_convert(value: Any, default: int = 0) -> int:
    """تحويل آمن للقيم إلى أعداد صحيحة"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

# Example usage:
if __name__ == "__main__":
    # اختبار وظيفة تنسيق المدة
    print(format_duration(3661))  # 01:01:01
    
    # اختبار وظيفة تنسيق الحجم
    print(format_file_size(1500000))  # 1.43 MB
    
    # اختبار التحقق من الرابط
    print(validate_url("https://youtu.be/xyz"))  # True