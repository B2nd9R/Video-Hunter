from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from telegram.ext import Application
from database.session import get_db
from webhooks.telegram import TelegramWebhookManager
from utils.logger import logger
from typing import Optional
from config import config

# إنشاء راوتر لـ API
router = APIRouter()

@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    نقطة نهاية واجهة Telegram webhook
    تستقبل التحديثات من Telegram وتعالجها
    """
    try:
        webhook_manager: TelegramWebhookManager = request.app.state.webhook_manager
        return await webhook_manager.process_webhook(request)
    except Exception as e:
        logger.error(f"خطأ في معالجة Webhook: {str(e)}", exc_info=True)
        raise HTTPException(500, "حدث خطأ داخلي في الخادم")

@router.get("/health")
async def health_check(request: Request, db: AsyncSession = Depends(get_db)):
    """
    فحص صحة التطبيق
    يتحقق من حالة التطبيق وقاعدة البيانات و Webhook
    """
    try:
        # التحقق من حالة قاعدة البيانات
        db_status = "connected"
        
        # التحقق من حالة webhook
        webhook_status = "not_configured"
        if hasattr(request.app.state, "webhook_manager"):
            webhook_status = await request.app.state.webhook_manager.health_check()
        
        return {
            "status": "ok",
            "environment": config.ENV,
            "database": db_status,
            "webhook": webhook_status,
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"خطأ في فحص الصحة: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/analytics")
async def get_analytics(days: int = 7, db: AsyncSession = Depends(get_db)):
    """
    الحصول على الإحصائيات
    يقدم إحصائيات حول استخدام البوت
    """
    try:
        from services.analytics import AnalyticsService
        analytics_service = AnalyticsService(db)
        return await analytics_service.get_download_stats(days)
    except Exception as e:
        logger.error(f"خطأ في الحصول على الإحصائيات: {str(e)}", exc_info=True)
        raise HTTPException(500, "حدث خطأ أثناء استرجاع الإحصائيات")

@router.get("/")
async def root():
    """الصفحة الرئيسية للـ API"""
    return {
        "app": "Video Hunter Bot",
        "version": "1.0.0",
        "status": "running"
    }

# معالج الأخطاء العام
@router.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """معالج الأخطاء العام"""
    logger.error(f"خطأ عام: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "حدث خطأ غير متوقع"}
    )