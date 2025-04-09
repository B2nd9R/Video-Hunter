import logging
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session
from .session import SessionLocal, get_sqlalchemy_db
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
        
    async def clear_existing_data(self):
        """حذف جميع البيانات الحالية"""
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
                self.session.query(table).delete()
                
            self.session.commit()
            logger.info("تم حذف البيانات الحالية بنجاح")
        except Exception as e:
            self.session.rollback()
            logger.error(f"خطأ في حذف البيانات: {str(e)}")
            raise

    async def seed_default_users(self):
        """إنشاء مستخدمين افتراضيين"""
        try:
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
            logger.error(f"خطأ في إنشاء المستخدمين: {str(e)}")
            raise

    async def seed_user_settings(self):
        """تهيئة الإعدادات الافتراضية للمستخدمين"""
        try:
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
            logger.error(f"خطأ في تهيئة الإعدادات: {str(e)}")
            raise

    async def seed_sample_downloads(self):
        """إنشاء تحميلات تجريبية"""
        try:
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
            logger.error(f"خطأ في إنشاء التحميلات: {str(e)}")
            raise

    async def seed_rewards_system(self):
        """تهيئة نظام النقاط والمكافآت"""
        try:
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
            logger.error(f"خطأ في تهيئة النقاط: {str(e)}")
            raise

    async def seed_system_logs(self):
        """إنشاء سجلات نظام تجريبية"""
        try:
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
            logger.error(f"خطأ في إنشاء السجلات: {str(e)}")
            raise

    async def run_seeding(self):
        """تشغيل عملية التهيئة الكاملة"""
        try:
            await self.clear_existing_data()
            await self.seed_default_users()
            await self.seed_user_settings()
            await self.seed_sample_downloads()
            await self.seed_rewards_system()
            await self.seed_system_logs()
            logger.info("تمت عملية التهيئة بنجاح 🎉")
        except Exception as e:
            logger.critical(f"فشل في عملية التهيئة: {str(e)}")
            raise
        finally:
            self.session.close()

# -----------------------------------------------------------
# استخدام الملف مباشرةً للتهيئة:
if __name__ == "__main__":
    import asyncio
    
    async def main():
        seeder = DatabaseSeeder()
        await seeder.run_seeding()
    
    asyncio.run(main())

# -----------------------------------------------------------
# استخدام الملف في التطبيق الرئيسي:
# from database.seed import DatabaseSeeder
# 
# async def initialize_data():
#     seeder = DatabaseSeeder()
#     await seeder.run_seeding()