import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    """Kiểm tra API root hoạt động đúng."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Auto Video Generator" in response.json()["message"]

def test_get_music_list():
    """Kiểm tra API danh sách nhạc nền trả về kết quả hợp lệ."""
    response = client.get("/api/music-list")
    assert response.status_code == 200
    data = response.json()
    assert "music_files" in data
    assert len(data["music_files"]) > 0

def test_preview_voice():
    """Kiểm tra API phát thử giọng nói hoạt động đúng với giọng mặc định."""
    response = client.get("/api/preview-voice?voice=vi-VN-HoaiMyNeural")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"

def test_generate_script_mock():
    """Kiểm tra API sinh kịch bản (chạy ở chế độ Mock hoặc thật)."""
    payload = {
        "topic": "Trí tuệ nhân tạo tương lai",
        "character_description": "A smart young man with glasses",
        "voice_type": "vi-VN-HoaiMyNeural",
        "duration_minutes": 3
    }
    response = client.post("/api/generate-script", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert "scenes" in data
    assert len(data["scenes"]) > 0
    assert data["scenes"][0]["scene_number"] == 1

def test_video_generation_flow():
    """Kiểm tra khởi chạy quy trình render video ngầm và truy vấn tiến độ."""
    # 1. Sinh kịch bản mock trước
    script_payload = {
        "topic": "Hố đen vũ trụ",
        "character_description": "An astronaut in space",
        "voice_type": "vi-VN-HoaiMyNeural",
        "duration_minutes": 1  # Dùng 1 phút để test cho nhanh
    }
    script_res = client.post("/api/generate-script", json=script_payload)
    assert script_res.status_code == 200
    script_data = script_res.json()

    # 2. Gửi request sinh video
    video_payload = {
        "title": script_data["title"],
        "theme": script_data["theme"],
        "character_description": script_data["character_description"],
        "scenes": script_data["scenes"][:2],  # Chỉ lấy 2 scene để tránh render quá lâu khi test
        "seed": 42,
        "voice_type": "vi-VN-HoaiMyNeural",
        "use_music": False  # Tắt nhạc để test độc lập
    }
    
    video_res = client.post("/api/generate-video", json=video_payload)
    assert video_res.status_code == 200
    video_data = video_res.json()
    assert "task_id" in video_data
    
    task_id = video_data["task_id"]
    
    # 3. Truy vấn trạng thái task
    status_res = client.get(f"/api/tasks/{task_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["task_id"] == task_id
    assert status_data["status"] in ["processing", "completed", "failed"]


def test_image_generator_self_healing_402_retry(tmp_path):
    """Kiểm tra cơ chế tự phục hồi khi Pollinations AI bị lỗi 402 (Queue Full)."""
    from unittest.mock import patch, MagicMock
    from app.services.image_gen import image_generator
    
    output_img = tmp_path / "test_402.jpg"
    
    # Giả lập requests.get trả về 402 ở lần 1, và 200 thành công ở lần 2
    mock_resp_402 = MagicMock()
    mock_resp_402.status_code = 402
    
    tiny_jpeg = b'\xff\xd8\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9'
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.content = tiny_jpeg
    
    with patch("requests.get") as mock_get, \
         patch("time.sleep") as mock_sleep:
        
        mock_get.side_effect = [mock_resp_402, mock_resp_200]
        
        result_path = image_generator.generate_image(
            prompt="A beautiful sunset",
            output_path=output_img,
            seed=42
        )
        
        assert result_path.exists()
        with open(result_path, "rb") as f:
            assert f.read() == b"fake image content"
            
        assert mock_get.call_count == 2
        assert mock_sleep.call_count == 1


def test_image_generator_self_healing_fallback(tmp_path):
    """Kiểm tra cơ chế tự phục hồi (Self-Healing) tạo ảnh fallback khi Pollinations AI lỗi hoàn toàn."""
    from unittest.mock import patch
    from app.services.image_gen import image_generator
    
    output_img = tmp_path / "test_fallback.jpg"
    
    with patch("requests.get") as mock_get, \
         patch("time.sleep") as mock_sleep:
        
        # Giả lập mọi yêu cầu đều bị ném ngoại lệ (lỗi kết nối)
        mock_get.side_effect = Exception("Connection error to Pollinations AI")
        
        result_path = image_generator.generate_image(
            prompt="A futuristic city with high towers",
            output_path=output_img,
            seed=42
        )
        
        # Hệ thống phải tự phục hồi bằng cách tạo ảnh fallback và không ném ra Exception làm crash app
        assert result_path.exists()
        assert result_path.stat().st_size > 0
        # Đảm bảo requests.get được gọi tối đa max_retries (4 lần)
        assert mock_get.call_count == 4


def test_stress_video_generation_10_scenes(tmp_path):
    """
    Stress test giả lập việc render một kịch bản video dài 10 phân cảnh trở lên.
    Giả lập lỗi mạng ngẫu nhiên và rate limit 402 để kiểm tra xem tính năng tự phục hồi 
    (Self-Healing) có giúp hoàn thành quy trình tạo video thành công hay không.
    """
    from unittest.mock import patch, MagicMock
    from pathlib import Path
    from app.services.tts_gen import tts_generator
    
    # Tạo 10 phân cảnh
    scenes = []
    for i in range(1, 11):
        scenes.append({
            "scene_number": i,
            "visual_prompt": f"Scenic view of mountain and river number {i}, photo, high quality",
            "narration_text": f"Chào mừng bạn đến với phân cảnh số {i} của video trải nghiệm.",
            "estimated_duration": 3.0
        })
        
    payload = {
        "title": "Video Stress Test 10 Phân Cảnh",
        "theme": "Nature",
        "character_description": "None",
        "scenes": scenes,
        "seed": 100,
        "voice_type": "vi-VN-HoaiMyNeural",
        "use_music": False
    }
    
    # Để kiểm soát thời gian chạy test và tránh nghẽn mạng do Edge-TTS, ta mock tts_generator
    # Nhưng vẫn giữ nguyên quy trình ghi file âm thanh câm nhanh
    async def mock_generate_voice(text, output_path, voice):
        # Tạo file audio câm dài 1.0s bằng hàm có sẵn của tts_generator (rút ngắn thời lượng để render nhanh hơn)
        tts_generator._create_silence_mp3(1.0, output_path)
        return 1.0
        
    # Mock requests.get để giả lập lỗi mạng và rate limit 402 ngẫu nhiên trên các phân cảnh:
    # - Cảnh 1, 2, 3: 200 thành công ngay
    # - Cảnh 4: 402 lần đầu, sau đó 200 thành công (kiểm thử 402 retry)
    # - Cảnh 5: lỗi liên tục ném Exception (kiểm thử fallback healing)
    # - Các cảnh còn lại: 200 thành công ngay
    tiny_jpeg = b'\xff\xd8\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9'
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.content = tiny_jpeg
    
    mock_resp_402 = MagicMock()
    mock_resp_402.status_code = 402
    
    call_idx = 0
    def mock_requests_get(*args, **kwargs):
        nonlocal call_idx
        call_idx += 1
        
        # Cảnh 4: Lần đầu tiên gọi (là lần gọi thứ 4 tổng cộng) trả về 402, lần sau trả về 200
        if call_idx == 4:
            return mock_resp_402
        # Cảnh 5: Lần đầu gọi của cảnh 5 (là lần gọi thứ 6 tổng cộng, vì cảnh 4 gọi 2 lần) và các lần retry tiếp theo của nó
        elif call_idx >= 6 and call_idx <= 9:
            raise Exception("Pollinations AI Server Timeout")
        else:
            return mock_resp_200

    with patch("requests.get", side_effect=mock_requests_get) as mock_get, \
         patch("time.sleep") as mock_sleep, \
         patch.object(tts_generator, "generate_voice", side_effect=mock_generate_voice) as mock_tts:
         
        # Gửi request thông qua fastapi TestClient
        # Vì TestClient chạy BackgroundTasks một cách đồng bộ trong luồng chính của nó,
        # phản hồi trả về từ client.post sẽ chỉ được trả lại SAU KHI background task hoàn thành.
        response = client.post("/api/generate-video", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        
        task_id = data["task_id"]
        
        # Kiểm tra trạng thái task từ task_manager
        from app.services.task_manager import task_manager
        task = task_manager.get_task(task_id)
        
        # Quy trình render phải hoàn thành thành công nhờ cơ chế tự phục hồi (Self-Healing)
        assert task is not None
        assert task["status"] == "completed", f"Task render thất bại: {task.get('message')}"
        assert task["progress"] == 100
        assert task["video_url"] is not None
        
        # Kiểm tra xem file video đầu ra có được sinh ra thực sự không
        video_relative_path = task["video_url"].replace("/static/", "")
        video_absolute_path = Path("app").parent / "storage" / video_relative_path
        
        assert video_absolute_path.exists()
        assert video_absolute_path.stat().st_size > 0
        
        # Dọn dẹp file final_output sau khi test xong
        if video_absolute_path.exists():
            try:
                # Xóa thư mục dự án
                import shutil
                shutil.rmtree(video_absolute_path.parent)
            except Exception:
                pass

