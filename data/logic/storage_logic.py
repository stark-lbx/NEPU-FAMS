from data.basic.asset_dao import AssetAttachDao
from common.utils import generate_biz_id
from common.log import get_logger
import os

logger = get_logger("storage_logic")

# 简化版：本地存储替代FastDFS，实训环境快速落地
STORAGE_BASE_PATH = "./upload_files"


class StorageLogic:
    def __init__(self, db_path: str = "fams.db"):
        self.attach_dao = AssetAttachDao(db_path)
        os.makedirs(STORAGE_BASE_PATH, exist_ok=True)

    def upload_attach(self, asset_biz_id: str, attach_name: str, file_data: bytes,
                      attach_type: int, upload_user_biz_id: str) -> tuple:
        """上传附件，保存本地+写数据库"""
        biz_id = generate_biz_id()
        # 生成存储路径
        ext = os.path.splitext(attach_name)[1]
        file_path = f"{STORAGE_BASE_PATH}/{biz_id}{ext}"

        # 写入文件
        with open(file_path, "wb") as f:
            f.write(file_data)

        file_size = len(file_data)
        # 写数据库
        self.attach_dao.insert({
            "biz_id": biz_id,
            "asset_biz_id": asset_biz_id,
            "attach_name": attach_name,
            "attach_path": file_path,
            "attach_type": attach_type,
            "file_size": file_size,
            "upload_user_biz_id": upload_user_biz_id
        })
        logger.info(f"上传附件成功: {biz_id} {attach_name}")
        return biz_id, file_path

    def list_attach(self, asset_biz_id: str):
        return self.attach_dao.list_by_asset(asset_biz_id)

    def delete_attach(self, attach_biz_id: str) -> bool:
        attach = self.attach_dao.select_by_biz_id(attach_biz_id)
        if not attach:
            raise Exception("附件不存在")
        # 删除本地文件
        if os.path.exists(attach["attach_path"]):
            os.remove(attach["attach_path"])
        # 软删除数据库记录
        self.attach_dao.delete_by_biz_id(attach_biz_id)
        logger.info(f"删除附件: {attach_biz_id}")
        return True

    def get_file_path(self, attach_biz_id: str) -> str:
        attach = self.attach_dao.select_by_biz_id(attach_biz_id)
        if not attach:
            raise Exception("附件不存在")
        return attach["attach_path"]