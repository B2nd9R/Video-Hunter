import datetime
import logging
import os
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from config import config
from services.downloader import download_video
from services.reward_service import claim_reward, get_active_rewards, get_user_points
from utils.helpers import format_file_size
from utils.logger import logger
from database.session import get_db

class CallbackHandler:
    """معالج أحداث الضغط على الأزرار التفاعلية"""
    
    def __init__(self):
        self.callback_actions = {
            'download': self.handle_download_callback,
            'buy': self.handle_reward_callback,
            'quality': self.handle_quality_callback
        }

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """التوجيه المركزي لجميع أحداث الضغط"""
        query = update.callback_query
        await query.answer()
        
        try:
            action, *data = query.data.split(':')
            handler = self.callback_actions.get(action)
            
            if handler:
                await handler(query, data)
            else:
                logger.warning(f"Unknown callback action: {action}")
                await query.edit_message_text("⚠️ هذا الزر لم يعد يعمل، يرجى المحاولة مرة أخرى")

        except Exception as e:
            logger.error(f"Callback error: {e}", exc_info=True)
            await query.edit_message_text("❌ حدث خطأ أثناء معالجة طلبك")

    async def handle_download_callback(self, query, data: list) -> None:
        """معالجة طلب التحميل من الأزرار"""
        url, quality = data[0], data[1] if len(data) > 1 else 'best'
        user_id = query.from_user.id
        
        try:
            await query.edit_message_text(f"⏳ جاري تحميل الفيديو بجودة {quality}...")
            
            # التحقق من المكافآت النشطة
            active_rewards = await get_active_rewards(user_id)
            vip_active = any(r['reward_id'] == 200 for r in active_rewards)  # VIP quality
            
            if quality == 'best' and vip_active:
                quality = '4k'  # ترقية الجودة إذا كان لدى المستخدم مكافأة VIP
            
            file_path = await download_video(url, quality)
            
            if not file_path:
                await query.edit_message_text("❌ فشل تحميل الفيديو")
                return
            
            file_size = format_file_size(os.path.getsize(file_path))
            await query.message.reply_video(
                video=open(file_path, 'rb'),
                caption=f"تم التحميل بنجاح 🎬\nالجودة: {quality.upper()}\nالحجم: {file_size}",
                supports_streaming=True
            )
            
            # تحديث سجل التحميلات
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO downloads 
                    (user_id, url, platform, download_date, file_size) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (user_id, url, await self._get_platform(url), datetime.now(), os.path.getsize(file_path))
                )
                conn.commit()
            
            await query.delete_message()
            os.remove(file_path)
            
        except Exception as e:
            logger.error(f"Download callback failed: {e}")
            await query.edit_message_text("❌ حدث خطأ غير متوقع أثناء التحميل")

    async def handle_reward_callback(self, query, data: list) -> None:
        """معالجة شراء المكافآت"""
        reward_id = int(data[0])
        user_id = query.from_user.id
        
        try:
            reward_info = config.REWARDS.get(reward_id)
            if not reward_info:
                await query.answer("⚠️ هذه المكافأة لم تعد متاحة", show_alert=True)
                return
            
            user_points = await get_user_points(user_id)
            if user_points < reward_id:
                await query.answer(
                    f"نقاطك غير كافية! لديك {user_points} من أصل {reward_id} نقطة",
                    show_alert=True
                )
                return
            
            # تنفيذ عملية الشراء
            result = await claim_reward(user_id, reward_id)
            
            await query.edit_message_text(
                f"🎉 تم تفعيل مكافأة {reward_info['name']} بنجاح!\n"
                f"📅 تنتهي في: {result['expiry_date']}\n"
                f"💎 النقاط المتبقية: {result['remaining_points']}"
            )
            
        except Exception as e:
            logger.error(f"Reward purchase failed: {e}")
            await query.answer("❌ فشلت عملية الشراء", show_alert=True)

    async def handle_quality_callback(self, query, data: list) -> None:
        """تغيير جودة التحميل المفضلة"""
        quality = data[0]
        user_id = query.from_user.id
        
        with get_db() as conn:
            conn.execute(
                "UPDATE settings SET default_quality = ? WHERE user_id = ?",
                (quality, user_id)
            )
            conn.commit()
        
        await query.answer(f"تم تعيين الجودة الافتراضية إلى {quality.upper()}")
        await query.edit_message_reply_markup(self._build_quality_keyboard(quality))

    def _build_quality_keyboard(self, selected_quality: str) -> InlineKeyboardMarkup:
        """بناء لوحة أزرار اختيار الجودة"""
        qualities = [
            ('أعلى جودة', 'best'),
            ('متوسطة (720p)', 'medium'),
            ('منخفضة (480p)', 'low')
        ]
        
        buttons = []
        for text, quality in qualities:
            if quality == selected_quality:
                text = f"✅ {text}"
            buttons.append(
                [InlineKeyboardButton(text, callback_data=f"quality:{quality}")]
            )
        
        return InlineKeyboardMarkup(buttons)

    async def _get_platform(self, url: str) -> str:
        """تحديد المنصة من الرابط"""
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
callback_handler = CallbackHandler()

# دالة التسجيل للاستخدام في التطبيق
def setup(application):
    application.add_handler(CallbackQueryHandler(callback_handler.handle_callback))
    logger.info("تم تسجيل معالج الأزرار التفاعلية")