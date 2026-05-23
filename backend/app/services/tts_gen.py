import os
import logging
import edge_tts
from pathlib import Path
from moviepy import AudioFileClip

logger = logging.getLogger(__name__)

# Danh sách một số giọng đọc tiếng Việt chất lượng từ Edge-TTS:
# vi-VN-HoaiMyNeural (Nữ)
# vi-VN-NamMinhNeural (Nam)
DEFAULT_VOICE = "vi-VN-HoaiMyNeural"

class TTSGenerator:
    async def generate_voice(self, text: str, output_path: Path, voice: str = DEFAULT_VOICE) -> float:
        """
        Tạo giọng đọc từ văn bản sử dụng edge-tts và lưu dưới dạng file mp3.
        Trả về thời lượng (duration) của file âm thanh (tính bằng giây).
        """
        # Đảm bảo thư mục cha tồn tại
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Đang tạo giọng đọc cho văn bản (độ dài {len(text)} ký tự) bằng giọng {voice}...")
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))
            
            # Tính toán thời lượng file audio sử dụng MoviePy AudioFileClip
            audio_clip = AudioFileClip(str(output_path))
            duration = audio_clip.duration
            audio_clip.close()
            
            logger.info(f"Đã tạo xong file âm thanh: {output_path}, thời lượng: {duration:.2f}s")
            return duration
            
        except Exception as e:
            logger.error(f"Lỗi trong quá trình tạo giọng đọc Edge-TTS: {str(e)}")
            # Trả về thời lượng giả lập dựa trên tốc độ nói trung bình (khoảng 3 từ/giây)
            words_count = len(text.split())
            fallback_duration = max(2.0, words_count / 2.5)
            logger.warning(f"Sử dụng thời lượng giả lập fallback: {fallback_duration:.2f}s")
            
            # Tạo file audio câm dài fallback_duration để tránh lỗi crash FFmpeg
            self._create_silence_mp3(fallback_duration, output_path)
            return fallback_duration

    def _create_silence_mp3(self, duration: float, output_path: Path):
        """Tạo file mp3 câm bằng FFmpeg phòng trường hợp lỗi mạng hoặc lỗi API."""
        try:
            import subprocess
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "anullsrc=r=22050:c=1",
                "-t", f"{duration:.2f}",
                str(output_path)
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logger.info(f"Đã tạo file audio câm fallback dài {duration:.2f}s tại {output_path}")
        except Exception as e:
            logger.error(f"Không thể tạo file audio câm bằng FFmpeg: {str(e)}")

tts_generator = TTSGenerator()
