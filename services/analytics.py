import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import func, and_, case
from sqlalchemy.sql import label
from database.session import get_db
from database.models import Download, User, SystemLog, ClaimedReward, UserPoints
from config import config
from utils.logger import logger

class AnalyticsService:
    """خدمة تحليلات متكاملة لجمع وإدارة البيانات الإحصائية"""
    
    def __init__(self):
        self.db = next(get_db())
        self.time_ranges = {
            '24h': timedelta(hours=24),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30)
        }

    # ---------------------- تحليلات التحميلات ----------------------
    async def get_download_stats(self, time_range: str = '7d') -> Dict[str, Any]:
        """إحصائيات التحميلات حسب الفترة الزمنية"""
        try:
            time_delta = self._validate_time_range(time_range)
            start_date = datetime.now() - time_delta

            query = self.db.query(
                func.count(Download.id).label('total_downloads'),
                func.sum(Download.file_size).label('total_size'),
                func.avg(Download.file_size).label('avg_size'),
                func.avg(case((Download.status == 'completed', 1), else_=0)).label('success_rate')
            ).filter(Download.download_date >= start_date)

            result = query.first()
            
            return {
                "total_downloads": result.total_downloads or 0,
                "total_size": format_file_size(result.total_size) if result.total_size else "0 MB",
                "average_size": format_file_size(result.avg_size) if result.avg_size else "0 MB",
                "success_rate": f"{round(result.success_rate * 100, 2)}%" if result.success_rate else "0%",
                "time_range": time_range
            }

        except Exception as e:
            logger.error(f"Download stats error: {str(e)}")
            return {}

    async def get_platform_distribution(self) -> Dict[str, float]:
        """توزيع التحميلات حسب المنصة"""
        try:
            result = self.db.query(
                Download.platform,
                func.count(Download.id).label('count')
            ).group_by(Download.platform).all()
            
            total = sum(item.count for item in result)
            return {
                item.platform: round((item.count / total) * 100, 2)
                for item in result
            }
        except Exception as e:
            logger.error(f"Platform distribution error: {str(e)}")
            return {}

    # ---------------------- تحليلات المستخدمين ----------------------
    async def get_user_activity(self, user_id: int) -> Dict[str, Any]:
        """تحليل تفصيلي لنشاط مستخدم معين"""
        try:
            user = self.db.query(User).get(user_id)
            if not user:
                return {}

            last_week = datetime.now() - timedelta(days=7)
            
            activity = {
                "user_id": user_id,
                "total_downloads": user.total_downloads,
                "last_activity": user.last_activity.isoformat(),
                "favorite_platform": self._get_favorite_platform(user_id),
                "weekly_trend": self._get_weekly_activity(user_id, last_week),
                "storage_usage": self._calculate_storage_usage(user_id)
            }
            
            return activity
        except Exception as e:
            logger.error(f"User activity error: {str(e)}")
            return {}

    def _get_weekly_activity(self, user_id: int, start_date: datetime) -> Dict[str, int]:
        """النشاط الأسبوعي للمستخدم"""
        result = self.db.query(
            func.date_trunc('day', Download.download_date).label('date'),
            func.count(Download.id).label('count')
        ).filter(
            and_(
                Download.user_id == user_id,
                Download.download_date >= start_date
            )
        ).group_by('date').all()
        
        return {row.date.strftime('%Y-%m-%d'): row.count for row in result}

    # ---------------------- صحة النظام ----------------------
    async def get_system_health(self) -> Dict[str, Any]:
        """فحص شامل لصحة النظام"""
        try:
            stats = {
                "database": self._get_database_status(),
                "storage": self._get_storage_metrics(),
                "performance": await self._get_performance_metrics(),
                "active_users": self._get_active_users_count(),
                "error_rate": self._calculate_error_rate()
            }
            return stats
        except Exception as e:
            logger.error(f"System health error: {str(e)}")
            return {}

    def _get_database_status(self) -> Dict[str, Any]:
        """معلومات حالة قاعدة البيانات"""
        size = self.db.execute("SELECT pg_database_size(current_database())").scalar()
        return {
            "size": format_file_size(size),
            "connections": self.db.execute("SELECT numbackends FROM pg_stat_database WHERE datname=current_database()").scalar(),
            "last_vacuum": self.db.execute("SELECT last_vacuum FROM pg_stat_all_tables WHERE relname='downloads'").scalar()
        }

    # ---------------------- تحليلات المكافآت ----------------------
    async def get_reward_analytics(self) -> Dict[str, Any]:
        """تحليل أداء نظام المكافآت"""
        try:
            return {
                "popular_rewards": self._get_popular_rewards(),
                "user_distribution": self._get_points_distribution(),
                "redemption_rate": self._calculate_redemption_rate()
            }
        except Exception as e:
            logger.error(f"Reward analytics error: {str(e)}")
            return {}

    def _get_popular_rewards(self) -> List[Dict]:
        """المكافآت الأكثر شيوعًا"""
        result = self.db.query(
            ClaimedReward.reward_id,
            func.count(ClaimedReward.id).label('claims')
        ).group_by(ClaimedReward.reward_id).order_by(func.count(ClaimedReward.id).desc()).limit(5).all()
        
        return [{"reward_id": r.reward_id, "claims": r.claims} for r in result]

    # ---------------------- وظائف مساعدة ----------------------
    def _validate_time_range(self, time_range: str) -> timedelta:
        """التحقق من صحة الفترة الزمنية"""
        if time_range not in self.time_ranges:
            raise ValueError(f"فترة زمنية غير صالحة: {time_range}")
        return self.time_ranges[time_range]

    def _get_favorite_platform(self, user_id: int) -> Optional[str]:
        """المنصة المفضلة للمستخدم"""
        result = self.db.query(
            Download.platform,
            func.count(Download.id).label('count')
        ).filter(Download.user_id == user_id).group_by(Download.platform).order_by(func.count(Download.id).desc()).first()
        
        return result.platform if result else None

    def _calculate_storage_usage(self, user_id: int) -> Dict[str, str]:
        """حساب استخدام التخزين"""
        total = self.db.query(func.sum(Download.file_size)).filter(Download.user_id == user_id).scalar()
        return {
            "total": format_file_size(total) if total else "0 MB",
            "average": format_file_size(total/user.total_downloads) if user.total_downloads > 0 else "0 MB"
        }

    def _get_storage_metrics(self) -> Dict[str, Any]:
        """مقاييس التخزين الكلية"""
        total = self.db.query(func.sum(Download.file_size)).scalar()
        return {
            "total": format_file_size(total) if total else "0 MB",
            "daily_average": format_file_size(total/30) if total else "0 MB"  # متوسط 30 يوم
        }

    def _get_active_users_count(self) -> int:
        """عدد المستخدمين النشطين (نشط خلال 7 أيام)"""
        cutoff = datetime.now() - timedelta(days=7)
        return self.db.query(User).filter(User.last_activity >= cutoff).count()

    def _calculate_error_rate(self) -> float:
        """حساب معدل الأخطاء"""
        total = self.db.query(SystemLog).count()
        errors = self.db.query(SystemLog).filter(SystemLog.event_type == 'ERROR').count()
        return round((errors / total) * 100, 2) if total > 0 else 0.0

    def _get_points_distribution(self) -> Dict[str, float]:
        """توزيع النقاط بين المستخدمين"""
        quartiles = self.db.query(
            label('quartile', func.ntile(4).over(order_by=UserPoints.points)),
            func.avg(UserPoints.points).label('average')
        ).group_by('quartile').all()
        
        return {f"Q{q.quartile}": q.average for q in quartiles}

    def _calculate_redemption_rate(self) -> float:
        """معدل استبدال النقاط"""
        total_points = self.db.query(func.sum(UserPoints.points)).scalar()
        redeemed_points = self.db.query(func.sum(ClaimedReward.reward_id)).scalar()
        return round((redeemed_points / total_points) * 100, 2) if total_points > 0 else 0.0

# ===========================================================
# أمثلة استخدام:
if __name__ == "__main__":
    from database.session import init_db
    import asyncio
    
    async def test():
        await init_db()
        analytics = AnalyticsService()
        
        # إحصائيات التحميلات
        print("إحصائيات التحميلات:")
        print(await analytics.get_download_stats('7d'))
        
        # تحليل مستخدم
        print("\nتحليل المستخدم:")
        print(await analytics.get_user_activity(1))
        
        # صحة النظام
        print("\nصحة النظام:")
        print(await analytics.get_system_health())
        
        # تحليل المكافآت
        print("\nتحليل المكافآت:")
        print(await analytics.get_reward_analytics())
    
    asyncio.run(test())