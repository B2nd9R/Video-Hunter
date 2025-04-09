import re
import logging
from typing import Dict, Any
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters
from config import config
from services.downloader import download_video, get_video_info, clean_url
from services.reward_service import get_user_points
from utils.helpers import format_file_size
from utils.logger import logger
from database.session import get_db

class MessageHandler:
    """معالج الرسائل النصية الواردة من المستخدمين"""
    
    def __init__(self):
        self.settings_states = {
            "awaiting_quality": self.handle_quality_setting,
            "awaiting_size": self.handle_size_setting,
            "awaiting_language": self.handle_language_setting
        }

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """المعالج الرئيسي للرسائل النصية"""
        user = update.message.from_user
        text = update.message.text.strip()
        
        try:
            # التحقق من حالة الإعدادات أولاً
            if await self._check_settings_state(update, context, text):
                return
                
            # معالجة الروابط المباشرة
            if await self._is_supported_url(text):
                await self.handle_video_url(update, text)
                return
                
            # معالجة الأوامر النصية
            await self._handle_text_commands(update, text)
                
        except Exception as e:
            logger.error(f"Message handling error: {e}", exc_info=True)
            await update.message.reply_text("❌ حدث خطأ غير متوقع أثناء معالجة رسالتك")

    async def _check_settings_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
        """فحص ومعالجة حالات ضبط الإعدادات"""
        user_state = context.user_data.get('settings_state')
        if user_state and user_state in self.settings_states:
            handler = self.settings_states[user_state]
            await handler(update, context, text)
            return True
        return False

    async def _is_supported_url(self, text: str) -> bool:
        """التحقق مما إذا كان النص يحتوي على رابط مدعوم"""
        cleaned_url = await clean_url(text)
        return any(re.match(pattern, cleaned_url) for pattern in config.SUPPORTED_PATTERNS)

    async def handle_video_url(self, update: Update, url: str) -> None:
        """معالجة روابط الفيديو المرسلة مباشرة"""
        user = update.message.from_user
        msg = await update.message.reply_text("⏳ جاري معالجة طلبك...")
        
        try:
            # الحصول على إعدادات المستخدم
            with get_db() as conn:
                settings = conn.execute(
                    "SELECT default_quality, max_size FROM settings WHERE user_id = ?",
                    (user.id,)
                ).fetchone() or {'default_quality': 'best', 'max_size': 50}
            
            # تحميل الفيديو
            file_path = await download_video(url, settings['default_quality'])
            if not file_path:
                await msg.edit_text("❌ فشل تحميل الفيديو، يرجى التحقق من الرابط")
                return
            
            # التحقق من الحجم
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > settings['max_size']:
                await msg.edit_text(f"⚠️ جاري ضغط الفيديو (الحد الأقصى: {settings['max_size']}MB)...")
                file_path = await compress_video(file_path, settings['max_size'])
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            # إرسال الفيديو
            await update.message.reply_video(
                video=open(file_path, 'rb'),
                caption=f"تم التحميل بنجاح 🎬\nالحجم: {format_file_size(file_size_mb * 1024 * 1024)}",
                supports_streaming=True
            )
            
            # تسجيل التحميل
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO downloads 
                    (user_id, url, platform, download_date, file_size) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (user.id, url, await self._get_platform(url), datetime.now(), file_size_mb * 1024 * 1024)
                )
                conn.commit()
            
            await msg.delete()
            os.remove(file_path)
            
        except Exception as e:
            logger.error(f"Video URL handling failed: {e}")
            await msg.edit_text("❌ حدث خطأ أثناء معالجة الفيديو")

    async def _handle_text_commands(self, update: Update, text: str) -> None:
        """معالجة الأوامر النصية غير المرتبطة بالإعدادات"""
        user = update.message.from_user
        
        if text == "تغيير الجودة الافتراضية":
            await self.show_quality_options(update)
        elif text == "تغيير الحد الأقصى للحجم":
            await update.message.reply_text("📏 يرجى إدخال الحد الأقصى للحجم بالميجابايت (مثال: 50):")
            context.user_data['settings_state'] = "awaiting_size"
        elif text == "تغيير اللغة":
            await self.show_language_options(update)
        elif text == "العودة إلى القائمة الرئيسية":
            await self.show_main_menu(update)
        else:
            await update.message.reply_text(
                "🔍 لم أتعرف على طلبك، يمكنك إرسال:\n"
                "- رابط فيديو مباشر للتحميل\n"
                "- /help لعرض الأوامر المتاحة"
            )

    async def show_quality_options(self, update: Update) -> None:
        """عرض خيارات جودة التحميل"""
        keyboard = [
            ["أعلى جودة (افتراضي)"],
            ["جودة متوسطة (720p)"],
            ["جودة منخفضة (480p)"],
            ["العودة إلى الإعدادات"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "📊 اختر جودة التحميل الافتراضية:",
            reply_markup=reply_markup
        )
        context.user_data['settings_state'] = "awaiting_quality"

    async def handle_quality_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
        """معالجة اختيار جودة التحميل"""
        quality_map = {
            "أعلى جودة (افتراضي)": "best",
            "جودة متوسطة (720p)": "medium",
            "جودة منخفضة (480p)": "low"
        }
        
        if text in quality_map:
            with get_db() as conn:
                conn.execute(
                    "UPDATE settings SET default_quality = ? WHERE user_id = ?",
                    (quality_map[text], update.message.from_user.id)
                )
                conn.commit()
            
            await update.message.reply_text(f"✅ تم تعيين جودة التحميل إلى: {text}")
        await self.show_settings_menu(update)
        context.user_data.pop('settings_state', None)

    async def handle_size_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
        """معالجة إدخال الحد الأقصى للحجم"""
        try:
            max_size = int(text)
            if max_size <= 0:
                raise ValueError
                
            with get_db() as conn:
                conn.execute(
                    "UPDATE settings SET max_size = ? WHERE user_id = ?",
                    (max_size, update.message.from_user.id)
                )
                conn.commit()
            
            await update.message.reply_text(f"✅ تم تعيين الحد الأقصى لحجم الفيديو إلى: {max_size}MB")
        except ValueError:
            await update.message.reply_text("⚠️ يرجى إدخال رقم صحيح موجب (مثال: 50)")
            return
        
        context.user_data.pop('settings_state', None)
        await self.show_settings_menu(update)

    async def show_language_options(self, update: Update) -> None:
        """عرض خيارات اللغة"""
        keyboard = [
            ["العربية", "English"],
            ["العودة إلى الإعدادات"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🌐 اختر لغة الواجهة:",
            reply_markup=reply_markup
        )
        context.user_data['settings_state'] = "awaiting_language"

    async def handle_language_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
        """معالجة اختيار اللغة"""
        lang_map = {"العربية": "ar", "English": "en"}
        
        if text in lang_map:
            with get_db() as conn:
                conn.execute(
                    "UPDATE settings SET language = ? WHERE user_id = ?",
                    (lang_map[text], update.message.from_user.id)
                )
                conn.commit()
            
            await update.message.reply_text(f"✅ تم تغيير اللغة إلى: {text}")
        await self.show_settings_menu(update)
        context.user_data.pop('settings_state', None)

    async def show_settings_menu(self, update: Update) -> None:
        """عرض قائمة الإعدادات الرئيسية"""
        keyboard = [
            ["تغيير الجودة الافتراضية"],
            ["تغيير الحد الأقصى للحجم"],
            ["تغيير اللغة"],
            ["العودة إلى القائمة الرئيسية"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "⚙️ اختر من قائمة الإعدادات:",
            reply_markup=reply_markup
        )

    async def show_main_menu(self, update: Update) -> None:
        """عرض القائمة الرئيسية"""
        keyboard = [
            ["تحميل فيديو"],
            ["إعدادات البوت"],
            ["نقاطي والمكافآت"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🏠 القائمة الرئيسية:",
            reply_markup=reply_markup
        )
        context.user_data.pop('settings_state', None)

    async def _get_platform(self, url: str) -> str:
        """تحديد منصة الفيديو من الرابط"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'YouTube'
        elif 'tiktok.com' in url:
            return 'TikTok'
        elif 'instagram.com' in url:
            return 'Instagram'
        elif 'twitter.com' in url or 'x.com' in url:
            return 'Twitter/X'
        elif 'facebook.com' in url:
            return 'Facebook'
        return 'Other'

# تهيئة المعالج الرئيسي
message_handler = MessageHandler()

# دالة التسجيل للاستخدام في التطبيق
def setup(application):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler.handle_message))
    logger.info("تم تسجيل معالج الرسائل النصية")