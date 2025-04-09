import os
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from tempfile import NamedTemporaryFile
from config import config
from utils.helpers import format_file_size, clean_filename
from utils.logger import logger
from utils.validators import validate_video_file

class VideoProcessor:
    """فئة متقدمة لمعالجة الفيديو بجميع عملياته الأساسية"""
    
    def __init__(self):
        self.temp_dir = Path("temp_videos")
        self.temp_dir.mkdir(exist_ok=True)
        self.supported_formats = ['mp4', 'avi', 'mkv', 'mov', 'webm']
        self.max_retries = 3

    async def convert_format(
        self,
        input_path: str,
        output_format: str = 'mp4',
        resolution: Optional[Tuple[int, int]] = None
    ) -> Optional[str]:
        """
        تحويل تنسيق الفيديو مع إمكانية تغيير الدقة
        Args:
            input_path: مسار الملف المدخل
            output_format: صيغة المخرجات المطلوبة (default: mp4)
            resolution: تغيير الدقة (عرض, ارتفاع)
        Returns:
            مسار الملف الناتج أو None في حالة الفشل
        """
        try:
            if not validate_video_file(input_path):
                raise ValueError("ملف الفيديو غير صالح")

            output_path = self.temp_dir / f"{Path(input_path).stem}.{output_format}"
            
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-strict', 'experimental'
            ]

            if resolution:
                cmd += ['-vf', f'scale={resolution[0]}:{resolution[1]}']

            cmd.append(str(output_path))

            result = await self._run_command(cmd)
            if result:
                logger.info(f"تم التحويل بنجاح إلى {output_format}")
                return str(output_path)
            return None

        except Exception as e:
            logger.error(f"خطأ في التحويل: {str(e)}")
            return None

    async def compress_video(
        self,
        input_path: str,
        target_size_mb: float,
        crf_quality: int = 28
    ) -> Optional[str]:
        """
        ضغط الفيديو مع الحفاظ على الجودة
        Args:
            input_path: مسار الملف المدخل
            target_size_mb: الحجم المستهدف بالميجابايت
            crf_quality: جودة الضغط (23-28 جيد، 29-35 متوسط)
        Returns:
            مسار الملف المضغوط أو None
        """
        try:
            duration = float(subprocess.check_output([
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                input_path
            ]).decode().strip())

            target_bits = (target_size_mb * 8 * 1024 * 1024) / duration
            bitrate = f"{target_bits / 1024:.2f}k"

            output_path = self.temp_dir / f"compressed_{Path(input_path).name}"

            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx264',
                '-b:v', bitrate,
                '-maxrate', bitrate,
                '-bufsize', f'{bitrate}*2',
                '-crf', str(crf_quality),
                '-c:a', 'copy',
                '-y', str(output_path)
            ]

            result = await self._run_command(cmd)
            return str(output_path) if result else None

        except Exception as e:
            logger.error(f"خطأ في الضغط: {str(e)}")
            return None

    async def add_watermark(
        self,
        input_path: str,
        watermark_text: str,
        position: str = 'bottom-right'
    ) -> Optional[str]:
        """
        إضافة علامة مائية نصية للفيديو
        Args:
            input_path: مسار الفيديو
            watermark_text: النص المراد إضافته
            position: موقع العلامة (top-left, top-right, bottom-left, bottom-right)
        Returns:
            مسار الفيديو المعدل أو None
        """
        try:
            position_map = {
                'top-left': '10:10',
                'top-right': 'main_w-text_w-10:10',
                'bottom-left': '10:main_h-text_h-10',
                'bottom-right': 'main_w-text_w-10:main_h-text_h-10'
            }

            output_path = self.temp_dir / f"watermarked_{Path(input_path).name}"

            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vf', f"drawtext=text='{watermark_text}':"
                       f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                       f"fontsize=24:fontcolor=white@0.5:"
                       f"box=1:boxcolor=black@0.5:"
                       f"x={position_map[position]}:y={position_map[position].split(':')[1]}",
                '-codec:a', 'copy',
                '-y', str(output_path)
            ]

            result = await self._run_command(cmd)
            return str(output_path) if result else None

        except Exception as e:
            logger.error(f"خطأ في إضافة العلامة المائية: {str(e)}")
            return None

    async def extract_audio(
        self,
        input_path: str,
        output_format: str = 'mp3'
    ) -> Optional[str]:
        """
        استخراج الصوت من الفيديو
        Args:
            input_path: مسار الفيديو
            output_format: صيغة الصوت المطلوبة (mp3, wav, aac)
        Returns:
            مسار ملف الصوت أو None
        """
        try:
            output_path = self.temp_dir / f"{Path(input_path).stem}.{output_format}"
            
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vn',
                '-acodec', 'libmp3lame' if output_format == 'mp3' else 'pcm_s16le',
                '-ar', '44100',
                '-ac', '2',
                '-ab', '192k',
                '-f', output_format,
                '-y', str(output_path)
            ]

            result = await self._run_command(cmd)
            return str(output_path) if result else None

        except Exception as e:
            logger.error(f"خطأ في استخراج الصوت: {str(e)}")
            return None

    async def _run_command(self, command: list, timeout: int = 600) -> bool:
        """تنفيذ أوامر FFmpeg مع إدارة الأخطاء"""
        for attempt in range(self.max_retries):
            try:
                result = subprocess.run(
                    command,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout
                )
                if result.returncode == 0:
                    return True
                logger.error(f"FFmpeg error: {result.stderr.decode()}")
            except subprocess.TimeoutExpired:
                logger.error("انتهى الوقت المخصص للمعالجة")
            except Exception as e:
                logger.error(f"Attempt {attempt+1} failed: {str(e)}")
        
        return False

    async def cleanup_temp_files(self, file_path: str) -> None:
        """تنظيف الملفات المؤقتة"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"تم حذف الملف المؤقت: {file_path}")
        except Exception as e:
            logger.error(f"خطأ في تنظيف الملفات: {str(e)}")

# مثال للاستخدام:
if __name__ == "__main__":
    import asyncio
    
    async def test_processing():
        processor = VideoProcessor()
        
        # تحويل الفيديو
        converted = await processor.convert_format("input.avi", resolution=(1280, 720))
        if converted:
            print(f"تم التحويل إلى: {converted}")
        
        # ضغط الفيديو
        compressed = await processor.compress_video(converted, 25)
        if compressed:
            print(f"الملف المضغوط: {compressed}")
        
        # تنظيف الملفات
        await processor.cleanup_temp_files(converted)
        await processor.cleanup_temp_files(compressed)
    
    asyncio.run(test_processing())