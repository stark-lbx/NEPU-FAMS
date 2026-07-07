from .base_dao import BaseDao

class CheckTaskDao(BaseDao):
    table_name = "fams_check_task"

    def list_by_dept(self, target_dept_biz_id: str):
        return self.list_by_condition({"target_dept_biz_id": target_dept_biz_id}, order_by="create_time DESC")


class CheckDetailDao(BaseDao):
    table_name = "fams_check_detail"

    def list_by_task(self, task_biz_id: str):
        return self.list_by_condition({"task_biz_id": task_biz_id}, order_by="check_time DESC")

    def get_by_task_asset(self, task_biz_id: str, asset_biz_id: str):
        sql = "SELECT * FROM fams_check_detail WHERE task_biz_id = ? AND asset_biz_id = ?"
        conn = self._get_conn()
        row = conn.execute(sql, (task_biz_id, asset_biz_id)).fetchone()
        conn.close()
        return dict(row) if row else None