from data.basic.dict_dao import DictDao
from common.utils import generate_biz_id
from common.log import get_logger

logger = get_logger("dict_logic")

class DictLogic:
    def __init__(self, db_path: str = "fams.db"):
        self.dict_dao = DictDao(db_path)

    def list_by_type(self, dict_type: str):
        """按类型查询字典列表"""
        return self.dict_dao.list_by_type(dict_type)

    def list_types(self):
        """获取所有字典分类"""
        return self.dict_dao.list_types()

    def create_dict(self, dict_data: dict) -> str:
        """新增字典项"""
        dict_data["biz_id"] = generate_biz_id()
        self.dict_dao.insert(dict_data)
        logger.info(f"新增字典: {dict_data['dict_type']} - {dict_data['dict_code']}")
        return dict_data["biz_id"]

    def update_dict(self, biz_id: str, dict_data: dict) -> bool:
        """更新字典项"""
        return self.dict_dao.update_by_biz_id(biz_id, dict_data)

    def delete_dict(self, biz_id: str) -> bool:
        """软删除字典项"""
        return self.dict_dao.delete_by_biz_id(biz_id)