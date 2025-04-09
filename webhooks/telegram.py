import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException
from telegram import Update
from telegram.ext import Application
from config import config
from utils.logger import logger
from utils.helpers import validate_url

class TelegramWebhookManager:
    """مدير متكامل لمعالجة وتكوين واجهة ويب هوك التليجرام"""
    
    def __init__(self, application: Application):
        self.application = application
        self.bot = application.bot
        self.webhook_url = config.WEBHOOK_URL
        self.secret_token = config.API_SECRET_KEY
        
        # التحقق من صحة إعدادات الويب هوك
        if not validate_url(self.webhook_url):
            logger.critical("عنوان الويب هوك غير صالح!")
            raise ValueError("Invalid webhook URL configuration")

    async def setup_webhook(self) -> bool:
        """تهيئة إعدادات الويب هوك مع التحقق المتقدم"""
        try:
            result = await self.bot.set_webhook(
                url=self.webhook_url,
                secret_token=self.secret_token,
                allowed_updates=[
                    "message", 
                    "callback_query",
                    "chat_member",
                    "my_chat_member"
                ],
                drop_pending_updates=True
            )
            
            if result:
                logger.info(f"تم تفعيل الويب هوك بنجاح على: {self.webhook_url}")
                await self._verify_webhook()
                return True
                
            logger.error("فشل في تفعيل الويب هوك")
            return False
            
        except Exception as e:
            logger.error(f"فشل إعداد الويب هوك: {str(e)}")
            raise HTTPException(500, "Internal server error during webhook setup")

    async def process_webhook(self, request: Request) -> Dict[str, Any]:
        """معالجة طلبات الويب هوك الواردة مع التحقق الأمني"""
        # التحقق من التوكن السري
        if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != self.secret_token:
            raise HTTPException(403, "Forbidden: Invalid secret token")
        
        try:
            data = await request.json()
            update = Update.de_json(data, self.bot)
            await self.application.process_update(update)
            return {"status": "success", "processed_update_id": update.update_id}
            
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            raise HTTPException(400, "Invalid update data") from e

    async def delete_webhook(self) -> bool:
        """حذف إعدادات الويب هوك مع تنظيف البيانات"""
        try:
            result = await self.bot.delete_webhook(drop_pending_updates=True)
            if result:
                logger.info("تم إلغاء تفعيل الويب هوك بنجاح")
                return True
            return False
        except Exception as e:
            logger.error(f"فشل في حذف الويب هوك: {str(e)}")
            return False

    async def _verify_webhook(self) -> None:
        """تحقق من تفعيل الويب هوك فعليًا"""
        webhook_info = await self.bot.get_webhook_info()
        if webhook_info.url != self.webhook_url:
            logger.error("معلومات الويب هوك غير متطابقة!")
            raise ConnectionError("Webhook verification failed")
            
        logger.debug(f"معلومات الويب هوك: {webhook_info.to_dict()}")

    async def health_check(self) -> Dict[str, Any]:
        """فحص صحة إعدادات الويب هوك"""
        try:
            webhook_info = await self.bot.get_webhook_info()
            return {
                "status": "active" if webhook_info.url else "inactive",
                "url": webhook_info.url,
                "pending_updates": webhook_info.pending_update_count,
                "last_error": webhook_info.last_error_message,
                "certificate_expiration": webhook_info.ip_address
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"status": "error", "details": str(e)}

# -----------------------------------------------------------
# مثال للاستخدام مع FastAPI:
# from telegram.ext import Application
# from webhooks.telegram import TelegramWebhookManager

# app = FastAPI()
# telegram_app = Application.builder().token("TOKEN").build()
# webhook_manager = TelegramWebhookManager(telegram_app)

# @app.on_event("startup")
# async def on_startup():
#     await webhook_manager.setup_webhook()

# @app.post("/webhook")
# async def handle_webhook(request: Request):
#     return await webhook_manager.process_webhook(request)

if __name__ == "__main__":
    # اختبار محلي للويب هوك
    import asyncio
    from telegram.ext import Application
    
    async def test_webhook():
        test_app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        manager = TelegramWebhookManager(test_app)
        
        try:
            await manager.setup_webhook()
            print(await manager.health_check())
            await asyncio.sleep(5)
            await manager.delete_webhook()
        except Exception as e:
            print(f"Test failed: {str(e)}")
    
    asyncio.run(test_webhook())