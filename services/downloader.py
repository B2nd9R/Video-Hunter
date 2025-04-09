import os
import re
import logging
import yt_dlp
import subprocess
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from config import config
from utils.helpers import format_file_size
from utils.logger import logger
from database.session import get_db

class VideoDownloader:
    """فئة مسؤولة عن تحميل ومعالجة الفيديوهات من مختلف المنصات"""
    
    def __init__(self):
        self.temp_dir = Path("temp")
        self.temp_dir.mkdir(exist_ok=True)
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'force_ipv4': True,
            'outtmpl': str(self.temp_dir / '%(id)s.%(ext)s'),
        }

    async def clean_url(self, url: str) -> str:
        """تنظيف الروابط من المعاملات الإضافية"""
        return url.split('?')[0].split('&')[0]

    async def validate_url(self, url: str) -> bool:
        """التحقق من صحة الرابط ودعم المنصة"""
        cleaned_url = await self.clean_url(url)
        return any(re.match(pattern, cleaned_url) for pattern in config.SUPPORTED_PATTERNS)

    async def get_platform(self, url: str) -> str:
        """تحديد المنصة من الرابط"""
        domain = urlparse(url).netloc.lower()
        if 'youtube' in domain or 'youtu.be' in domain:
            return 'YouTube'
        elif 'tiktok' in domain:
            return 'TikTok'
        elif 'instagram' in domain:
            return 'Instagram'
        elif 'twitter' in domain or 'x.com' in domain:
            return 'Twitter/X'
        elif 'facebook' in domain:
            return 'Facebook'
        return 'Other'

    async def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """الحصول على معلومات الفيديو بدون تحميل"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Untitled'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'filesize': info.get('filesize_approx', 0),
                    'formats': info.get('formats', []),
                    'resolution': self._get_best_resolution(info),
                    'ext': info.get('ext', 'mp4')
                }
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return None

    def _get_best_resolution(self, info: Dict[str, Any]) -> str:
        """الحصول على أفضل دقة متاحة"""
        formats = info.get('formats', [])
        if not formats:
            return 'Unknown'
        
        resolutions = [f.get('resolution') for f in formats if f.get('vcodec') != 'none']
        return max(resolutions, key=lambda x: int(x.split('x')[1]) if resolutions else 'Unknown')

    async def download_with_ytdlp(self, url: str, quality: str = 'best') -> Optional[str]:
        """تحميل الفيديو باستخدام yt-dlp"""
        opts = {**self.ydl_opts, 'format': self._get_quality_format(quality)}
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filepath = ydl.prepare_filename(info)
                
                # تسجيل التحميل في قاعدة البيانات
                await self._log_download(
                    user_id=None,  # سيتم تعبئته عند الاستدعاء
                    url=url,
                    platform=await self.get_platform(url),
                    file_size=os.path.getsize(filepath)
                )
                return filepath
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None

    def _get_quality_format(self, quality: str) -> str:
        """تحديد تنسيق الجودة المطلوبة"""
        quality_map = {
            'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'medium': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'low': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        }
        return quality_map.get(quality, quality_map['best'])

    async def download_twitter_video(self, url: str) -> Optional[str]:
        """تحميل فيديو من تويتر مع معالجة خاصة"""
        opts = {
            **self.ydl_opts,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://twitter.com/'
            }
        }
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        except Exception as e:
            logger.error(f"Twitter download failed: {e}")
            return None

    async def convert_to_mp4(self, input_path: str) -> Optional[str]:
        """تحويل الفيديو إلى صيغة MP4"""
        output_path = Path(input_path).with_suffix('.mp4')
        
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libx264', '-preset', 'fast',
            '-c:a', 'aac', '-strict', 'experimental',
            '-y', str(output_path)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return str(output_path)
        except subprocess.CalledProcessError as e:
            logger.error(f"Conversion failed: {e.stderr.decode()}")
            return None

    async def compress_video(self, input_path: str, target_size_mb: int) -> Optional[str]:
        """ضغط الفيديو لتقليل حجمه"""
        output_path = Path(input_path).with_stem(f"{Path(input_path).stem}_compressed")
        
        # حساب معدل البت المطلوب
        duration = float(subprocess.run([
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_path
        ], capture_output=True, text=True).stdout)
        
        target_bits = target_size_mb * 8 * 1024 * 1024
        bitrate = int(target_bits / duration / 1024)  # كيلوبت في الثانية
        
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libx264', '-preset', 'slow',
            '-b:v', f'{bitrate}k', '-maxrate', f'{bitrate}k',
            '-bufsize', f'{bitrate * 2}k',
            '-c:a', 'aac', '-b:a', '128k',
            '-y', str(output_path)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return str(output_path)
        except subprocess.CalledProcessError as e:
            logger.error(f"Compression failed: {e.stderr.decode()}")
            return None

    async def _log_download(self, user_id: int, url: str, platform: str, file_size: int):
        """تسجيل عملية التحميل في قاعدة البيانات"""
        with get_db() as conn:
            conn.execute(
                """INSERT INTO downloads 
                (user_id, url, platform, download_date, file_size) 
                VALUES (?, ?, ?, ?, ?)""",
                (user_id, url, platform, datetime.now(), file_size)
            )
            conn.commit()

# إنشاء نسخة واحدة من Downloader لاستخدامها في جميع أنحاء التطبيق
downloader = VideoDownloader()

# واجهات الدوال للاستيراد المباشر
async def download_video(*args, **kwargs):
    return await downloader.download_with_ytdlp(*args, **kwargs)

async def get_video_info(*args, **kwargs):
    return await downloader.get_video_info(*args, **kwargs)

async def clean_url(*args, **kwargs):
    return await downloader.clean_url(*args, **kwargs)

async def compress_video(*args, **kwargs):
    return await downloader.compress_video(*args, **kwargs)