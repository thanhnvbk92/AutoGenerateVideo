import os
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import settings
from app.services.script_gen import script_generator
from app.services.tts_gen import tts_generator
from app.services.image_gen import image_generator
from app.services.video_comp import video_composer
from app.services.task_manager import task_manager

# Thiết lập ghi log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Auto Video Generator API")

# Cấu hình CORS để frontend React gọi được API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trạng thái của các task render được quản lý bởi task_manager lưu bền vững trong file JSON

# Đảm bảo các thư mục tĩnh và storage tồn tại trước khi mount
settings.create_directories()
app.mount("/static", StaticFiles(directory=str(settings.STORAGE_DIR)), name="static")

# Khởi tạo một file nhạc nền mặc định câm hoặc nhạc nhẹ nếu chưa có
DEFAULT_MUSIC_PATH = settings.STORAGE_DIR / "default_music.mp3"
if not DEFAULT_MUSIC_PATH.exists():
    # Tạo một file audio trống bằng cách sao chép một file dummy hoặc ghi log cảnh báo
    # Chúng ta sẽ kiểm tra sự tồn tại của file nhạc nền khi render, nếu không có sẽ bỏ qua bước trộn nhạc
    logger.info("Chưa có nhạc nền mặc định tại default_music.mp3. Hệ thống sẽ bỏ qua nhạc nền nếu không tìm thấy.")

# --- ĐỊNH NGHĨA PYDANTIC MODELS ---

class ScriptRequest(BaseModel):
    topic: str
    character_description: str
    voice_type: str = "vi-VN-HoaiMyNeural"
    duration_minutes: int = 7

class SceneItem(BaseModel):
    scene_number: int
    visual_prompt: str
    narration_text: str
    estimated_duration: float

class VideoGenerateRequest(BaseModel):
    title: str
    theme: str
    character_description: str
    scenes: List[SceneItem]
    seed: int = 42
    voice_type: str = "vi-VN-HoaiMyNeural"
    use_music: bool = True
    bg_music_name: str = "default_music.mp3"

# --- API ENDPOINTS ---

@app.get("/")
def read_root():
    return {"message": "Chào mừng đến với API tự động tạo video (Auto Video Generator)!"}

@app.get("/api/music-list")
def get_music_list():
    """
    API lấy danh sách các tệp nhạc nền có sẵn.
    """
    music_dir = settings.STORAGE_DIR / "music"
    music_dir.mkdir(exist_ok=True)
    
    # Lấy các file .mp3 trong thư mục music
    music_files = [f.name for f in music_dir.glob("*.mp3")]
    
    # Luôn thêm nhạc mặc định nếu tồn tại
    if (settings.STORAGE_DIR / "default_music.mp3").exists():
        music_files.insert(0, "default_music.mp3")
    else:
        # Nếu chưa có file nào, thêm một item giả lập để hiển thị
        if not music_files:
            music_files.append("default_music.mp3")
            
    return {"music_files": music_files}

@app.get("/api/preview-voice")
async def preview_voice(voice: str = "vi-VN-HoaiMyNeural"):
    """
    API sinh hoặc trả về file âm thanh nghe thử ngắn cho giọng đọc được chọn.
    """
    sample_text = "Chào bạn! Đây là giọng đọc thuyết minh thử nghiệm của tôi."
    preview_dir = settings.STORAGE_DIR / "previews"
    preview_dir.mkdir(exist_ok=True)
    preview_path = preview_dir / f"{voice}_preview.mp3"
    
    try:
        # Nếu chưa có file preview, sinh file bằng TTS
        if not preview_path.exists():
            await tts_generator.generate_voice(sample_text, preview_path, voice)
            
        return FileResponse(path=str(preview_path), media_type="audio/mpeg", filename=f"{voice}_preview.mp3")
    except Exception as e:
        logger.error(f"Lỗi khi tạo preview giọng đọc: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Không thể sinh giọng đọc thử nghiệm: {str(e)}")

