import os
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import settings
from app.services.script_gen import script_generator
from app.services.tts_gen import tts_generator
from app.services.image_gen import image_generator
from app.services.video_comp import video_composer

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

# Lưu trữ trạng thái của các task render ngầm trong bộ nhớ tạm (in-memory)
# Trong môi trường sản xuất, nên dùng Redis hoặc DB
tasks_status: Dict[str, Dict[str, Any]] = {}

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

# --- API ENDPOINTS ---

@app.get("/")
def read_root():
    return {"message": "Chào mừng đến với API tự động tạo video (Auto Video Generator)!"}

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
    tasks_status[task_id] = {
        "task_id": task_id,
        "status": "processing",
        "progress": 0,
        "message": "Đang chuẩn bị dự án...",
        "video_url": None
    }
    
    # Đẩy tác vụ render xuống background task
    background_tasks.add_task(
        run_video_generation_flow,
        task_id=task_id,
        request_data=req.dict()
    )
    
    return {"task_id": task_id, "message": "Quá trình sinh video đã được bắt đầu ngầm."}

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    API 3: API truy vấn tiến độ render video từ Frontend theo thời gian thực.
    """
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin task này.")
    return tasks_status[task_id]

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
        scene_video_paths = []
        audio_durations = []
        
        # Vòng lặp sinh tài nguyên và render cho từng phân cảnh
        for idx, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", idx + 1)
            
            # Cập nhật status: Tiến độ sinh tài nguyên của từng scene chiếm từ 0% đến 80% tổng tiến độ
            current_progress = int((idx / total_scenes) * 80)
            tasks_status[task_id]["progress"] = current_progress
            tasks_status[task_id]["message"] = f"Đang tạo phân cảnh {scene_num}/{total_scenes}: Sinh giọng đọc & ảnh AI..."
            
            # 1. Sinh âm thanh giọng đọc (TTS)
            narration = scene.get("narration_text", "")
            audio_path = audio_dir / f"scene_{scene_num}.mp3"
            # Gọi async service
            duration = await tts_generator.generate_voice(narration, audio_path, voice_type)
            audio_durations.append(duration)
            
            # 2. Sinh ảnh nhân vật đồng nhất (Pollinations AI)
            visual_prompt = scene.get("visual_prompt", "")
            image_path = images_dir / f"scene_{scene_num}.jpg"
            # Pollinations là GET HTTP đồng bộ, chạy trên thread pool để tránh block event loop
            await asyncio.to_thread(
                image_generator.generate_image,
                prompt=visual_prompt,
                output_path=image_path,
                seed=seed
            )
            
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
            
            # Cho event loop nghỉ một chút để không block tài nguyên hệ thống
            await asyncio.sleep(0.1)

        # 4. Ghép nối các video tạm thời bằng FFmpeg Concat (80% -> 90%)
        tasks_status[task_id]["progress"] = 80
        tasks_status[task_id]["message"] = "Đang thực hiện ghép nối các phân cảnh..."
        
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
        tasks_status[task_id]["progress"] = 90
        tasks_status[task_id]["message"] = "Đang phối trộn nhạc nền và tạo phụ đề hoàn chỉnh..."
        
        final_video_path = project_dir / "final_output.mp4"
        
        # Kiểm tra xem có sử dụng nhạc nền không
        music_path = DEFAULT_MUSIC_PATH if (use_music and DEFAULT_MUSIC_PATH.exists()) else None
        
        if music_path:
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
        tasks_status[task_id]["status"] = "completed"
        tasks_status[task_id]["progress"] = 100
        tasks_status[task_id]["message"] = "Tạo video hoàn tất thành công!"
        tasks_status[task_id]["video_url"] = f"/static/projects/{project_id}/final_output.mp4"
        
        logger.info(f"Task {task_id} hoàn thành xuất sắc! Video link: {tasks_status[task_id]['video_url']}")
        
    except Exception as err:
        logger.error(f"Lỗi nghiêm trọng trong quá trình xử lý Task {task_id}: {str(err)}")
        tasks_status[task_id]["status"] = "failed"
        tasks_status[task_id]["message"] = f"Lỗi: {str(err)}"
