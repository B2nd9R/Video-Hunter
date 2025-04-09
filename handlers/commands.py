import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Any

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import ContextTypes, CommandHandler

from config import config
from database.session import get_db
from services.downloader import (
    download_video,
    get_video_info,
    clean_url,
    compress_video,
    download_with_ytdlp
)
from services.reward_service import (
    get_user_points,
    get_active_rewards,
    claim_reward
)
from utils.helpers import (
    format_duration,
    format_file_size,
    validate_url
)
from utils.logger import logger

# ========== أوامر البوت الأساسية ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """رسالة ترحيبية موسعة مع معلومات النظام"""
    try:
        user = update.message.from_user
        welcome_text = f"""
🎬 <b>مرحباً بك {user.first_name} في بوت تحميل الفيديوهات!</b>

📥 <u>المنصات المدعومة:</u>
- YouTube | TikTok | Instagram
- Twitter/X | Facebook | وغيرها

✨ <u>الميزات الرئيسية:</u>
✔ تحميل بجودة عالية (حتى 4K)
✔ ضغط الفيديوهات حسب الحجم المطلوب
✔ نظام النقاط والمكافآت التفضيلية
✔ سجل تحميلات شخصي كامل

🎮 <u>كيفية الاستخدام:</u>
1. أرسل رابط الفيديو مباشرة للتحميل
2. استخدم /info لعرض معلومات الفيديو
3. اكتسب النقاط مع كل تحميل

📌 <b>جرب هذه الأوامر:</b>
/info [رابط] - عرض معلومات الفيديو
/compress [حجم] [رابط] - ضغط الفيديو
/rewards - عرض نظام المكافآت
"""
        await update.message.reply_text(welcome_text, parse_mode='HTML')
        
        # تسجيل المستخدم في قاعدة البيانات
        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, join_date) VALUES (?, ?, ?, ?, ?)",
                (user.id, user.username, user.first_name, user.last_name, datetime.now())
            )
            conn.commit()
            
    except Exception as e:
        logger.error(f"خطأ في أمر start: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء تحميل رسالة الترحيب")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """قائمة مساعدة منظمة مع تصنيفات"""
    help_text = """
🛠 <b>قائمة الأوامر المتاحة:</b>

📥 <u>أوامر التحميل:</u>
/start - بدء استخدام البوت
/info [رابط] - عرض معلومات الفيديو
/formats [رابط] - عرض جودات التحميل
/compress [حجم] [رابط] - ضغط الفيديو (مثال: /compress 25MB رابط)

📊 <u>أوامر الحساب:</u>
/history - سجل التحميلات (آخر 10)
/settings - ضبط إعدادات الجودة والحجم
/rewards - نظام المكافآت والنقاط

❓ <u>أوامر المساعدة:</u>
/help - عرض هذه القائمة
"""
    await update.message.reply_text(help_text, parse_mode='HTML')

# ========== أوامر معالجة الفيديو ==========

async def video_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض معلومات الفيديو مع تحسينات العرض"""
    try:
        if not context.args:
            await update.message.reply_text("⚠️ يرجى إرسال رابط الفيديو مع الأمر\nمثال: /info https://youtu.be/xyz")
            return

        url = clean_url(' '.join(context.args))
        if not validate_url(url):
            await update.message.reply_text("❌ الرابط غير مدعوم أو غير صالح")
            return

        video_data = await get_video_info(url)
        if not video_data:
            await update.message.reply_text("❌ لم يتم العثور على معلومات الفيديو، يرجى التحقق من الرابط")
            return

        response = f"""
