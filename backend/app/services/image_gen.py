import urllib.parse
import requests
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ImageGenerator:
    def generate_image(self, prompt: str, output_path: Path, seed: int = 42, width: int = 1280, height: int = 720) -> Path:
        """
        Tải ảnh được sinh từ Pollinations AI dựa trên prompt, seed cố định và kích thước.
        Lưu ảnh trực tiếp vào output_path.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Mã hóa prompt sang định dạng an toàn cho URL
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Sử dụng model flux (hoặc turbo, hoặc mặc định) và nologo để ảnh sạch đẹp
        # Pollinations AI: https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&seed={seed}&model=flux&nologo=true
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&seed={seed}&model=flux&nologo=true&private=true"
        
        try:
            logger.info(f"Đang tải ảnh sinh từ Pollinations AI...")
            logger.debug(f"URL Request: {url}")
            
            # Gửi request tải ảnh, timeout sau 60 giây vì AI sinh ảnh có thể mất chút thời gian
            response = requests.get(url, timeout=60)
            
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Đã lưu ảnh thành công tại: {output_path}")
                return output_path
            else:
                logger.error(f"Không thể tải ảnh. Status code: {response.status_code}. Response: {response.text[:200]}")
                raise Exception(f"Pollinations AI trả về status code {response.status_code}")
                
        except Exception as e:
            logger.error(f"Lỗi khi gọi API Pollinations AI: {str(e)}")
            # Tạo ảnh placeholder màu xám đơn giản phòng trường hợp offline hoặc API lỗi
            self._create_fallback_placeholder(prompt, output_path, width, height)
            return output_path

    def _create_fallback_placeholder(self, prompt: str, output_path: Path, width: int, height: int):
        """
        Tạo ảnh placeholder tĩnh trong trường hợp lỗi mạng hoặc lỗi API.
        Sử dụng PIL (nếu có) hoặc tạo một file ảnh BMP/PNG cơ bản.
        """
        logger.warning(f"Đang tạo ảnh fallback placeholder cho: {output_path}")
        try:
            from PIL import Image, ImageDraw, ImageFont
            # Tạo ảnh xám đậm
            img = Image.new('RGB', (width, height), color='#1f2937')
            draw = ImageDraw.Draw(img)
            
            # Vẽ một số hình cơ bản và ghi prompt rút gọn lên ảnh
            text = prompt[:50] + "..." if len(prompt) > 50 else prompt
            draw.text((50, height // 2), f"[Fallback Image]\n{text}", fill='#f3f4f6')
            
            img.save(output_path)
            logger.info("Đã tạo ảnh fallback PIL thành công.")
        except Exception as e:
            logger.error(f"Không thể tạo ảnh fallback bằng PIL: {str(e)}")
            try:
                import subprocess
                # Sử dụng FFmpeg để sinh ra file ảnh JPG hợp lệ (tránh crash MoviePy do file text sai định dạng)
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"color=c=gray:s={width}x{height}",
                    "-vframes", "1",
                    str(output_path)
                ]
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                logger.info(f"Đã sử dụng FFmpeg tạo ảnh tĩnh fallback tại: {output_path}")
            except Exception as ffmpeg_err:
                logger.error(f"Không thể tạo ảnh fallback bằng cả FFmpeg: {str(ffmpeg_err)}")

image_generator = ImageGenerator()
