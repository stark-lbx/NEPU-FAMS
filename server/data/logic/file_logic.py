"""
文件上传下载、权限校验 业务逻辑
不得出现任何SQL语句
"""
from typing import Any, Dict, List, Optional, Tuple
import uuid
import os
from datetime import datetime

from data.basic.file_dao import FileDAO


class FileLogic:
    """文件存储业务逻辑"""

    ALLOWED_EXTENSIONS = {
        "jpg", "jpeg", "png", "gif", "bmp", "webp", "svg",
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        "txt", "csv", "zip", "rar",
    }

    def __init__(self, db_config: Dict, file_config: Dict):
        self.file_dao = FileDAO(db_config)
        self.upload_dir = file_config.get("upload_dir", "./uploads")
        self.max_size_mb = file_config.get("max_size_mb", 20)
        self.allowed_types = file_config.get("allowed_types", list(self.ALLOWED_EXTENSIONS))
        os.makedirs(self.upload_dir, exist_ok=True)

    def upload_file(self, file_content: bytes, original_name: str,
                    biz_type: str, biz_id: int, uploader_id: int) -> Optional[Dict]:
        """上传文件"""
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        if ext not in self.allowed_types:
            return {"error": f"不支持的文件类型: {ext}"}

        size_mb = len(file_content) / (1024 * 1024)
        if size_mb > self.max_size_mb:
            return {"error": f"文件大小超过限制 ({self.max_size_mb}MB)"}

        # 生成存储文件名
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        date_dir = datetime.now().strftime("%Y/%m/%d")
        store_dir = os.path.join(self.upload_dir, date_dir)
        os.makedirs(store_dir, exist_ok=True)
        file_path = os.path.join(store_dir, stored_name)

        with open(file_path, "wb") as f:
            f.write(file_content)

        file_id = self.file_dao.insert_file({
            "file_name": original_name,
            "file_path": file_path,
            "file_size": len(file_content),
            "file_type": ext,
            "biz_type": biz_type,
            "biz_id": biz_id,
            "uploader_id": uploader_id,
        })
        return {"file_id": file_id, "file_name": original_name,
                "file_path": file_path, "file_size": len(file_content)}

    def get_file_info(self, file_id: int) -> Optional[Dict]:
        return self.file_dao.get_file_by_id(file_id)

    def get_file_content(self, file_id: int) -> Optional[bytes]:
        """获取文件内容"""
        file_info = self.file_dao.get_file_by_id(file_id)
        if not file_info:
            return None
        path = file_info["file_path"]
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    def list_files(self, biz_type: str = "", biz_id: int = 0,
                   uploader_id: int = 0,
                   page_num: int = 1, page_size: int = 20) -> Tuple[List, int]:
        return self.file_dao.list_files(biz_type, biz_id, uploader_id, page_num, page_size)

    def delete_file(self, file_id: int) -> bool:
        file_info = self.file_dao.get_file_by_id(file_id)
        if not file_info:
            return False
        path = file_info["file_path"]
        if os.path.exists(path):
            os.remove(path)
        self.file_dao.delete_file(file_id)
        return True