@app.post("/api/generate-script")
async def generate_script(req: ScriptRequest):
    """
    API 1: Nhận chủ đề và mô tả nhân vật, sinh kịch bản chi tiết qua Gemini API.
    """
    try:
        script = await script_generator.generate_script(
            topic=req.topic,
            character_desc=req.character_description,
            voice_type=req.voice_type,
            total_duration_minutes=req.duration_minutes
        )
        return script
    except Exception as e:
        logger.error(f"Lỗi khi sinh kịch bản: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Không thể sinh kịch bản: {str(e)}")

@app.post("/api/generate-video")
async def generate_video(req: VideoGenerateRequest, background_tasks: BackgroundTasks):
    """
    API 2: Nhận kịch bản đã chỉnh sửa, khởi chạy Task chạy ngầm để render video và trả về Task ID.
    """
    task_id = str(uuid.uuid4())
    task_manager.set_task(task_id, {
        "task_id": task_id,
        "status": "processing",
        "progress": 0,
        "message": "Đang chuẩn bị dự án...",
        "video_url": None
    })
    
    # Đẩy tác vụ render xuống background task
    background_tasks.add_task(
        run_video_generation_flow,
        task_id=task_id,
        request_data=req.model_dump()
    )
    
    return {"task_id": task_id, "message": "Quá trình sinh video đã được bắt đầu ngầm."}

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    API 3: API truy vấn tiến độ render video từ Frontend theo thời gian thực.
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin task này.")
    return task

@app.get("/api/projects")
def get_projects_list():
    """
    API lấy danh sách tất cả các dự án (tasks) đã tạo, sắp xếp theo thời gian cập nhật mới nhất.
    """
    try:
        db = task_manager._read_db()
        sorted_tasks = sorted(
            db.values(),
            key=lambda x: x.get("last_updated", 0),
            reverse=True
        )
        return {"projects": sorted_tasks}
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách dự án: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Không thể lấy danh sách dự án: {str(e)}")

# --- BACKGROUND WORKER LOGIC ---

