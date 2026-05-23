import os
import subprocess
import logging
import imageio_ffmpeg
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
            
            # Giữ nguyên ảnh tĩnh gốc chất lượng cao để tránh hiện tượng nhiễu hạt/nhấp nháy do thuật toán nội suy kích thước lẻ của MoviePy
            zoom_clip = image_clip
            
            # Gán âm thanh cho clip
            audio_clip = AudioFileClip(str(audio_path))
            video_clip = zoom_clip.with_audio(audio_clip)
            
            # Xuất clip phụ (render tạm)
            # Sử dụng libx264 và aac, preset medium và crf 18 để đảm bảo chất lượng hình ảnh nét căng 100%
            # Đặt pix_fmt="yuv420p" để video clip tạm thời và video ghép nối (kể cả khi fallback copy trực tiếp) luôn tương thích hoàn hảo với Chrome/Firefox/Edge
            video_clip.write_videofile(
                str(output_path),
                fps=24,
                codec="libx264",
                audio_codec="aac",
                logger=None, # Tắt progress bar mặc định của moviepy để tránh spam log
                preset="medium",
                ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "18"]
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
            
            # Sử dụng executable ffmpeg từ imageio_ffmpeg để đảm bảo hoạt động trên Windows
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            
            # Lệnh FFmpeg concatenate không render lại
            # -f concat: chế độ concat demuxer
            # -safe 0: cho phép đường dẫn tuyệt đối
            # -y: tự động ghi đè file cũ
            # -c copy: sao chép nguyên trạng video/audio stream không re-encode
            cmd = [
                ffmpeg_exe, "-y",
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
        Sử dụng FFmpeg để ghép nhạc nền và chèn phụ đề vào video thành phẩm.
        Đảm bảo file output_path luôn được tạo ra (có cơ chế fallback an toàn).
        """
        import shutil
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Đường dẫn tương đối hoặc tuyệt đối tương thích cho bộ lọc subtitles của FFmpeg
        srt_ffmpeg_path = str(srt_path.resolve()).replace("\\", "/").replace(":", "\\:")
        
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        has_music = music_path and music_path.exists() and music_path.is_file()
        
        logger.info(f"Bắt đầu phối trộn nhạc nền & lồng phụ đề (Có nhạc nền: {has_music})...")
        
        # Thử nghiệm lần 1: Đầy đủ tính năng
        try:
            if has_music:
                filter_complex = "[1:a]volume=0.12[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                cmd = [
                    ffmpeg_exe, "-y",
                    "-i", str(video_path),
                    "-stream_loop", "-1", "-i", str(music_path),
                    "-filter_complex", filter_complex,
                    "-map", "0:v",
                    "-map", "[aout]",
                    "-vf", f"subtitles='{srt_ffmpeg_path}':force_style='Fontname=Arial,Fontsize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=3,Outline=1,Shadow=1,Alignment=2'",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-preset", "medium",
                    "-crf", "22",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    str(output_path)
                ]
            else:
                # Không có nhạc, chỉ chèn phụ đề và giữ nguyên audio thuyết minh gốc
                cmd = [
                    ffmpeg_exe, "-y",
                    "-i", str(video_path),
                    "-vf", f"subtitles='{srt_ffmpeg_path}':force_style='Fontname=Arial,Fontsize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=3,Outline=1,Shadow=1,Alignment=2'",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-preset", "medium",
                    "-crf", "22",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    str(output_path)
                ]
            
            logger.info(f"Thực thi lệnh FFmpeg: {' '.join(cmd[:10])}...")
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if process.returncode == 0:
                logger.info(f"Đã xuất video hoàn chỉnh thành công: {output_path}")
                return output_path
                
            logger.warning(f"Lệnh FFmpeg thất bại với exit code {process.returncode}. Stderr: {process.stderr}")
            
        except Exception as e:
            logger.error(f"Lỗi khi thực thi FFmpeg lần 1: {str(e)}")
            
        # Thử nghiệm lần 2: Fallback nếu lỗi phụ đề (ví dụ do lỗi font hoặc đường dẫn srt)
        if has_music:
            try:
                logger.info("Thử lồng nhạc nền mà KHÔNG chèn phụ đề để tránh crash...")
                filter_complex = "[1:a]volume=0.12[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                cmd_fallback = [
                    ffmpeg_exe, "-y",
                    "-i", str(video_path),
                    "-stream_loop", "-1", "-i", str(music_path),
                    "-filter_complex", filter_complex,
                    "-map", "0:v",
                    "-map", "[aout]",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-preset", "medium",
                    "-crf", "22",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    str(output_path)
                ]
                process = subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if process.returncode == 0:
                    logger.info(f"Đã xuất video fallback (chỉ lồng nhạc) thành công: {output_path}")
                    return output_path
            except Exception as fe:
                logger.error(f"Lỗi khi lồng nhạc fallback: {str(fe)}")
                
        # Thử nghiệm lần 3: Fallback an toàn tuyệt đối - sao chép file gốc sang file final_output
        try:
            logger.info("Mọi phương án render nâng cao đều thất bại. Sao chép trực tiếp file video thô sang final_output để giữ tính hoạt động của ứng dụng.")
            shutil.copy(str(video_path), str(output_path))
            logger.info(f"Đã hoàn thành sao chép file video thô sang {output_path}")
            return output_path
        except Exception as copy_err:
            logger.error(f"Không thể sao chép tệp fallback: {str(copy_err)}")
            return video_path

    def _format_srt_time(self, seconds: float) -> str:
        """Helper format giây thành HH:MM:SS,mmm"""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

video_composer = VideoComposer()
