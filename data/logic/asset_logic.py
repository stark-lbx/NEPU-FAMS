from data.basic.asset_dao import AssetDao, AssetStatusLogDao
from common.utils import generate_biz_id, now_str
from common.log import get_logger

logger = get_logger("asset_logic")


class AssetLogic:
    def __init__(self, db_path: str = "fams.db"):
        self.asset_dao = AssetDao(db_path)
        self.status_log_dao = AssetStatusLogDao(db_path)

    def create_asset(self, asset_data: dict) -> str:
        """新增资产，生成biz_id"""
        asset_data["biz_id"] = generate_biz_id()
        self.asset_dao.insert(asset_data)
        logger.info(f"新增资产成功: {asset_data['biz_id']}")
        return asset_data["biz_id"]

    def get_asset(self, biz_id: str):
        return self.asset_dao.select_by_biz_id(biz_id)

    def list_asset(self, dept_biz_id: str, status_code: str = "", page: int = 1, page_size: int = 20):
        offset = (page - 1) * page_size
        total = self.asset_dao.count_by_dept_status(dept_biz_id, status_code)
        data = self.asset_dao.list_by_dept_status(dept_biz_id, status_code, page_size, offset)
        return data, total

    def update_status(self, asset_biz_id: str, new_status_code: str,
                      oper_user_biz_id: str, oper_desc: str = "") -> bool:
        """更新资产状态，同时写入变更流水"""
        asset = self.asset_dao.select_by_biz_id(asset_biz_id)
        if not asset:
            raise Exception("资产不存在")

        old_status = asset["current_status_code"]
        if old_status == new_status_code:
            return True

        # 更新主表状态
        success = self.asset_dao.update_by_biz_id(asset_biz_id, {"current_status_code": new_status_code})
        if success:
            # 写入状态流水
            self.status_log_dao.insert({
                "asset_biz_id": asset_biz_id,
                "old_status_code": old_status,
                "new_status_code": new_status_code,
                "oper_user_biz_id": oper_user_biz_id,
                "oper_desc": oper_desc
            })
            logger.info(f"资产状态变更: {asset_biz_id} {old_status} -> {new_status_code}")
        return success