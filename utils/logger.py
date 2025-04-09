import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import func, and_
from database.session import get_db
from database.models import ClaimedReward, Download, User, SystemLog, UserPoints
from utils.logger import logger

class AnalyticsService:
    """خدمة متقدمة لتحليل بيانات التطبيق"""
    
    def __init__(self):
        self.db = next(get_db())

    async def get_download_stats(self, days: int = 7) -> Dict[str, Any]:
        """إحصائيات التحميلات خلال فترة محددة"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # إحصائيات عامة
            total_downloads = self.db.query(func.count(Download.id)).filter(
                Download.download_date >= start_date
            ).scalar()
            
            # التحميلات حسب المنصة
            by_platform = self.db.query(
                Download.platform,
                func.count(Download.id)
            ).filter(
                Download.download_date >= start_date
            ).group_by(Download.platform).all()
            
            # التحميلات الناجحة مقابل الفاشلة
            success_rate = self.db.query(
                func.avg(func.cast(Download.status == 'completed', Integer))
            ).filter(
                Download.download_date >= start_date
            ).scalar()
            
            return {
                "total_downloads": total_downloads,
                "platform_distribution": dict(by_platform),
                "success_rate": round(success_rate * 100, 2) if success_rate else 0,
                "time_period": f"آخر {days} أيام"
            }
            
        except Exception as e:
            logger.error(f"خطأ في جمع إحصائيات التحميلات: {str(e)}")
            return {}

    async def get_user_activity(self, user_id: int) -> Dict[str, Any]:
        """تحليل نشاط مستخدم معين"""
        try:
            user = self.db.query(User).get(user_id)
            if not user:
                return {}
            
            # النشاط الأخير
            last_activity = self.db.query(func.max(Download.download_date)).filter(
                Download.user_id == user_id
            ).scalar()
            
            # متوسط حجم التحميلات
            avg_size = self.db.query(func.avg(Download.file_size)).filter(
                Download.user_id == user_id
            ).scalar()
            
            return {
                "user_id": user_id,
                "total_downloads": user.total_downloads,
                "last_activity": last_activity,
                "average_size": round(avg_size / (1024*1024), 2) if avg_size else 0,
                "favorite_platform": self._get_favorite_platform(user_id)
            }
        except Exception as e:
            logger.error(f"خطأ في تحليل نشاط المستخدم: {str(e)}")
            return {}

    def _get_favorite_platform(self, user_id: int) -> Optional[str]:
        """الحصول على المنصة المفضلة للمستخدم"""
        result = self.db.query(
            Download.platform,
            func.count(Download.id).label('count')
        ).filter(
            Download.user_id == user_id
        ).group_by(Download.platform).order_by(func.count(Download.id).desc()).first()
        
        return result[0] if result else None

    async def get_system_health(self) -> Dict[str, Any]:
        """فحص صحة النظام العام"""
        try:
            # إحصائيات الأخطاء
            error_logs = self.db.query(SystemLog).filter(
                SystemLog.event_type == 'ERROR'
            ).count()
            
            # معدل الاستخدام
            active_users = self.db.query(User).filter(
                User.last_activity >= datetime.now() - timedelta(days=1)
            ).count()
            
            return {
                "total_users": self.db.query(User).count(),
                "active_users_last_24h": active_users,
                "error_rate_last_7d": error_logs,
                "database_size": self._get_database_size()
            }
        except Exception as e:
            logger.error(f"خطأ في فحص صحة النظام: {str(e)}")
            return {}

    def _get_database_size(self) -> str:
        """تقدير حجم قاعدة البيانات"""
        size_bytes = self.db.execute(
            "SELECT pg_database_size(current_database())"
        ).scalar()
        
        # تحويل إلى تنسيق مقروء
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} GB"

    async def get_rewards_analytics(self) -> Dict[str, Any]:
        """تحليل بيانات نظام المكافآت"""
        try:
            # المكافآت الأكثر شيوعاً
            popular_rewards = self.db.query(
                ClaimedReward.reward_id,
                func.count(ClaimedReward.id).label('total_claims')
            ).group_by(ClaimedReward.reward_id).order_by(func.count(ClaimedReward.id).desc()).limit(5).all()
            
            # توزيع النقاط
            points_distribution = self.db.query(
                func.ntile(4).over(order_by=UserPoints.points).label('quartile'),
                func.avg(UserPoints.points)
            ).group_by('quartile').all()
            
            return {
                "most_popular_rewards": [
                    {"reward_id": r[0], "claims": r[1]} for r in popular_rewards
                ],
                "points_distribution": [
                    {"quartile": q[0], "average_points": q[1]} for q in points_distribution
                ]
            }
        except Exception as e:
            logger.error(f"خطأ في تحليل المكافآت: {str(e)}")
            return {}

# مثال للاستخدام:
if __name__ == "__main__":
    analytics = AnalyticsService()
    
    # الحصول على إحصائيات التحميلات
    print(analytics.get_download_stats())
    
    # تحليل نشاط المستخدم
    print(analytics.get_user_activity(1))
    
    # فحص صحة النظام
    print(analytics.get_system_health())