async def run_video_generation_flow(task_id: str, request_data: Dict[str, Any]):
    """
    Task chạy ngầm điều phối tuần tự quy trình tạo video:
    TTS -> Sinh ảnh -> Render clip phân cảnh -> Ghép video -> Lồng nhạc & Phụ đề.
    """
    project_id = str(uuid.uuid4())
    project_dir = settings.STORAGE_DIR / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Tạo các thư mục con cho dự án
    audio_dir = project_dir / "audio"
    images_dir = project_dir / "images"
    scenes_dir = project_dir / "scenes"
    
    audio_dir.mkdir(exist_ok=True)
    images_dir.mkdir(exist_ok=True)
    scenes_dir.mkdir(exist_ok=True)
    
    scenes = request_data.get("scenes", [])
    total_scenes = len(scenes)
    seed = request_data.get("seed", 42)
    voice_type = request_data.get("voice_type", "vi-VN-HoaiMyNeural")
    use_music = request_data.get("use_music", True)
    
    logger.info(f"Khởi chạy Task {task_id} cho dự án {project_id} có {total_scenes} phân cảnh.")
    
    try:
        # Cơ chế tải tài nguyên (TTS & Image) song song tối đa 5 tác vụ đồng thời
        sem = asyncio.Semaphore(5)
        # Semaphore giới hạn tối đa 1 tác vụ gọi Pollinations AI đồng thời để tránh lỗi 402 Queue Full theo IP
        image_sem = asyncio.Semaphore(1)
        
        completed_assets = 0
        results = []
        
        async def fetch_assets_for_scene(idx, scene):
            nonlocal completed_assets
            async with sem:
                scene_num = scene.get("scene_number", idx + 1)
                
                # 1. Sinh âm thanh giọng đọc (TTS) có cơ chế tận dụng cache
                narration = scene.get("narration_text", "")
                audio_path = audio_dir / f"scene_{scene_num}.mp3"
                
                if audio_path.exists() and audio_path.stat().st_size > 0:
                    logger.info(f"Đã có sẵn file âm thanh cho phân cảnh {scene_num}, sử dụng cache.")
                    # Đọc thời lượng từ file audio có sẵn
                    from moviepy import AudioFileClip
                    try:
                        audio_clip = AudioFileClip(str(audio_path))
                        duration = audio_clip.duration
                        audio_clip.close()
                    except Exception:
                        # Nếu file lỗi, tạo lại
                        duration = await tts_generator.generate_voice(narration, audio_path, voice_type)
                else:
                    duration = await tts_generator.generate_voice(narration, audio_path, voice_type)
                
                # 2. Sinh ảnh nhân vật đồng nhất (Pollinations AI) có cơ chế tận dụng cache
                visual_prompt = scene.get("visual_prompt", "")
                image_path = images_dir / f"scene_{scene_num}.jpg"
                
                if image_path.exists() and image_path.stat().st_size > 0:
                    logger.info(f"Đã có sẵn file hình ảnh cho phân cảnh {scene_num}, sử dụng cache.")
                else:
                    async with image_sem:
                        await asyncio.to_thread(
                            image_generator.generate_image,
                            prompt=visual_prompt,
                            output_path=image_path,
                            seed=seed + idx
                        )
                
                completed_assets += 1
                # Cập nhật tiến độ tải tài nguyên: từ 5% đến 40%
                download_progress = 5 + int((completed_assets / total_scenes) * 35)
                task_manager.update_task(task_id, {
                    "progress": download_progress,
                    "message": f"Đã chuẩn bị tài nguyên phân cảnh {completed_assets}/{total_scenes}..."
                })
                
                return idx, audio_path, image_path, duration

        # Khởi chạy song song
        task_manager.update_task(task_id, {
            "progress": 5,
            "message": f"Bắt đầu tải song song tài nguyên cho {total_scenes} phân cảnh..."
        })
        
        download_tasks = [fetch_assets_for_scene(idx, scene) for idx, scene in enumerate(scenes)]
        results = await asyncio.gather(*download_tasks)
        
        # Sắp xếp kết quả theo đúng thứ tự phân cảnh ban đầu
        results.sort(key=lambda x: x[0])
        
        scene_video_paths = []
        audio_durations = []
        
        # Render tuần tự các phân cảnh từ tài nguyên đã chuẩn bị
        for idx, audio_path, image_path, duration in results:
            scene_num = idx + 1
            
            # Cập nhật status render: chiếm từ 40% đến 80% tổng tiến độ
            render_progress = 40 + int((idx / total_scenes) * 40)
            task_manager.update_task(task_id, {
                "progress": render_progress,
                "message": f"Đang render video phân cảnh {scene_num}/{total_scenes}..."
            })
            
            # 3. Render video phân cảnh tạm thời (MoviePy)
            scene_video_path = scenes_dir / f"scene_{scene_num}.mp4"
            await asyncio.to_thread(
                video_composer.create_scene_clip,
                image_path=image_path,
                audio_path=audio_path,
                output_path=scene_video_path,
                duration=duration
            )
            scene_video_paths.append(scene_video_path)
            audio_durations.append(duration)
            
            # Cho event loop nghỉ một chút để giải phóng CPU
            await asyncio.sleep(0.05)

        # 4. Ghép nối các video tạm thời bằng FFmpeg Concat (80% -> 90%)
        task_manager.update_task(task_id, {
            "progress": 80,
            "message": "Đang thực hiện ghép nối các phân cảnh..."
        })
        
        concatenated_video_path = project_dir / "concatenated.mp4"
        await asyncio.to_thread(
            video_composer.concatenate_videos,
            video_paths=scene_video_paths,
            output_path=concatenated_video_path
        )
        
        # 5. Tạo file phụ đề SRT
        srt_path = project_dir / "subtitles.srt"
        await asyncio.to_thread(
            video_composer.create_srt_subtitles,
            scenes=scenes,
            audio_durations=audio_durations,
            output_path=srt_path
        )
        
        # 6. Trộn nhạc nền & hardcode phụ đề (90% -> 100%)
        task_manager.update_task(task_id, {
            "progress": 90,
            "message": "Đang phối trộn nhạc nền và tạo phụ đề hoàn chỉnh..."
        })
        
        final_video_path = project_dir / "final_output.mp4"
        
        # Lấy tên nhạc nền được chọn từ request
        bg_music_name = request_data.get("bg_music_name", "default_music.mp3")
        music_path = None
        
        if use_music:
            if bg_music_name == "default_music.mp3":
                music_path = DEFAULT_MUSIC_PATH
            else:
                music_path = settings.STORAGE_DIR / "music" / bg_music_name
            
            # Fallback nếu file nhạc chọn không tồn tại
            if music_path and not music_path.exists():
                music_path = DEFAULT_MUSIC_PATH if DEFAULT_MUSIC_PATH.exists() else None
        
        if music_path and music_path.exists():
            await asyncio.to_thread(
                video_composer.add_background_music_and_subtitles,
                video_path=concatenated_video_path,
                music_path=music_path,
                srt_path=srt_path,
                output_path=final_video_path
            )
        else:
            # Nếu không có nhạc nền hoặc không yêu cầu nhạc nền, chỉ chèn phụ đề (nếu có thể) hoặc copy thẳng concatenated sang final
            logger.info("Không sử dụng nhạc nền. Thực hiện lồng phụ đề thô.")
            await asyncio.to_thread(
                video_composer.add_background_music_and_subtitles,
                video_path=concatenated_video_path,
                music_path=Path(""), # Sẽ kích hoạt fallback không nhạc
                srt_path=srt_path,
                output_path=final_video_path
            )
            
        # Dọn dẹp các tệp tạm của phân cảnh để tiết kiệm dung lượng ổ đĩa
        # Giữ lại final_output.mp4 và phụ đề srt
        try:
            for path in scene_video_paths:
                if path.exists():
                    path.unlink()
            if concatenated_video_path.exists():
                concatenated_video_path.unlink()
            logger.info("Đã dọn dẹp các file video tạm thời.")
        except Exception as cleanup_err:
            logger.warning(f"Lỗi dọn dẹp tệp tạm: {str(cleanup_err)}")
            
        # Cập nhật kết quả hoàn tất
        video_url = f"/static/projects/{project_id}/final_output.mp4"
        task_manager.update_task(task_id, {
            "status": "completed",
            "progress": 100,
            "message": "Tạo video hoàn tất thành công!",
            "video_url": video_url
        })
        
        logger.info(f"Task {task_id} hoàn thành xuất sắc! Video link: {video_url}")
        
    except Exception as err:
        logger.error(f"Lỗi nghiêm trọng trong quá trình xử lý Task {task_id}: {str(err)}")
        task_manager.update_task(task_id, {
            "status": "failed",
            "message": f"Lỗi: {str(err)}"
        })

