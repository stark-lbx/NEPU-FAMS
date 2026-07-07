from data.basic.check_dao import CheckTaskDao, CheckDetailDao
from data.basic.asset_dao import AssetDao
from common.utils import generate_biz_id
from common.log import get_logger

logger = get_logger("check_logic")

class CheckLogic:
    def __init__(self, db_path: str = "fams.db"):
        self.task_dao = CheckTaskDao(db_path)
        self.detail_dao = CheckDetailDao(db_path)
        self.asset_dao = AssetDao(db_path)

    def create_task(self, task_data: dict) -> str:
        task_data["biz_id"] = generate_biz_id()
        task_data["task_status"] = "WAIT"
        self.task_dao.insert(task_data)
        logger.info(f"创建盘点任务: {task_data['biz_id']}")
        return task_data["biz_id"]

    def submit_detail(self, detail_data: dict) -> bool:
        """提交盘点明细，存在则更新，不存在则插入"""
        exist = self.detail_dao.get_by_task_asset(detail_data["task_biz_id"], detail_data["asset_biz_id"])
        if exist:
            update_data = {
                "actual_exist": detail_data["actual_exist"],
                "real_location": detail_data.get("real_location", ""),
                "check_remark": detail_data.get("check_remark", ""),
                "check_user_biz_id": detail_data["check_user_biz_id"]
            }
            self.detail_dao.update_by_biz_id(exist["biz_id"], update_data)
        else:
            detail_data["biz_id"] = generate_biz_id()
            self.detail_dao.insert(detail_data)
        logger.info(f"提交盘点明细: {detail_data['task_biz_id']} {detail_data['asset_biz_id']}")
        return True

    def list_task_by_dept(self, dept_biz_id: str):
        return self.task_dao.list_by_dept(dept_biz_id)

    def get_task_detail(self, task_biz_id: str):
        return self.detail_dao.list_by_task(task_biz_id)