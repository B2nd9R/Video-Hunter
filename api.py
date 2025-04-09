from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from config import config
from database.session import init_db, session
from webhooks.telegram import TelegramWebhookManager
from utils.logger import logger
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق"""
    # بدء التشغيل
    try:
        logger.info("🚀 بدء تشغيل واجهة API...")
        await init_db()
        
        from handlers import setup_commands, setup_callbacks
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        setup_commands(application)
        setup_callbacks(application)
        app.state.application = application
        app.state.webhook_manager = TelegramWebhookManager(application)
        
        if config.ENV == "prod":
            await app.state.webhook_manager.setup_webhook()
        
        logger.info("✅ تم تهيئة التطبيق بنجاح")
        yield
    
    # التنظيف عند الإيقاف
    finally:
        logger.info("🛑 إيقاف واجهة API...")
        await session.close()
        if config.ENV == "prod":
            await app.state.webhook_manager.delete_webhook()
        logger.info("✅ تم التنظيف بنجاح")

app = FastAPI(lifespan=lifespan)

# إعدادات CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """نقطة نهاية واجهة Telegram webhook"""
    try:
        return await app.state.webhook_manager.process_webhook(request)
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(500, "Internal server error")

@app.get("/health")
async def health_check():
    """فحص صحة التطبيق"""
    return {
        "status": "ok",
        "environment": config.ENV,
        "database": "connected",
        "webhook": await app.state.webhook_manager.health_check()
    }

@app.get("/analytics")
async def get_analytics(days: int = 7):
    """الحصول على الإحصائيات"""
    from services.analytics import AnalyticsService
    return await AnalyticsService().get_download_stats(days)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """معالج الأخطاء العام"""
    logger.error(f"Global error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "حدث خطأ غير متوقع"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.ENV == "dev",
        ssl_keyfile=config.SSL_KEY_PATH,
        ssl_certfile=config.SSL_CERT_PATH
    )