from asyncio.log import logger
import logging
import asyncio
from typing import Optional
from telegram.ext import Application
from config import config
from database.session import init_db, session
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
        
        # تهيئة قاعدة البيانات
        await init_db()
        logger.info("✅ تم تهيئة قاعدة البيانات")
        
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
        logger.critical(f"فشل في بدء التشغيل: {str(e)}")
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
            logger.error(f"خطأ في مهام الخلفية: {str(e)}")

async def shutdown(application: Application):
    """تنظيف الموارد عند الإغلاق"""
    try:
        logger.info("🛑 جارِ إيقاف البوت...")
        await application.shutdown()
        await application.updater.stop()
        await session.close()
        logger.info("✅ تم التنظيف بنجاح")
    except Exception as e:
        logger.error(f"خطأ أثناء الإيقاف: {str(e)}")

async def run_polling():
    """تشغيل البوت في وضع polling"""
    application = await startup()
    try:
        logger.info("🔃 بدء التشغيل في وضع polling...")
        await application.run_polling()
    finally:
        await shutdown(application)

async def run_web():
    """تشغيل البوت في وضع webhook"""
    from webhooks.telegram import TelegramWebhookManager
    application = await startup()
    webhook_manager = TelegramWebhookManager(application)
    
    try:
        logger.info("🌐 بدء التشغيل في وضع webhook...")
        await webhook_manager.setup_webhook()
        await application.start()
        await asyncio.Future()  # تشغيل إلى ما لا نهاية
    finally:
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
        logger.critical(f"خطأ غير متوقع: {str(e)}")
        raise