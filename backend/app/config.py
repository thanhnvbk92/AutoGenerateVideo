import os
from pathlib import Path
from dotenv import load_dotenv

# Tải file .env từ thư mục backend
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

class Settings:
    # Cấu hình máy chủ
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", 8000))
    
    # Cấu hình API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Thư mục lưu trữ assets
    STORAGE_DIR: Path = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage"))
    
    # Đảm bảo các thư mục tồn tại
    def create_directories(self):
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        # Các thư mục con để lưu trữ asset theo dự án
        (self.STORAGE_DIR / "projects").mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.create_directories()
