# python -m uvicorn main:app --reload

import asyncio
import logging
from contextlib import asynccontextmanager
from telegram.ext import Application
from config import config
from database import init_db, get_db, async_engine
from handlers import (
    setup_commands,
    setup_messages,
    setup_callbacks
)
from utils.logger import setup_logging
from services.analytics import AnalyticsService
from services.reward_service import reward_service
from sqlalchemy import inspect

# تكوين نظام السجلات
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_):
    """إدارة دورة حياة التطبيق"""
    try:
        await startup()
        yield
    finally:
        await shutdown()

async def verify_tables_exist():
    """التحقق من وجود الجداول الأساسية"""
    try:
        async with async_engine.connect() as conn:
            inspector = await conn.run_sync(inspect)
            required_tables = [
                'users', 
                'downloads', 
                'user_points', 
                'claimed_rewards'
            ]
            
            missing = [
                table 
                for table in required_tables 
                if not inspector.has_table(table)
            ]
            
            if missing:
                raise RuntimeError(f"جداول مفقودة: {', '.join(missing)}")
                
    except Exception as e:
        logger.error(f"فشل التحقق: {str(e)}")
        raise

async def startup():
    """إجراءات بدء التشغيل"""
    try:
        logger.info("🚀 بدء عملية التهيئة...")
        
        # 1. تهيئة قاعدة البيانات
        await init_db()
        
        # 2. التحقق من الجداول
        await verify_tables_exist()
        
        # 3. اختبار الاتصال
        async with get_db() as db:
            await db.execute("SELECT 1")
            logger.info("✅ اتصال قاعدة البيانات نشط")
        
        # 4. إعداد تطبيق التيليجرام
        application = Application.builder().token(config.TELEGRAM_TOKEN).build()
        setup_commands(application)
        setup_messages(application)
        setup_callbacks(application)
        logger.info("✅ تم إعداد handlers البوت")
        
        # 5. تشغيل المهام الخلفية
        asyncio.create_task(background_tasks())
        
        return application
        
    except Exception as e:
        logger.critical(f"فشل التشغيل: {str(e)}", exc_info=True)
        raise

async def background_tasks():
    """المهام الدورية الخلفية"""
    while True:
        try:
            # تحديث الإحصائيات
            stats = await AnalyticsService.get_system_stats()
            logger.debug(f"الإحصائيات: {stats}")
            
            # تنظيف المكافآت المنتهية
            await reward_service.cleanup_expired_rewards()
            
            await asyncio.sleep(3600)  # كل ساعة
            
        except Exception as e:
            logger.error(f"خطأ في المهام الخلفية: {str(e)}", exc_info=True)
            await asyncio.sleep(60)

async def shutdown():
    """إجراءات إيقاف التشغيل"""
    try:
        logger.info("🛑 بدء عملية الإيقاف...")
        await async_engine.dispose()
        logger.info("✅ تم إغلاق اتصالات قاعدة البيانات")
    except Exception as e:
        logger.error(f"خطأ أثناء الإيقاف: {str(e)}", exc_info=True)

async def run_polling():
    """وضع التشغيل Polling"""
    application = None
    try:
        application = await startup()
        logger.info("🔃 بدء التشغيل في وضع Polling...")
        await application.run_polling()
    finally:
        if application:
            await shutdown()

async def run_webhook():
    """وضع التشغيل Webhook"""
    from webhooks.telegram import webhook_manager
    application = None
    try:
        application = await startup()
        logger.info("🌍 بدء التشغيل في وضع Webhook...")
        await webhook_manager.setup()
        await application.start()
        await asyncio.Future()  # تشغيل دائم
    finally:
        if application:
            await shutdown()

if __name__ == "__main__":
    try:
        if config.ENV == "prod":
            asyncio.run(run_webhook())
        else:
            asyncio.run(run_polling())
    except KeyboardInterrupt:
        logger.info("👋 تم الإيقاف بواسطة المستخدم")
    except Exception as e:
        logger.critical(f"خطأ غير متوقع: {str(e)}", exc_info=True)