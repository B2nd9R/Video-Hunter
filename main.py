from asyncio.log import logger
import logging
import asyncio
from typing import Optional
from telegram.ext import Application
from config import config
from database import init_db, SessionLocal
from handlers import (
    setup_commands,
    setup_messages,
    setup_callbacks
)
from utils.logger import setup_logging
from services.analytics import AnalyticsService
from services.reward_service import reward_service

# تكوين السجلات
setup_logging()

async def startup():
    """تهيئة التطبيق عند بدء التشغيل"""
    try:
        logger.info("🚀 بدء تشغيل البوت...")
        
        # تهيئة قاعدة البيانات مع التحقق من الجداول
        await init_db()
        
        # إنشاء جلسة جديدة للتحقق
        db = SessionLocal()
        try:
            from database.models import ClaimedReward
            if not db.query(ClaimedReward).first():
                logger.info("جدول claimed_rewards موجود ولكن فارغ")
        except Exception as e:
            logger.error(f"خطأ في التحقق من الجداول: {str(e)}")
        finally:
            db.close()
        
        # تسجيل الhandlers
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        setup_commands(application)
        setup_messages(application)
        setup_callbacks(application)
        logger.info("✅ تم تسجيل جميع ال handlers")
        
        # تشغيل خدمات الخلفية
        asyncio.create_task(background_tasks())
        logger.info("✅ تم تشغيل خدمات الخلفية")
        
        return application
        
    except Exception as e:
        logger.critical(f"فشل في بدء التشغيل: {str(e)}", exc_info=True)
        raise

async def background_tasks():
    """مهام الخلفية الدورية"""
    while True:
        try:
            # تحديث الإحصائيات كل ساعة
            stats = await AnalyticsService().get_system_health()
            logger.debug(f"إحصائيات النظام: {stats}")
            
            # تنظيف النقاط المنتهية
            await reward_service.cleanup_expired_rewards()
            
            await asyncio.sleep(3600)  # كل ساعة
            
        except Exception as e:
            logger.error(f"خطأ في مهام الخلفية: {str(e)}", exc_info=True)

async def shutdown(application: Application):
    """تنظيف الموارد عند الإغلاق"""
    try:
        logger.info("🛑 جارِ إيقاف البوت...")
        await application.shutdown()
        await application.updater.stop()
        await SessionLocal.close_all()
        logger.info("✅ تم التنظيف بنجاح")
    except Exception as e:
        logger.error(f"خطأ أثناء الإيقاف: {str(e)}", exc_info=True)

async def run_polling():
    """تشغيل البوت في وضع polling"""
    application = None
    try:
        application = await startup()
        logger.info("🔃 بدء التشغيل في وضع polling...")
        await application.run_polling()
    except Exception as e:
        logger.critical(f"خطأ رئيسي: {str(e)}", exc_info=True)
    finally:
        if application:
            await shutdown(application)

async def run_web():
    """تشغيل البوت في وضع webhook"""
    from webhooks.telegram import TelegramWebhookManager
    application = None
    try:
        application = await startup()
        webhook_manager = TelegramWebhookManager(application)
        
        logger.info("🌐 بدء التشغيل في وضع webhook...")
        await webhook_manager.setup_webhook()
        await application.start()
        await asyncio.Future()  # تشغيل إلى ما لا نهاية
    except Exception as e:
        logger.critical(f"خطأ رئيسي: {str(e)}", exc_info=True)
    finally:
        if application:
            await shutdown(application)

if __name__ == "__main__":
    try:
        if config.ENV == "prod":
            asyncio.run(run_web())
        else:
            asyncio.run(run_polling())
    except KeyboardInterrupt:
        logger.info("👋 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.critical(f"خطأ غير متوقع: {str(e)}", exc_info=True)
        raise