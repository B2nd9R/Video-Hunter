from sqlalchemy.orm import Session
from . import models

def create_user(db: Session, telegram_user):
    db_user = models.User(
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # إنشاء السجلات المرتبطة
    db_settings = models.UserSettings(user_id=db_user.id)
    db_points = models.UserPoints(user_id=db_user.id)
    db_statistics = models.UserStatistics(user_id=db_user.id)
    
    db.add_all([db_settings, db_points, db_statistics])
    db.commit()
    return db_user

def log_download(db: Session, user_id: int, url: str, platform: str, file_size: float):
    # إيجاد أو إنشاء المنصة
    platform_obj = db.query(models.Platform).filter_by(name=platform).first()
    if not platform_obj:
        platform_obj = models.Platform(name=platform, domain_pattern=f"%{platform}%")
        db.add(platform_obj)
        db.commit()
    
    download = models.Download(
        user_id=user_id,
        url=url,
        platform_id=platform_obj.id,
        file_size=file_size,
        status='completed'
    )
    db.add(download)
    
    # تحديث الإحصائيات
    stats = db.query(models.UserStatistics).filter_by(user_id=user_id).first()
    stats.total_downloads += 1
    stats.total_storage += file_size
    stats.last_download = download.download_date
    
    db.commit()
    return download

def add_points(db: Session, user_id: int, points: int):
    user_points = db.query(models.UserPoints).filter_by(user_id=user_id).first()
    user_points.balance += points
    user_points.last_earned = datetime.utcnow()
    db.commit()
    return user_points