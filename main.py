# python -m uvicorn main:app --reload

from telegram.ext import Application
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import config
from database.session import init_db, using_sqlite
from webhooks.telegram import TelegramWebhookManager
from utils.logger import logger
import uvicorn
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق"""
    # بدء التشغيل
    try:
        logger.info("🚀 بدء تشغيل تطبيق بوت التليجرام...")
        
        # تهيئة قاعدة البيانات
        await init_db()
        logger.info("✅ تم تهيئة قاعدة البيانات")
        
        # تهيئة بوت تليجرام
        from handlers import setup_commands, setup_callbacks
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        setup_commands(application)
        setup_callbacks(application)
        app.state.application = application
        app.state.webhook_manager = TelegramWebhookManager(application)
        
        if config.ENV == "prod":
            logger.info("🔄 إعداد Webhook في بيئة الإنتاج...")
            await app.state.webhook_manager.setup_webhook()
        else:
            logger.info("💻 تشغيل في وضع التطوير المحلي")
        
        logger.info("✅ تم تهيئة التطبيق بنجاح")
        yield
    
    # التنظيف عند الإيقاف
    finally:
        logger.info("🛑 إيقاف التطبيق...")
        
        # إغلاق اتصالات قاعدة البيانات
        # لا نحتاج لإغلاق session في SQLAlchemy غير المتزامن
        if not using_sqlite:
            from database.session import async_engine
            await async_engine.dispose()
        
        # إزالة webhook في بيئة الإنتاج
        if config.ENV == "prod":
            await app.state.webhook_manager.delete_webhook()
            
        logger.info("✅ تم إيقاف التطبيق بنجاح")

# إنشاء تطبيق FastAPI
app = FastAPI(
    title="Video Hunter Bot API",
    description="واجهة برمجة تطبيقات لبوت تحميل الفيديوهات",
    version="1.0.0",
    lifespan=lifespan
)

# إعدادات CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# استيراد واجهات API
from api import router
app.include_router(router)

if __name__ == "__main__":
    # تحديد المنفذ من المتغيرات البيئية أو الإعدادات
    port = int(os.environ.get("PORT", config.API_PORT))
    
    # تشغيل التطبيق
    uvicorn.run(
        "main:app",
        host=config.API_HOST, 
        port=port,
        reload=config.ENV == "dev",
        # استخدام SSL فقط إذا كانت ملفات الشهادات موجودة
        ssl_keyfile=config.SSL_KEY_PATH if os.path.exists(config.SSL_KEY_PATH) else None,
        ssl_certfile=config.SSL_CERT_PATH if os.path.exists(config.SSL_CERT_PATH) else None
    )