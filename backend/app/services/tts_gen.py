import os
import logging
import edge_tts
import wave
import struct
import asyncio
import subprocess
import unicodedata
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
        Có cơ chế thử lại (retry) lên đến 3 lần với exponential backoff nếu gặp lỗi mạng/rate limit.
        Trả về thời lượng (duration) của file âm thanh (tính bằng giây).
        """
        # Đảm bảo thư mục cha tồn tại
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Chuẩn hóa văn bản tiếng Việt sang dạng dựng sẵn (NFC) để tránh lỗi phát âm/mã hóa trên Windows và Edge-TTS API
        if text:
            text = unicodedata.normalize('NFC', text)
            # Loại bỏ các ký tự điều khiển không in được (ngoại trừ xuống dòng và tab)
            text = "".join(ch for ch in text if ch.isprintable() or ch in '\n\r\t').strip()
        else:
            text = ""

        max_retries = 3
        retry_delay = 1.0  # giây
        
        for attempt in range(1, max_retries + 1):
            try:
                try:
                    logger.info(f"Đang tạo giọng đọc cho văn bản (độ dài {len(text)} ký tự) bằng giọng {voice} (Lần thử {attempt}/{max_retries})...")
                except UnicodeEncodeError:
                    logger.info(f"Dang tao giong doc cho van ban (do dai {len(text)} ky tu) bang giong {voice} (Lan thu {attempt}/{max_retries})...")
                
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(str(output_path))
                
                # Tính toán thời lượng file audio sử dụng MoviePy AudioFileClip
                audio_clip = AudioFileClip(str(output_path))
                duration = audio_clip.duration
                audio_clip.close()
                
                try:
                    logger.info(f"Đã tạo xong file âm thanh: {output_path}, thời lượng: {duration:.2f}s")
                except UnicodeEncodeError:
                    logger.info(f"Da tao xong file am thanh: {output_path.name}, thoi luong: {duration:.2f}s")
                return duration
                
            except Exception as e:
                err_msg = str(e)
                try:
                    logger.warning(f"Lỗi khi gọi API edge-tts lần thử {attempt}: {err_msg}")
                except UnicodeEncodeError:
                    logger.warning(f"Loi khi goi API edge-tts lan thu {attempt}: {err_msg.encode('ascii', 'replace').decode('ascii')}")
                
                if attempt < max_retries:
                    try:
                        logger.info(f"Thử lại sau {retry_delay} giây...")
                    except UnicodeEncodeError:
                        logger.info(f"Thu lai sau {retry_delay} giay...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2.0  # Exponential backoff
                else:
                    try:
                        logger.error(f"Đã thất bại sau {max_retries} lần thử gọi API edge-tts. Tiến hành tạo file audio câm fallback.")
                    except UnicodeEncodeError:
                        logger.error(f"Da that bai sau {max_retries} lan thu goi API edge-tts. Tien hanh tao file audio cam fallback.")
                    
                    # Tính toán thời lượng giả lập dựa trên tốc độ nói trung bình (khoảng 2.5 từ/giây)
                    words_count = len(text.split())
                    fallback_duration = max(2.0, words_count / 2.5)
                    try:
                        logger.warning(f"Sử dụng thời lượng giả lập fallback: {fallback_duration:.2f}s")
                    except UnicodeEncodeError:
                        logger.warning(f"Su dung thoi luong gia lap fallback: {fallback_duration:.2f}s")
                    
                    # Xóa file lỗi cũ nếu có để tránh xung đột khóa file
                    if output_path.exists():
                        try:
                            output_path.unlink()
                        except Exception:
                            pass
                    
                    # Tạo file audio câm chuẩn MP3 bằng FFmpeg
                    self._create_silence_mp3(fallback_duration, output_path)
                    return fallback_duration


    def _create_silence_mp3(self, duration: float, output_path: Path):
        """Tạo file mp3 câm chuẩn sử dụng FFmpeg (thông qua imageio_ffmpeg hoặc moviepy)."""
        try:
            # 1. Tìm đường dẫn binary FFmpeg
            ffmpeg_bin = "ffmpeg"
            try:
                import imageio_ffmpeg
                ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            except ImportError:
                try:
                    from moviepy.config import get_setting
                    ffmpeg_bin = get_setting("FFMPEG_BINARY")
                except Exception:
                    pass

            # 2. Sử dụng FFmpeg sinh file MP3 câm chuẩn
            cmd = [
                ffmpeg_bin, "-y",
                "-f", "lavfi",
                "-i", "anullsrc=r=22050:cl=mono",
                "-t", str(duration),
                "-acodec", "libmp3lame",
                str(output_path)
            ]
            try:
                logger.info(f"Đang tạo file audio câm fallback dài {duration:.2f}s tại {output_path} bằng FFmpeg...")
            except UnicodeEncodeError:
                logger.info(f"Dang tao file audio cam fallback dai {duration:.2f}s tai {output_path.name} bang FFmpeg...")
            
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if res.returncode == 0:
                logger.info("Đã tạo file audio câm fallback thành công bằng FFmpeg.")
                return
            else:
                logger.error(f"FFmpeg sinh file audio câm thất bại. Exit code: {res.returncode}")
        except Exception as e:
            logger.error(f"Lỗi khi cố gắng tạo file audio câm bằng FFmpeg: {str(e)}")

        # 3. Fallback cuối cùng nếu FFmpeg lỗi: Tạo file WAV PCM giả lập MP3 như cũ (có nguy cơ lỗi giải mã nhưng giữ tính chạy được)
        try:
            logger.warning("Không thể dùng FFmpeg, sử dụng fallback tạo file WAV PCM giả lập MP3 làm phương án cuối cùng...")
        except UnicodeEncodeError:
            logger.warning("Khong the dung FFmpeg, su dung fallback tao file WAV PCM gia lap MP3 lam phuong an cuoi cung...")
            
        try:
            sample_rate = 22050
            num_channels = 1
            sample_width = 2  # 16-bit
            num_samples = int(duration * sample_rate)
            
            with wave.open(str(output_path), 'wb') as wav_file:
                wav_file.setnchannels(num_channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                
                silence_data = struct.pack('<h', 0) * num_samples
                wav_file.writeframes(silence_data)
            logger.info("Đã tạo file WAV giả lập MP3 thành công.")
        except Exception as fallback_err:
            logger.error(f"Lỗi tạo file audio câm dự phòng cuối cùng: {str(fallback_err)}")

tts_generator = TTSGenerator()
