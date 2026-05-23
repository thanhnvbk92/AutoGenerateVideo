import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.lock = threading.Lock()
        self._initialize_db()

    def _initialize_db(self):
        """Khởi tạo file cơ sở dữ liệu JSON nếu chưa tồn tại."""
        with self.lock:
            try:
                self.filepath.parent.mkdir(parents=True, exist_ok=True)
                if not self.filepath.exists():
                    with open(self.filepath, "w", encoding="utf-8") as f:
                        json.dump({}, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Không thể khởi tạo cơ sở dữ liệu Task: {str(e)}")

    def _read_db(self) -> Dict[str, Any]:
        """Đọc toàn bộ dữ liệu từ file JSON."""
        try:
            if self.filepath.exists():
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi đọc file cơ sở dữ liệu Task: {str(e)}")
        return {}

    def _write_db(self, data: Dict[str, Any]):
        """Ghi dữ liệu vào file JSON."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Lỗi khi ghi file cơ sở dữ liệu Task: {str(e)}")

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin của một task theo ID."""
        with self.lock:
            db = self._read_db()
            return db.get(task_id)

    def set_task(self, task_id: str, task_data: Dict[str, Any]):
        """Lưu mới hoặc ghi đè thông tin một task."""
        import time
        with self.lock:
            db = self._read_db()
            task_data["last_updated"] = time.time()
            db[task_id] = task_data
            self._write_db(db)

    def update_task(self, task_id: str, updates: Dict[str, Any]):
        """Cập nhật một phần thông tin của một task."""
        import time
        with self.lock:
            db = self._read_db()
            updates["last_updated"] = time.time()
            if task_id in db:
                db[task_id].update(updates)
                self._write_db(db)
            else:
                # Nếu task chưa tồn tại, tạo mới với các trường cập nhật
                db[task_id] = updates
                self._write_db(db)

# Khởi tạo một đối tượng toàn cục dùng chung cho cả backend app
from app.config import settings
task_manager = TaskManager(settings.STORAGE_DIR / "tasks_db.json")