📹 <b>معلومات الفيديو:</b>
━━━━━━━━━━━━━━
🔍 <b>العنوان:</b> {video_data.get('title', 'غير معروف')}
⏱ <b>المدة:</b> {format_duration(video_data.get('duration', 0))}
📦 <b>الحجم:</b> {format_file_size(video_data.get('filesize', 0))}
🖼 <b>الجودة:</b> {video_data.get('resolution', 'غير معروف')}
📌 <b>المصدر:</b> {url}
"""
        await update.message.reply_text(response, parse_mode='HTML')

        if video_data.get('thumbnail'):
            try:
                await update.message.reply_photo(video_data['thumbnail'])
            except Exception as e:
                logger.warning(f"فشل إرسال الصورة المصغرة: {e}")

    except Exception as e:
        logger.error(f"خطأ في أمر video_info: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء معالجة طلبك")

async def list_formats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض جودات الفيديو مع واجهة تفاعلية محسنة"""
    try:
        if not context.args:
            await update.message.reply_text("⚠️ يرجى إرسال رابط الفيديو مع الأمر\nمثال: /formats https://youtu.be/xyz")
            return

        url = clean_url(' '.join(context.args))
        if not validate_url(url):
            await update.message.reply_text("❌ الرابط غير مدعوم أو غير صالح")
            return

        video_data = await get_video_info(url)
        if not video_data or not video_data.get('formats'):
            await update.message.reply_text("❌ لا تتوفر جودات لهذا الفيديو")
            return

        formats_list = []
        seen_formats = set()
        
        for fmt in video_data['formats']:
            if fmt.get('vcodec') == 'none':
                continue
                
            format_id = fmt.get('format_id', 'unknown')
            if format_id in seen_formats:
                continue
                
            seen_formats.add(format_id)
            
            format_str = (
                f"🎬 <b>{format_id}</b> | "
                f"📏 {fmt.get('resolution', 'غير معروف')} | "
                f"💾 {format_file_size(fmt.get('filesize', 0))}"
            )
            formats_list.append(format_str)

        response = "📋 <b>الجودات المتاحة:</b>\n" + "\n".join(formats_list[:15])
        
        keyboard = [
            [InlineKeyboardButton("⬇️ أعلى جودة", callback_data=f"dl:{url}:best")],
            [InlineKeyboardButton("⬇️ جودة متوسطة", callback_data=f"dl:{url}:medium")],
            [InlineKeyboardButton("⬇️ أقل جودة", callback_data=f"dl:{url}:low")]
        ]
        
        await update.message.reply_text(
            response,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"خطأ في أمر list_formats: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء جلب الجودات المتاحة")

