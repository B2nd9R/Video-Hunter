import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from database.session import get_db
from config import config
from utils.logger import logger

class RewardService:
    """نظام إدارة النقاط والمكافآت للمستخدمين"""
    
    def __init__(self):
        self.rewards = config.REWARDS

    async def get_user_points(self, user_id: int) -> int:
        """الحصول على رصيد النقاط للمستخدم"""
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT points FROM user_points WHERE user_id = ?",
                (user_id,)
            )
            result = cursor.fetchone()
            return result['points'] if result else 0

    async def add_points(self, user_id: int, points: int) -> int:
        """إضافة نقاط للمستخدم مع التحقق من الصحة"""
        if points <= 0:
            raise ValueError("يجب أن تكون النقاط أكبر من الصفر")
        
        with get_db() as conn:
            # التأكد من وجود سجل للمستخدم
            conn.execute(
                "INSERT OR IGNORE INTO user_points (user_id) VALUES (?)",
                (user_id,)
            )
            
            # إضافة النقاط
            conn.execute(
                "UPDATE user_points SET points = points + ? WHERE user_id = ?",
                (points, user_id)
            )
            
            conn.commit()
        
        new_balance = await self.get_user_points(user_id)
        logger.info(f"تمت إضافة {points} نقطة للمستخدم {user_id}. الرصيد الجديد: {new_balance}")
        return new_balance

    async def deduct_points(self, user_id: int, points: int) -> bool:
        """خصم النقاط مع التحقق من الرصيد المتاح"""
        current_balance = await self.get_user_points(user_id)
        
        if current_balance < points:
            logger.warning(f"محاولة خصم {points} نقطة من المستخدم {user_id} مع رصيد {current_balance} فقط")
            return False
        
        with get_db() as conn:
            conn.execute(
                "UPDATE user_points SET points = points - ? WHERE user_id = ?",
                (points, user_id)
            )
            conn.commit()
        
        logger.info(f"تم خصم {points} نقطة من المستخدم {user_id}")
        return True

    async def get_active_rewards(self, user_id: int) -> List[Dict[str, Any]]:
        """الحصول على المكافآت النشطة للمستخدم"""
        with get_db() as conn:
            cursor = conn.execute(
                """SELECT reward_id, claim_date, duration 
                FROM claimed_rewards 
                WHERE user_id = ? 
                AND date(claim_date, '+' || duration || ' days') >= date('now')""",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    async def claim_reward(self, user_id: int, reward_id: int) -> Dict[str, Any]:
        """استبدال النقاط بمكافأة"""
        if reward_id not in self.rewards:
            raise ValueError("هذه المكافأة غير متاحة")
        
        reward = self.rewards[reward_id]
        current_points = await self.get_user_points(user_id)
        
        if current_points < reward_id:
            raise ValueError(f"نقاطك غير كافية. تحتاج {reward_id} نقطة")
        
        # خصم النقاط
        if not await self.deduct_points(user_id, reward_id):
            raise ValueError("فشل في خصم النقاط")
        
        # تسجيل المكافأة
        expiry_date = datetime.now() + timedelta(days=reward['duration'])
        with get_db() as conn:
            conn.execute(
                """INSERT INTO claimed_rewards 
                (user_id, reward_id, claim_date, duration) 
                VALUES (?, ?, ?, ?)""",
                (user_id, reward_id, datetime.now(), reward['duration'])
            )
            conn.commit()
        
        logger.info(f"المستخدم {user_id} قام بشراء مكافأة {reward['name']}")
        
        return {
            'reward_name': reward['name'],
            'expiry_date': expiry_date.strftime('%Y-%m-%d'),
            'remaining_points': await self.get_user_points(user_id)
        }

    async def get_daily_bonus(self, user_id: int) -> Dict[str, Any]:
        """الحصول على المكافأة اليومية مع تتبع التسلسل"""
        with get_db() as conn:
            user_data = conn.execute(
                "SELECT last_daily_bonus, streak_count FROM user_points WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            today = datetime.now().date()
            last_bonus = datetime.strptime(user_data['last_daily_bonus'], '%Y-%m-%d').date() if user_data and user_data['last_daily_bonus'] else None
            streak = user_data['streak_count'] if user_data else 0
            
            # حساب النقاط بناء على التسلسل
            if last_bonus == today:
                return {'status': 'already_claimed', 'points': 0}
                
            if last_bonus and (today - last_bonus).days == 1:
                streak += 1
            else:
                streak = 1
                
            points = 5 + (streak * 2)  # 5 نقاط أساسية + 2 لكل يوم متتالي
            
            # تحديث البيانات
            conn.execute(
                """UPDATE user_points 
                SET points = points + ?, 
                    last_daily_bonus = ?, 
                    streak_count = ? 
                WHERE user_id = ?""",
                (points, today.isoformat(), streak, user_id)
            )
            conn.commit()
            
            return {
                'status': 'success',
                'points': points,
                'streak': streak,
                'next_bonus': (today + timedelta(days=1)).isoformat()
            }

# إنشاء نسخة وحيدة من الخدمة لاستخدامها في التطبيق
reward_service = RewardService()

# واجهات للاستيراد المباشر
async def get_user_points(*args, **kwargs):
    return await reward_service.get_user_points(*args, **kwargs)

async def get_active_rewards(*args, **kwargs):
    return await reward_service.get_active_rewards(*args, **kwargs)

async def claim_reward(*args, **kwargs):
    return await reward_service.claim_reward(*args, **kwargs)