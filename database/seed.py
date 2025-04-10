import logging
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy import select, inspect
from .session import AsyncSessionLocal, async_engine, using_sqlite
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

# إضافة دعم للمحركات المتزامنة وغير المتزامنة
if using_sqlite:
    from sqlalchemy.orm import Session as SessionType
else:
    from sqlalchemy.ext.asyncio import AsyncSession as SessionType


class DatabaseSeeder:
    """نظام تهيئة البيانات الأولية مع دعم كامل للـ Async و Sync"""
    
    def __init__(self):
        self.fake = Faker()
        self.default_password = "P@ssw0rd123!"

    async def _get_session(self) -> SessionType:
        """الحصول على جلسة قاعدة البيانات"""
        if using_sqlite:
            return AsyncSessionLocal()
        else:
            return AsyncSessionLocal()

    async def clear_existing_data(self):
        """حذف جميع البيانات الحالية"""
        session = await self._get_session()
        try:
            if using_sqlite:
                # منطق SQLite المتزامن
                inspector = inspect(async_engine)
                tables = inspector.get_table_names()
                
                # حذف البيانات من جميع الجداول
                for table in tables:
                    try:
                        session.execute(f"DELETE FROM {table}")
                        logger.info(f"تم حذف بيانات جدول {table}")
                    except Exception as e:
                        logger.warning(f"خطأ في حذف جدول {table}: {str(e)}")
                        session.rollback()
                
                session.commit()
            else:
                # منطق PostgreSQL غير المتزامن
                async with session as async_session:
                    # استخدام طريقة آمنة للحصول على أسماء الجداول
                    tables = []
                    async with async_engine.begin() as conn:
                        # استخدام run_sync لتنفيذ العمليات غير المتزامنة في سياق متزامن
                        tables_result = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
                        tables = tables_result
                    
                    # حذف البيانات من جميع الجداول
                    for table in tables:
                        try:
                            await async_session.execute(f"TRUNCATE TABLE {table} CASCADE")
                            logger.info(f"تم حذف بيانات جدول {table}")
                        except Exception as e:
                            logger.warning(f"خطأ في حذف جدول {table}: {str(e)}")
                            await async_session.rollback()
                    
                    await async_session.commit()
            
            logger.info("✅ تم حذف جميع البيانات بنجاح")
        except Exception as e:
            if using_sqlite:
                session.rollback()
            else:
                await session.rollback()
            logger.critical(f"❌ فشل في حذف البيانات: {str(e)}", exc_info=True)
            raise
        finally:
            if using_sqlite:
                session.close()

    async def seed_default_users(self):
        """إنشاء مستخدمين افتراضيين"""
        session = await self._get_session()
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
            
            if using_sqlite:
                # منطق SQLite المتزامن
                for user_data in users_data:
                    user = User(
                        **user_data,
                        join_date=datetime.now(),
                        last_activity=datetime.now()
                    )
                    session.add(user)
                
                session.commit()
            else:
                # منطق PostgreSQL غير المتزامن
                async with session as async_session:
                    for user_data in users_data:
                        user = User(
                            **user_data,
                            join_date=datetime.now(),
                            last_activity=datetime.now()
                        )
                        async_session.add(user)
                    
                    await async_session.commit()
            
            logger.info("✅ تم إنشاء المستخدمين الافتراضيين بنجاح")
        except Exception as e:
            if using_sqlite:
                session.rollback()
            else:
                await session.rollback()
            logger.error(f"❌ فشل في إنشاء المستخدمين: {str(e)}", exc_info=True)
            raise
        finally:
            if using_sqlite:
                session.close()

    async def seed_user_settings(self):
        """تهيئة إعدادات المستخدمين"""
        session = await self._get_session()
        try:
            if using_sqlite:
                # منطق SQLite المتزامن
                result = session.execute(select(User))
                users = result.scalars().all()
                
                for user in users:
                    settings = UserSettings(
                        user_id=user.id,
                        default_quality="best",
                        max_file_size=100 if user.is_admin else 50,
                        language="ar"
                    )
                    session.add(settings)
                
                session.commit()
            else:
                # منطق PostgreSQL غير المتزامن
                async with session as async_session:
                    result = await async_session.execute(select(User))
                    users = result.scalars().all()
                    
                    for user in users:
                        settings = UserSettings(
                            user_id=user.id,
                            default_quality="best",
                            max_file_size=100 if user.is_admin else 50,
                            language="ar"
                        )
                        async_session.add(settings)
                    
                    await async_session.commit()
            
            logger.info("✅ تم تهيئة إعدادات المستخدمين بنجاح")
        except Exception as e:
            if using_sqlite:
                session.rollback()
            else:
                await session.rollback()
            logger.error(f"❌ فشل في تهيئة الإعدادات: {str(e)}", exc_info=True)
            raise
        finally:
            if using_sqlite:
                session.close()

    async def seed_sample_downloads(self):
        """إنشاء تحميلات تجريبية"""
        session = await self._get_session()
        try:
            platforms = ["YouTube", "TikTok", "Instagram", "Twitter/X", "Facebook"]
            
            if using_sqlite:
                # منطق SQLite المتزامن
                result = session.execute(select(User))
                users = result.scalars().all()
                
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
                
                session.commit()
            else:
                # منطق PostgreSQL غير المتزامن
                async with session as async_session:
                    result = await async_session.execute(select(User))
                    users = result.scalars().all()
                    
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
                            async_session.add(download)
                    
                    await async_session.commit()
            
            logger.info("✅ تم إنشاء التحميلات التجريبية بنجاح")
        except Exception as e:
            if using_sqlite:
                session.rollback()
            else:
                await session.rollback()
            logger.error(f"❌ فشل في إنشاء التحميلات: {str(e)}", exc_info=True)
            raise
        finally:
            if using_sqlite:
                session.close()

    async def seed_rewards_system(self):
        """تهيئة نظام النقاط والمكافآت"""
        session = await self._get_session()
        try:
            if using_sqlite:
                # منطق SQLite المتزامن
                result = session.execute(select(User))
                users = result.scalars().all()
                
                for user in users:
                    points = UserPoints(
                        user_id=user.id,
                        points=self.fake.random_int(100, 1000),
                        last_daily_bonus=self.fake.date_this_year(),
                        streak_days=self.fake.random_int(1, 30)
                    )
                    session.add(points)
                    session.flush()  # للحصول على الـ ID
                    
                    # مكافآت مفعلة
                    for _ in range(2):
                        reward = ClaimedReward(
                            points_id=points.id,
                            reward_id=self.fake.random_element(list(config.REWARDS.keys())),
                            claim_date=self.fake.date_this_year(),
                            expiration_date=self.fake.future_date()
                        )
                        session.add(reward)
                
                session.commit()
            else:
                # منطق PostgreSQL غير المتزامن
                async with session as async_session:
                    result = await async_session.execute(select(User))
                    users = result.scalars().all()
                    
                    for user in users:
                        points = UserPoints(
                            user_id=user.id,
                            points=self.fake.random_int(100, 1000),
                            last_daily_bonus=self.fake.date_this_year(),
                            streak_days=self.fake.random_int(1, 30)
                        )
                        async_session.add(points)
                        await async_session.flush()  # للحصول على الـ ID
                        
                        # مكافآت مفعلة
                        for _ in range(2):
                            reward = ClaimedReward(
                                points_id=points.id,
                                reward_id=self.fake.random_element(list(config.REWARDS.keys())),
                                claim_date=self.fake.date_this_year(),
                                expiration_date=self.fake.future_date()
                            )
                            async_session.add(reward)
                    
                    await async_session.commit()
            
            logger.info("✅ تم تهيئة نظام النقاط بنجاح")
        except Exception as e:
            if using_sqlite:
                session.rollback()
            else:
                await session.rollback()
            logger.error(f"❌ فشل في تهيئة النقاط: {str(e)}", exc_info=True)
            raise
        finally:
            if using_sqlite:
                session.close()

    async def seed_system_logs(self):
        """إنشاء سجلات نظام تجريبية"""
        session = await self._get_session()
        try:
            log_types = ["AUTH", "DOWNLOAD", "ERROR", "SETTINGS", "REWARD"]
            
            if using_sqlite:
                # منطق SQLite المتزامن
                result = session.execute(select(User))
                users = result.scalars().all()
                
                for _ in range(50):
                    log = SystemLog(
                        event_type=self.fake.random_element(log_types),
                        description=self.fake.sentence(),
                        user_id=self.fake.random_element([u.id for u in users]),
                        timestamp=self.fake.date_time_this_year()
                    )
                    session.add(log)
                
                session.commit()
            else:
                # منطق PostgreSQL غير المتزامن
                async with session as async_session:
                    result = await async_session.execute(select(User))
                    users = result.scalars().all()
                    
                    for _ in range(50):
                        log = SystemLog(
                            event_type=self.fake.random_element(log_types),
                            description=self.fake.sentence(),
                            user_id=self.fake.random_element([u.id for u in users]),
                            timestamp=self.fake.date_time_this_year()
                        )
                        async_session.add(log)
                    
                    await async_session.commit()
            
            logger.info("✅ تم إنشاء سجلات النظام بنجاح")
        except Exception as e:
            if using_sqlite:
                session.rollback()
            else:
                await session.rollback()
            logger.error(f"❌ فشل في إنشاء السجلات: {str(e)}", exc_info=True)
            raise
        finally:
            if using_sqlite:
                session.close()

    async def run_seeding(self):
        """تشغيل عملية التهيئة الكاملة"""
        try:
            logger.info("🚀 بدء عملية التهيئة...")
            
            # التحقق من وجود الجداول الأساسية - تم تعديل هذا الجزء
            if using_sqlite:
                # منطق SQLite المتزامن
                inspector = inspect(async_engine)
                required_tables = ['users', 'claimed_rewards']
                missing_tables = [tbl for tbl in required_tables if tbl not in inspector.get_table_names()]
            else:
                # تعديل منطق PostgreSQL ليستخدم نهج متزامن آمن
                required_tables = ['users', 'claimed_rewards']
                missing_tables = []
                
                async with async_engine.begin() as conn:
                    # استخدام run_sync بدلاً من الاستدعاء المباشر لـ get_table_names
                    table_names = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
                    missing_tables = [tbl for tbl in required_tables if tbl not in table_names]
            
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