# --- HỆ THỐNG TỰ ĐỘNG GIÁM SÁT & TỰ PHỤC HỒI (MONITORING & AUTO-RECOVERY) ---

async def monitor_tasks_health():
    """
    Tiến trình giám sát chạy ngầm: Tự động quét và giải phóng các Task bị kẹt (Stuck) quá 3 phút.
    """
    import time
    while True:
        try:
            await asyncio.sleep(30)  # Quét định kỳ mỗi 30 giây
            db = task_manager._read_db()
            now = time.time()
            for task_id, task in db.items():
                if task.get("status") == "processing":
                    last_updated = task.get("last_updated", now)
                    # Nếu task ở trạng thái processing quá 3 phút (180 giây) không cập nhật
                    if now - last_updated > 180:
                        logger.warning(f"Phát hiện Task bị kẹt (Stuck): {task_id}. Tiến hành tự động giải cứu...")
                        task_manager.update_task(task_id, {
                            "status": "failed",
                            "message": "Hệ thống tự động phát hiện tiến trình bị kẹt quá lâu và đã giải phóng tài nguyên. Bạn có thể nhấn tạo lại để tiếp tục."
                        })
        except Exception as e:
            logger.error(f"Lỗi trong luồng giám sát Task Health: {str(e)}")

@app.on_event("startup")
async def startup_event():
    logger.info("Khởi chạy Luồng giám sát sức khỏe Task (Auto-Recovery Monitor)...")
    asyncio.create_task(monitor_tasks_health())

