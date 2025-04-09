import logging
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from .session import SessionLocal
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
    """نظام تهيئة البيانات الأولية للقاعدة بيانات"""
    
    def __init__(self):
        self.fake = Faker()
        self.default_password = "P@ssw0rd123!"
        self.session = SessionLocal()
        self.inspector = inspect(self.session.bind)
        
    async def clear_existing_data(self):
        """حذف جميع البيانات الحالية مع التحقق من وجود الجداول"""
        try:
            tables = [
                ClaimedReward,
                UserPoints,
                Download,
                UserSettings,
                User,
                SystemLog
            ]
            
            for table in tables:
                try:
                    if not self.inspector.has_table(table.__tablename__):
                        logger.warning(f"الجدول {table.__tablename__} غير موجود - سيتم تخطيه")
                        continue
                        
                    deleted_count = self.session.query(table).delete()
                    logger.info(f"تم حذف {deleted_count} سجل من جدول {table.__tablename__}")
                except Exception as table_error:
                    logger.error(f"خطأ في حذف جدول {table.__tablename__}: {str(table_error)}", exc_info=True)
                    self.session.rollback()
            
            self.session.commit()
            logger.info("تم حذف البيانات الحالية بنجاح")
        except Exception as main_error:
            self.session.rollback()
            logger.critical(f"خطأ رئيسي في حذف البيانات: {str(main_error)}", exc_info=True)
            raise

    async def seed_default_users(self):
        """إنشاء مستخدمين افتراضيين"""
        try:
            if not self.inspector.has_table(User.__tablename__):
                raise ValueError(f"جدول {User.__tablename__} غير موجود")

            users = [
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
            
            for user_data in users:
                user = User(
                    **user_data,
                    join_date=datetime.now(),
                    last_activity=datetime.now()
                )
                self.session.add(user)
                
            self.session.commit()
            logger.info("تم إنشاء المستخدمين الافتراضيين بنجاح")
        except Exception as e:
            self.session.rollback()
            logger.error(f"خطأ في إنشاء المستخدمين: {str(e)}", exc_info=True)
            raise

    async def seed_user_settings(self):
        """تهيئة الإعدادات الافتراضية للمستخدمين"""
        try:
            if not all([self.inspector.has_table(t.__tablename__) for t in [User, UserSettings]]):
                raise ValueError("الجداول المطلوبة غير موجودة")

            users = self.session.query(User).all()
            for user in users:
                settings = UserSettings(
                    user_id=user.id,
                    default_quality="best",
                    max_file_size=100 if user.is_admin else 50,
                    language="ar"
                )
                self.session.add(settings)
                
            self.session.commit()
            logger.info("تم تهيئة إعدادات المستخدمين بنجاح")
        except Exception as e:
            self.session.rollback()
            logger.error(f"خطأ في تهيئة الإعدادات: {str(e)}", exc_info=True)
            raise

    async def seed_sample_downloads(self):
        """إنشاء تحميلات تجريبية"""
        try:
            if not all([self.inspector.has_table(t.__tablename__) for t in [User, Download]]):
                raise ValueError("الجداول المطلوبة غير موجودة")

            users = self.session.query(User).all()
            platforms = ["YouTube", "TikTok", "Instagram", "Twitter/X", "Facebook"]
            
            for user in users:
                for i in range(5):
                    download = Download(
                        user_id=user.id,
                        url=self.fake.url(),
                        platform=self.fake.random_element(platforms),
                        download_date=self.fake.date_time_this_year(),
                        file_size=self.fake.random_int(10, 500) * 1024 * 1024,
                        status="completed"
                    )
                    self.session.add(download)
                    
            self.session.commit()
            logger.info("تم إنشاء التحميلات التجريبية بنجاح")
        except Exception as e:
            self.session.rollback()
            logger.error(f"خطأ في إنشاء التحميلات: {str(e)}", exc_info=True)
            raise

    async def seed_rewards_system(self):
        """تهيئة نظام النقاط والمكافآت"""
        try:
            if not all([self.inspector.has_table(t.__tablename__) for t in [User, UserPoints, ClaimedReward]]):
                raise ValueError("الجداول المطلوبة غير موجودة")

            users = self.session.query(User).all()
            for user in users:
                points = UserPoints(
                    user_id=user.id,
                    points=self.fake.random_int(100, 1000),
                    last_daily_bonus=self.fake.date_this_year(),
                    streak_days=self.fake.random_int(1, 30)
                )
                self.session.add(points)
                
                # مكافآت مفعلة
                for _ in range(2):
                    reward = ClaimedReward(
                        points_id=points.id,
                        reward_id=self.fake.random_element(config.REWARDS.keys()),
                        claim_date=self.fake.date_this_year(),
                        expiration_date=self.fake.future_date()
                    )
                    self.session.add(reward)
                    
            self.session.commit()
            logger.info("تم تهيئة نظام النقاط بنجاح")
        except Exception as e:
            self.session.rollback()
            logger.error(f"خطأ في تهيئة النقاط: {str(e)}", exc_info=True)
            raise

    async def seed_system_logs(self):
        """إنشاء سجلات نظام تجريبية"""
        try:
            if not all([self.inspector.has_table(t.__tablename__) for t in [User, SystemLog]]):
                raise ValueError("الجداول المطلوبة غير موجودة")

            users = self.session.query(User).all()
            log_types = ["AUTH", "DOWNLOAD", "ERROR", "SETTINGS", "REWARD"]
            
            for _ in range(50):
                log = SystemLog(
                    event_type=self.fake.random_element(log_types),
                    description=self.fake.sentence(),
                    user_id=self.fake.random_element([u.id for u in users]),
                    timestamp=self.fake.date_time_this_year()
                )
                self.session.add(log)
                
            self.session.commit()
            logger.info("تم إنشاء سجلات النظام بنجاح")
        except Exception as e:
            self.session.rollback()
            logger.error(f"خطأ في إنشاء السجلات: {str(e)}", exc_info=True)
            raise

    async def run_seeding(self):
        """تشغيل عملية التهيئة الكاملة"""
        try:
            logger.info("بدء عملية التهيئة...")
            await self.clear_existing_data()
            await self.seed_default_users()
            await self.seed_user_settings()
            await self.seed_sample_downloads()
            await self.seed_rewards_system()
            await self.seed_system_logs()
            logger.info("✅ تمت عملية التهيئة بنجاح")
        except Exception as e:
            logger.critical(f"❌ فشل في عملية التهيئة: {str(e)}", exc_info=True)
            raise
        finally:
            self.session.close()

# استخدام الملف مباشرةً للتهيئة:
if __name__ == "__main__":
    import asyncio
    
    async def main():
        try:
            seeder = DatabaseSeeder()
            await seeder.run_seeding()
        except Exception as e:
            logger.critical(f"فشل في تنفيذ السكريبت: {str(e)}", exc_info=True)
            raise
    
    asyncio.run(main())