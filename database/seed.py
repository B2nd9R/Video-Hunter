import logging
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from .session import AsyncSessionLocal, async_engine
from .models import (
    User,
    UserSettings,
    Download,
    UserPoints,
    ClaimedReward,
    SystemLog
)
from config import config
from utils.logger import logger

class DatabaseSeeder:
    """نظام تهيئة البيانات الأولية مع دعم كامل للـ Async"""
    
    def __init__(self):
        self.fake = Faker()
        self.default_password = "P@ssw0rd123!"

    async def _get_session(self) -> AsyncSession:
        """الحصول على جلسة قاعدة البيانات"""
        return AsyncSessionLocal()

    async def clear_existing_data(self):
        """حذف جميع البيانات الحالية"""
        async with await self._get_session() as session:
            try:
                # الحصول على قائمة الجداول
                inspector = await session.run_sync(lambda conn: inspect(conn))
                tables = inspector.get_table_names()
                
                # حذف البيانات من جميع الجداول
                for table in tables:
                    try:
                        result = await session.execute(f"TRUNCATE TABLE {table} CASCADE")
                        logger.info(f"تم حذف بيانات جدول {table}")
                    except Exception as e:
                        logger.warning(f"خطأ في حذف جدول {table}: {str(e)}")
                        await session.rollback()
                
                await session.commit()
                logger.info("✅ تم حذف جميع البيانات بنجاح")
            except Exception as e:
                await session.rollback()
                logger.critical(f"❌ فشل في حذف البيانات: {str(e)}", exc_info=True)
                raise

    async def seed_default_users(self):
        """إنشاء مستخدمين افتراضيين"""
        async with await self._get_session() as session:
            try:
                users_data = [
                    {
                        "telegram_id": 123456789,
                        "username": "admin_user",
                        "first_name": "Admin",
                        "last_name": "User",
                        "is_admin": True
                    },
                    {
                        "telegram_id": 987654321,
                        "username": "test_user",
                        "first_name": "Test",
                        "last_name": "User"
                    }
                ]
                
                for user_data in users_data:
                    user = User(
                        **user_data,
                        join_date=datetime.now(),
                        last_activity=datetime.now()
                    )
                    session.add(user)
                
                await session.commit()
                logger.info("✅ تم إنشاء المستخدمين الافتراضيين بنجاح")
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ فشل في إنشاء المستخدمين: {str(e)}", exc_info=True)
                raise

    async def seed_user_settings(self):
        """تهيئة إعدادات المستخدمين"""
        async with await self._get_session() as session:
            try:
                result = await session.execute(select(User))
                users = result.scalars().all()
                
                for user in users:
                    settings = UserSettings(
                        user_id=user.id,
                        default_quality="best",
                        max_file_size=100 if user.is_admin else 50,
                        language="ar"
                    )
                    session.add(settings)
                
                await session.commit()
                logger.info("✅ تم تهيئة إعدادات المستخدمين بنجاح")
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ فشل في تهيئة الإعدادات: {str(e)}", exc_info=True)
                raise

    async def seed_sample_downloads(self):
        """إنشاء تحميلات تجريبية"""
        async with await self._get_session() as session:
            try:
                result = await session.execute(select(User))
                users = result.scalars().all()
                platforms = ["YouTube", "TikTok", "Instagram", "Twitter/X", "Facebook"]
                
                for user in users:
                    for _ in range(5):
                        download = Download(
                            user_id=user.id,
                            url=self.fake.url(),
                            platform=self.fake.random_element(platforms),
                            download_date=self.fake.date_time_this_year(),
                            file_size=self.fake.random_int(10, 500) * 1024 * 1024,
                            status="completed"
                        )
                        session.add(download)
                
                await session.commit()
                logger.info("✅ تم إنشاء التحميلات التجريبية بنجاح")
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ فشل في إنشاء التحميلات: {str(e)}", exc_info=True)
                raise

    async def seed_rewards_system(self):
        """تهيئة نظام النقاط والمكافآت"""
        async with await self._get_session() as session:
            try:
                result = await session.execute(select(User))
                users = result.scalars().all()
                
                for user in users:
                    points = UserPoints(
                        user_id=user.id,
                        points=self.fake.random_int(100, 1000),
                        last_daily_bonus=self.fake.date_this_year(),
                        streak_days=self.fake.random_int(1, 30)
                    )
                    session.add(points)
                    
                    # مكافآت مفعلة
                    for _ in range(2):
                        reward = ClaimedReward(
                            points_id=points.id,
                            reward_id=self.fake.random_element(list(config.REWARDS.keys())),
                            claim_date=self.fake.date_this_year(),
                            expiration_date=self.fake.future_date()
                        )
                        session.add(reward)
                
                await session.commit()
                logger.info("✅ تم تهيئة نظام النقاط بنجاح")
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ فشل في تهيئة النقاط: {str(e)}", exc_info=True)
                raise

    async def seed_system_logs(self):
        """إنشاء سجلات نظام تجريبية"""
        async with await self._get_session() as session:
            try:
                result = await session.execute(select(User))
                users = result.scalars().all()
                log_types = ["AUTH", "DOWNLOAD", "ERROR", "SETTINGS", "REWARD"]
                
                for _ in range(50):
                    log = SystemLog(
                        event_type=self.fake.random_element(log_types),
                        description=self.fake.sentence(),
                        user_id=self.fake.random_element([u.id for u in users]),
                        timestamp=self.fake.date_time_this_year()
                    )
                    session.add(log)
                
                await session.commit()
                logger.info("✅ تم إنشاء سجلات النظام بنجاح")
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ فشل في إنشاء السجلات: {str(e)}", exc_info=True)
                raise

    async def run_seeding(self):
        """تشغيل عملية التهيئة الكاملة"""
        try:
            logger.info("🚀 بدء عملية التهيئة...")
            
            # التحقق من وجود الجداول الأساسية
            async with async_engine.connect() as conn:
                inspector = await conn.run_sync(lambda conn: inspect(conn))
                required_tables = ['users', 'claimed_rewards']
                missing_tables = [tbl for tbl in required_tables if tbl not in inspector.get_table_names()]
                
                if missing_tables:
                    raise ValueError(f"جداول مفقودة: {', '.join(missing_tables)}")
            
            await self.clear_existing_data()
            await self.seed_default_users()
            await self.seed_user_settings()
            await self.seed_sample_downloads()
            await self.seed_rewards_system()
            await self.seed_system_logs()
            
            logger.info("🎉 تمت عملية التهيئة بنجاح")
        except Exception as e:
            logger.critical(f"💥 فشل في عملية التهيئة: {str(e)}", exc_info=True)
            raise

async def main():
    """الدالة الرئيسية لتنفيذ التهيئة"""
    try:
        from database import init_db
        await init_db()
        
        seeder = DatabaseSeeder()
        await seeder.run_seeding()
    except Exception as e:
        logger.critical(f"🔥 فشل تنفيذ السكريبت: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())