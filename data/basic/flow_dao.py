from .base_dao import BaseDao, _strip_internal
from typing import Dict, Any, Optional

class AuditFlowDao(BaseDao):
    table_name = "fams_audit_flow"

    def select_by_biz_id(self, biz_id: str) -> Optional[Dict[str, Any]]:
        """覆写：fams_audit_flow 表没有 is_delete 列"""
        sql = f"SELECT * FROM {self.table_name} WHERE biz_id = ?"
        conn = self._get_conn()
        row = conn.execute(sql, (biz_id,)).fetchone()
        conn.close()
        return _strip_internal(dict(row)) if row else None

    def get_by_business(self, business_type: int, business_biz_id: str):
        sql = "SELECT * FROM fams_audit_flow WHERE business_type = ? AND business_biz_id = ?"
        conn = self._get_conn()
        row = conn.execute(sql, (business_type, business_biz_id)).fetchone()
        conn.close()
        return _strip_internal(dict(row)) if row else None


class BorrowDao(BaseDao):
    table_name = "fams_asset_borrow"

    def active_by_asset(self, asset_biz_id: str):
        """查同一资产是否有进行中的领用流程（非终态）"""
        sql = """SELECT borrow_status, biz_id FROM fams_asset_borrow
                 WHERE asset_biz_id = ? AND is_delete = 0
                 AND borrow_status NOT IN ('REJECT', 'RETURN')"""
        conn = self._get_conn()
        rows = conn.execute(sql, (asset_biz_id,)).fetchall()
        conn.close()
        return [_strip_internal(dict(r)) for r in rows]

    def list_by_user(self, borrow_user_biz_id: str):
        return self.list_by_condition({"borrow_user_biz_id": borrow_user_biz_id}, order_by="create_time DESC")

    def list_by_dept(self, dept_biz_id: str):
        sql = """SELECT b.* FROM fams_asset_borrow b
                 LEFT JOIN fams_asset a ON b.asset_biz_id = a.biz_id
                 WHERE a.dept_biz_id = ? AND b.is_delete = 0
                 ORDER BY b.create_time DESC"""
        conn = self._get_conn()
        rows = conn.execute(sql, (dept_biz_id,)).fetchall()
        conn.close()
        return [_strip_internal(dict(r)) for r in rows]


class RepairDao(BaseDao):
    table_name = "fams_repair_workorder"

    def active_by_asset(self, asset_biz_id: str):
        """查同一资产是否有进行中的报修工单（非终态）"""
        sql = """SELECT order_status, biz_id FROM fams_repair_workorder
                 WHERE asset_biz_id = ? AND is_delete = 0
                 AND order_status NOT IN ('REJECT', 'COMPLETED')"""
        conn = self._get_conn()
        rows = conn.execute(sql, (asset_biz_id,)).fetchall()
        conn.close()
        return [_strip_internal(dict(r)) for r in rows]

    def list_by_report_user(self, report_user_biz_id: str):
        return self.list_by_condition({"report_user_biz_id": report_user_biz_id}, order_by="create_time DESC")

    def list_by_dept(self, dept_biz_id: str):
        sql = """SELECT r.* FROM fams_repair_workorder r
                 LEFT JOIN fams_asset a ON r.asset_biz_id = a.biz_id
                 WHERE a.dept_biz_id = ? AND r.is_delete = 0
                 ORDER BY r.create_time DESC"""
        conn = self._get_conn()
        rows = conn.execute(sql, (dept_biz_id,)).fetchall()
        conn.close()
        return [_strip_internal(dict(r)) for r in rows]


class ScrapDao(BaseDao):
    table_name = "fams_asset_scrap"

    def active_by_asset(self, asset_biz_id: str):
        """查同一资产是否有进行中的报废流程（非终态）"""
        sql = """SELECT scrap_status, biz_id FROM fams_asset_scrap
                 WHERE asset_biz_id = ? AND is_delete = 0
                 AND scrap_status NOT IN ('SCRAPPED', 'REJECT')"""
        conn = self._get_conn()
        rows = conn.execute(sql, (asset_biz_id,)).fetchall()
        conn.close()
        return [_strip_internal(dict(r)) for r in rows]

    def list_by_apply_user(self, apply_user_biz_id: str):
        return self.list_by_condition({"apply_user_biz_id": apply_user_biz_id}, order_by="create_time DESC")

    def list_by_dept(self, dept_biz_id: str):
        sql = """SELECT s.* FROM fams_asset_scrap s
                 LEFT JOIN fams_asset a ON s.asset_biz_id = a.biz_id
                 WHERE a.dept_biz_id = ? AND s.is_delete = 0
                 ORDER BY s.create_time DESC"""
        conn = self._get_conn()
        rows = conn.execute(sql, (dept_biz_id,)).fetchall()
        conn.close()
        return [_strip_internal(dict(r)) for r in rows]