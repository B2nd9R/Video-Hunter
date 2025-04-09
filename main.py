from asyncio.log import logger
import logging
import asyncio
from typing import Optional
from telegram.ext import Application
from config import config
from database import init_db, SessionLocal, engine
from handlers import (
    setup_commands,
    setup_messages,
    setup_callbacks
)
from utils.logger import setup_logging
from services.analytics import AnalyticsService
from services.reward_service import reward_service
from sqlalchemy import inspect

# تكوين السجلات
setup_logging()

async def verify_tables_exist():
    """التحقق من وجود جميع الجداول المطلوبة"""
    required_tables = ['users', 'claimed_rewards', 'user_points', 'downloads']
    inspector = inspect(engine)
    
    missing_tables = [table for table in required_tables if not inspector.has_table(table)]
    if missing_tables:
        raise RuntimeError(f"الجداول الناقصة: {missing_tables}")

async def startup():
    """تهيئة التطبيق عند بدء التشغيل"""
    try:
        logger.info("🚀 بدء تشغيل البوت...")
        
        # 1. تهيئة قاعدة البيانات مع التحقق من الجداول
        await init_db()
        
        # 2. التحقق الصارم من وجود الجداول
        await verify_tables_exist()
        
        # 3. التحقق من اتصال قاعدة البيانات
        db = SessionLocal()
        try:
            db.execute("SELECT 1")  # اختبار اتصال بسيط
            logger.info("✅ اتصال قاعدة البيانات نشط")
        except Exception as e:
            raise RuntimeError(f"فشل اختبار اتصال قاعدة البيانات: {str(e)}")
        finally:
            db.close()
        
        # 4. تسجيل الhandlers
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        setup_commands(application)
        setup_messages(application)
        setup_callbacks(application)
        logger.info("✅ تم تسجيل جميع ال handlers")
        
        # 5. تشغيل خدمات الخلفية
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