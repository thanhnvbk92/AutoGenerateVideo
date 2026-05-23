import os
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any
from moviepy import ImageClip, AudioFileClip

logger = logging.getLogger(__name__)

class VideoComposer:
    def create_scene_clip(self, image_path: Path, audio_path: Path, output_path: Path, duration: float) -> Path:
        """
        Tạo một video clip ngắn cho một phân cảnh từ ảnh và âm thanh.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Đang render phân cảnh clip: {output_path.name} (Thời lượng: {duration:.2f}s)")
            
            # Khởi tạo ImageClip
            # Thêm 0.2 giây đệm để tránh âm thanh bị cắt cụt ở cuối clip
            clip_duration = duration + 0.2
            image_clip = ImageClip(str(image_path)).with_duration(clip_duration)
            
            # Áp dụng hiệu ứng động phóng to nhẹ (Ken Burns Zoom)
            # Tăng nhẹ size từ 100% lên 105% theo thời gian t
            zoom_clip = image_clip.resized(lambda t: 1.0 + 0.05 * (t / clip_duration))
            
            # Gán âm thanh cho clip
            audio_clip = AudioFileClip(str(audio_path))
            video_clip = zoom_clip.with_audio(audio_clip)
            
            # Xuất clip phụ (render tạm)
            # Sử dụng libx264 và aac, preset ultra-fast để render nhanh nhất có thể cho từng scene
            video_clip.write_videofile(
                str(output_path),
                fps=24,
                codec="libx264",
                audio_codec="aac",
                logger=None, # Tắt progress bar mặc định của moviepy để tránh spam log
                preset="ultrafast"
            )
            
            # Đóng clip giải phóng tài nguyên
            video_clip.close()
            audio_clip.close()
            image_clip.close()
            
            logger.info(f"Đã render xong phân cảnh tạm: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Lỗi khi render phân cảnh {output_path.name}: {str(e)}")
            raise e

    def concatenate_videos(self, video_paths: List[Path], output_path: Path) -> Path:
        """
        Ghép nối nhiều video nhỏ thành một video lớn duy nhất bằng FFmpeg Concat Demuxer.
        Phương pháp này cực kỳ nhanh, không cần encode lại và tốn rất ít RAM.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Tạo file text chứa danh sách video để FFmpeg đọc
        list_file_path = output_path.parent / "concat_list.txt"
        with open(list_file_path, "w", encoding="utf-8") as f:
            for path in video_paths:
                # FFmpeg concat demuxer yêu cầu đường dẫn tương thích, tốt nhất là dùng dấu gạch chéo xuôi
                normalized_path = str(path.resolve()).replace("\\", "/")
                f.write(f"file '{normalized_path}'\n")
                
        try:
            logger.info(f"Đang thực hiện ghép nối {len(video_paths)} phân cảnh thành video lớn...")
            
            # Lệnh FFmpeg concatenate không render lại
            # -f concat: chế độ concat demuxer
            # -safe 0: cho phép đường dẫn tuyệt đối
            # -y: tự động ghi đè file cũ
            # -c copy: sao chép nguyên trạng video/audio stream không re-encode (tốc độ ánh sáng!)
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file_path),
                "-c", "copy",
                str(output_path)
            ]
            
            # Chạy FFmpeg CLI
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if process.returncode != 0:
                logger.error(f"Lỗi ghép nối video bằng FFmpeg. Stderr: {process.stderr}")
                raise Exception("FFmpeg Concat failed")
                
            logger.info(f"Đã ghép nối thành công video lớn: {output_path}")
            
            # Xóa file danh sách tạm thời sau khi hoàn tất
            if list_file_path.exists():
                list_file_path.unlink()
                
            return output_path
            
        except Exception as e:
            logger.error(f"Lỗi khi ghép nối video bằng FFmpeg: {str(e)}")
            raise e

    def create_srt_subtitles(self, scenes: List[Dict[str, Any]], audio_durations: List[float], output_path: Path):
        """
        Tạo file phụ đề .srt đồng bộ thời gian từ kịch bản phân cảnh.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                current_time = 0.0
                for i, (scene, duration) in enumerate(zip(scenes, audio_durations)):
                    start_time = current_time
                    end_time = current_time + duration + 0.2 # cộng thêm phần đệm
                    
                    # Convert thời gian sang format SRT: HH:MM:SS,mmm
                    start_srt = self._format_srt_time(start_time)
                    end_srt = self._format_srt_time(end_time)
                    
                    text = scene.get("narration_text", "")
                    
                    f.write(f"{i + 1}\n")
                    f.write(f"{start_srt} --> {end_srt}\n")
                    f.write(f"{text}\n\n")
                    
                    current_time = end_time
            logger.info(f"Đã tạo file phụ đề thành công: {output_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo file phụ đề SRT: {str(e)}")

    def add_background_music_and_subtitles(self, video_path: Path, music_path: Path, srt_path: Path, output_path: Path) -> Path:
        """
        Sử dụng FFmpeg để ghép nhạc nền (giảm âm lượng nhạc nền và trộn với giọng đọc)
        và ghi phụ đề vào video thành phẩm.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Đường dẫn tương đối hoặc tuyệt đối tương thích cho bộ lọc subtitles của FFmpeg
        # Chú ý: Bộ lọc subtitles của FFmpeg trên Windows thường yêu cầu xử lý ký tự đường dẫn đặc biệt
        # ví dụ: path phải thay đổi các ký tự '\' thành '/' và escape ký tự ':' thành '\:'
        srt_ffmpeg_path = str(srt_path.resolve()).replace("\\", "/").replace(":", "\\:")
        
        try:
            logger.info("Đang xử lý lồng nhạc nền và phụ đề cho video thành phẩm...")
            
            # Lệnh FFmpeg để:
            # 1. Trộn audio từ video gốc (index 0 - giọng đọc) và audio nhạc nền (index 1).
            # 2. Loop nhạc nền nếu nhạc nền ngắn hơn video (-stream_loop -1).
            # 3. Sử dụng bộ lọc amix để trộn: giảm volume nhạc nền xuống còn 0.12 (12%), giữ nguyên giọng đọc.
            # 4. Sử dụng bộ lọc video để chèn phụ đề (subtitles).
            
            # Lọc audio: [0:a] là audio video gốc, [1:a] là nhạc nền. 
            # volume=0.12: giảm âm lượng nhạc nền.
            # amix=inputs=2:duration=first: Trộn 2 luồng, thời lượng video bằng luồng thứ nhất (video).
            filter_complex = "[1:a]volume=0.12[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-stream_loop", "-1", "-i", str(music_path),
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[aout]",
                "-vf", f"subtitles='{srt_ffmpeg_path}'",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path)
            ]
            
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if process.returncode != 0:
                logger.warning(f"Lỗi khi lồng phụ đề/nhạc nền bằng FFmpeg (có thể do lỗi font hoặc thư mục phụ đề). Stderr: {process.stderr}")
                logger.info("Thử lồng nhạc nền mà KHÔNG chèn phụ đề vào video (người dùng có thể xem phụ đề trên UI)...")
                # Thử lại chỉ lồng nhạc nền, bỏ filter subtitles
                cmd_no_sub = [
                    "ffmpeg", "-y",
                    "-i", str(video_path),
                    "-stream_loop", "-1", "-i", str(music_path),
                    "-filter_complex", filter_complex,
                    "-map", "0:v",
                    "-map", "[aout]",
                    "-c:v", "copy", # copy video stream trực tiếp không encode lại
                    "-c:a", "aac",
                    "-b:a", "192k",
                    str(output_path)
                ]
                process_no_sub = subprocess.run(cmd_no_sub, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if process_no_sub.returncode != 0:
                    raise Exception(f"Lỗi lồng nhạc nền. Stderr: {process_no_sub.stderr}")
                    
            logger.info(f"Đã xuất video hoàn chỉnh thành công: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Lỗi khi lồng nhạc nền và phụ đề: {str(e)}")
            # Nếu toàn bộ thất bại, trả về video gốc để dự án vẫn có kết quả
            return video_path

    def _format_srt_time(self, seconds: float) -> str:
        """Helper format giây thành HH:MM:SS,mmm"""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

video_composer = VideoComposer()
