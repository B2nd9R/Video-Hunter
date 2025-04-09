from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database.base import Base

class User(Base):
    """نموذج مستخدم البوت"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(50))
    first_name = Column(String(100))
    last_name = Column(String(100))
    join_date = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)
    
    # العلاقات
    settings = relationship("UserSettings", uselist=False, back_populates="user")
    downloads = relationship("Download", back_populates="user")
    points = relationship("UserPoints", uselist=False, back_populates="user")

class UserSettings(Base):
    """إعدادات المستخدم المخصصة"""
    __tablename__ = 'user_settings'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    default_quality = Column(String(20), default='best')
    max_file_size = Column(Integer, default=50)  # بال megabytes
    language = Column(String(10), default='ar')
    notifications_enabled = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="settings")

class Download(Base):
    """سجل تحميلات المستخدم"""
    __tablename__ = 'downloads'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    url = Column(String(500), nullable=False)
    platform = Column(String(50))
    download_date = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Float)  # بال megabytes
    status = Column(String(20), default='pending')
    
    user = relationship("User", back_populates="downloads")

class UserPoints(Base):
    """نظام نقاط المستخدم"""
    __tablename__ = 'user_points'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    points = Column(Integer, default=0)
    last_daily_bonus = Column(DateTime)
    streak_days = Column(Integer, default=0)
    
    user = relationship("User", back_populates="points")
    claimed_rewards = relationship("ClaimedReward", back_populates="user_points")

class ClaimedReward(Base):
    """المكافآت التي قام المستخدم بشرائها"""
    __tablename__ = 'claimed_rewards'
    
    id = Column(Integer, primary_key=True)
    points_id = Column(Integer, ForeignKey('user_points.id'))
    reward_id = Column(Integer, nullable=False)
    claim_date = Column(DateTime, default=datetime.utcnow)
    expiration_date = Column(DateTime)
    
    user_points = relationship("UserPoints", back_populates="claimed_rewards")

class SystemLog(Base):
    """سجل أحداث النظام"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    event_type = Column(String(50), nullable=False)
    description = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'))
    
    user = relationship("User")