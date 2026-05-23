import json
import logging
import google.generativeai as genai
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

class ScriptGenerator:
    def __init__(self):
        # Khởi tạo Gemini API nếu có key
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Sử dụng gemini-1.5-flash là model chuẩn và nhanh cho các tác vụ sinh văn bản
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
            logger.warning("GEMINI_API_KEY chưa được cấu hình. ScriptGenerator sẽ chạy ở chế độ giả lập (mock mode).")

    async def generate_script(self, topic: str, character_desc: str, voice_type: str, total_duration_minutes: int = 7) -> Dict[str, Any]:
        """
        Sinh kịch bản chi tiết từ chủ đề và thông tin nhân vật sử dụng Gemini API.
        """
        if not self.model:
            return self._generate_mock_script(topic, character_desc, total_duration_minutes)

        # Tính toán số lượng scene cần thiết (mỗi scene trung bình 12 giây, video 7 phút cần khoảng 35 scenes)
        target_scenes = int((total_duration_minutes * 60) / 12)
        
        prompt = f"""
        Bạn là một biên kịch chuyên nghiệp và nhà sản xuất video AI xuất sắc.
        Hãy tạo một kịch bản chi tiết cho video dài khoảng {total_duration_minutes} phút (tổng cộng khoảng {target_scenes} phân cảnh) về chủ đề: "{topic}".
        
        Thông tin nhân vật chính xuyên suốt video:
        - Mô tả ngoại hình nhân vật: "{character_desc}"
        
        Ngôn ngữ kịch bản: Tiếng Việt.
        Định dạng đầu ra BẮT BUỘC là JSON hợp lệ theo cấu trúc sau:
        {{
          "title": "Tiêu đề video",
          "theme": "Chủ đề chính",
          "character_description": "{character_desc}",
          "scenes": [
            {{
              "scene_number": 1,
              "visual_prompt": "Mô tả chi tiết hình ảnh phân cảnh bằng tiếng Anh. Luôn luôn bắt đầu bằng '{character_desc}', mô tả tư thế, biểu cảm và bối cảnh cụ thể của phân cảnh đó để AI vẽ ảnh đúng nhân vật (ví dụ: '{character_desc}, sitting in a dark room looking at a glowing monitor, photorealistic, 8k resolution, cinematic lighting')",
              "narration_text": "Lời thoại thuyết minh bằng tiếng Việt của phân cảnh này. Cần dài khoảng 25-45 từ để khi đọc lên mất khoảng 10-15 giây.",
              "estimated_duration": 12
            }}
          ]
        }}

        LƯU Ý QUAN TRỌNG:
        1. Phải sinh chính xác khoảng {target_scenes} phân cảnh để đảm bảo video đạt độ dài yêu cầu. Các phân cảnh phải liên kết chặt chẽ và tạo thành một câu chuyện hoàn chỉnh từ đầu đến cuối.
        2. Mỗi phân cảnh, phần 'visual_prompt' PHẢI viết bằng tiếng Anh và PHẢI chứa phần mô tả ngoại hình nhân vật '{character_desc}' ở đầu để giữ tính đồng nhất khi sinh ảnh bằng AI.
        3. Phần 'narration_text' phải là lời bình tự nhiên, trôi chảy, cuốn hút người nghe.
        4. Trả về cấu trúc JSON thuần túy, không có thẻ markdown ```json hay bất kỳ văn bản giải thích nào khác.
        """

        try:
            # Thiết lập sinh JSON
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            script_data = json.loads(response.text)
            logger.info(f"Đã sinh kịch bản thành công với {len(script_data.get('scenes', []))} phân cảnh.")
            return script_data
            
        except Exception as e:
            logger.error(f"Lỗi khi sinh kịch bản từ Gemini API: {str(e)}")
            # Fallback sang mock script nếu API bị lỗi để tránh crash ứng dụng
            return self._generate_mock_script(topic, character_desc, total_duration_minutes)

    def _generate_mock_script(self, topic: str, character_desc: str, total_duration_minutes: int) -> Dict[str, Any]:
        """
        Sinh kịch bản giả lập (mock) dùng cho trường hợp offline hoặc API lỗi.
        """
        logger.info("Sinh kịch bản chế độ Mock.")
        target_scenes = int((total_duration_minutes * 60) / 12)
        
        scenes = []
        for i in range(1, target_scenes + 1):
            scenes.append({
                "scene_number": i,
                "visual_prompt": f"{character_desc}, demonstrating concept related to {topic}, scene {i}, photorealistic, 8k, cinematic lighting",
                "narration_text": f"Đây là phân cảnh thứ {i} giới thiệu về chủ đề {topic}. Chúng ta đang tìm hiểu các khía cạnh khác nhau của vấn đề này một cách chi tiết để tạo nên một video dài 7 đến 8 phút chất lượng.",
                "estimated_duration": 12
            })
            
        return {
            "title": f"Khám Phá: {topic} (Bản thử nghiệm)",
            "theme": topic,
            "character_description": character_desc,
            "scenes": scenes
        }

script_generator = ScriptGenerator()