async def compress_video_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ضغط الفيديو إلى حجم معين"""
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "⚖️ يرجى تحديد الحجم المطلوب والرابط\n"
                "مثال: /compress 25MB https://youtu.be/xyz"
            )
            return

        size_arg = context.args[0].upper()
        if not size_arg.endswith('MB'):
            await update.message.reply_text("⚠️ يرجى تحديد الحجم بالميجابايت (مثال: 25MB)")
            return

        try:
            target_size = int(size_arg[:-2])
            if target_size <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ حجم غير صالح. يرجى استخدام أرقام فقط (مثال: 25MB)")
            return

        url = clean_url(' '.join(context.args[1:]))
        if not validate_url(url):
            await update.message.reply_text("❌ الرابط غير مدعوم أو غير صالح")
            return

        msg = await update.message.reply_text(f"⏳ جاري تحميل الفيديو للضغط إلى {target_size}MB...")

        video_path = await download_with_ytdlp(url)
        if not video_path:
            await msg.edit_text("❌ فشل تحميل الفيديو. يرجى التأكد من الرابط")
            return

        await msg.edit_text("🔧 جاري ضغط الفيديو...")
        compressed_path = await compress_video(video_path, target_size)

        file_size = os.path.getsize(compressed_path) / (1024 * 1024)
        await msg.edit_text(f"✅ تم ضغط الفيديو بنجاح إلى {file_size:.1f}MB")

        await update.message.reply_video(
            video=open(compressed_path, 'rb'),
            caption=f"تم ضغط الفيديو إلى {file_size:.1f}MB",
            supports_streaming=True
        )

        # تنظيف الملفات المؤقتة
        os.remove(video_path)
        os.remove(compressed_path)

    except Exception as e:
        logger.error(f"خطأ في أمر compress: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء معالجة الفيديو")

# ========== أوامر إدارة الحساب ==========

async def download_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض سجل التحميلات للمستخدم"""
    try:
        user_id = update.message.from_user.id
        
        with get_db() as conn:
            history = conn.execute(
                """SELECT url, platform, download_date, file_size, status 
                FROM downloads 
                WHERE user_id = ? 
                ORDER BY download_date DESC 
                LIMIT 10""",
                (user_id,)
            ).fetchall()

        if not history:
            await update.message.reply_text("📭 لم تقم بأي تحميلات بعد.")
            return

        history_text = "⏳ <b>سجل آخر 10 تحميلات:</b>\n━━━━━━━━━━━━━━\n"
        for idx, item in enumerate(history, 1):
            date = datetime.strptime(item['download_date'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
            status_icon = "✅" if item['status'] == 'completed' else "❌"
            history_text += (
                f"{idx}. {status_icon} <b>{item['platform']}</b>\n"
                f"   📅 {date} | 📦 {format_file_size(item['file_size'])}\n"
                f"   🔗 {item['url'][:30]}...\n\n"
            )

        await update.message.reply_text(history_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"خطأ في أمر history: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء جلب سجل التحميلات")

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """قائمة إعدادات المستخدم"""
    try:
        user_id = update.message.from_user.id
        
        with get_db() as conn:
            settings = conn.execute(
                """SELECT default_quality, max_size, language, notification_enabled 
                FROM settings 
                WHERE user_id = ?""",
                (user_id,)
            ).fetchone()

        if not settings:
            await update.message.reply_text("❌ تعذر تحميل الإعدادات. يرجى المحاولة لاحقاً")
            return

        settings_text = f"""
⚙️ <b>الإعدادات الحالية:</b>
━━━━━━━━━━━━━━
📊 <b>الجودة:</b> {settings['default_quality']}
📏 <b>الحد الأقصى:</b> {settings['max_size']}MB
🌐 <b>اللغة:</b> {settings['language']}
🔔 <b>الإشعارات:</b> {'مفعّلة' if settings['notification_enabled'] else 'معطّلة'}
"""
        keyboard = [
            ["تغيير الجودة الافتراضية"],
            ["تغيير الحد الأقصى للحجم"],
            ["تغيير اللغة"],
            ["تفعيل/تعطيل الإشعارات"],
            ["العودة إلى القائمة الرئيسية"]
        ]
        
        await update.message.reply_text(
            settings_text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"خطأ في أمر settings: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء تحميل الإعدادات")

async def rewards_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض نظام المكافآت والنقاط"""
    try:
        user_id = update.message.from_user.id
        points = get_user_points(user_id)
        active_rewards = get_active_rewards(user_id)

        rewards_text = """
🎁 <b>نظام المكافآت:</b>
━━━━━━━━━━━━━━
رصيدك الحالي: {} نقطة

<b>المكافآت المتاحة:</b>
""".format(points)

        for cost, reward in config.REWARDS.items():
            rewards_text += f"\n💰 <b>{cost} نقطة</b> - {reward['name']} ({reward['duration']} أيام)"

        if active_rewards:
            rewards_text += "\n\n✨ <b>مكافآتك النشطة:</b>"
            for reward in active_rewards:
                reward_info = config.REWARDS[reward['reward_id']]
                rewards_text += f"\n- {reward_info['name']} (تنتهي في {reward['expiry_date']})"

        keyboard = [
            [InlineKeyboardButton(f"شراء {cost} نقطة", callback_data=f"buy_{cost}")] 
            for cost in config.REWARDS.keys()
        ]
        
        await update.message.reply_text(
            rewards_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"خطأ في أمر rewards: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء تحميل نظام المكافآت")

# ========== تسجيل الأوامر ==========

def setup(application):
    """تسجيل جميع أوامر البوت"""
    commands = [
        ('start', start),
        ('help', help_command),
        ('info', video_info),
        ('formats', list_formats),
        ('compress', compress_video_cmd),
        ('history', download_history),
        ('settings', settings_menu),
        ('rewards', rewards_command)
    ]
    
    for command, handler in commands:
        application.add_handler(CommandHandler(command, handler))
    
    logger.info("تم تسجيل جميع أوامر البوت بنجاح")