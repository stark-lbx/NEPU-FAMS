"""
统计报表 DAO — 单库查询（不跨库 JOIN）
所有联表操作在 Logic 层完成
"""
from typing import Dict, List, Optional
from .base_dao import BaseDAO


class ReportAssetDAO(BaseDAO):
    """资产统计 — 仅查 asset_core_db"""

    def dept_asset_count(self, dept_id: int = 0) -> List[Dict]:
        if dept_id:
            sql = """SELECT dept_id AS dept_id, COUNT(*) AS count
                     FROM asset_info WHERE dept_id = :dept_id
                     GROUP BY dept_id"""
            return self._execute(sql, {"dept_id": dept_id})
        sql = """SELECT dept_id AS dept_id, COUNT(*) AS count
                 FROM asset_info
                 GROUP BY dept_id
                 ORDER BY count DESC"""
        return self._execute(sql, {})

    def status_distribution(self, dept_id: int = 0) -> List[Dict]:
        """
        返回 [{ status_id, status_name, value }, ...]
        JOIN asset_status 表把数字状态翻译成中文名
        """
        if dept_id:
            sql = """SELECT a.status AS status_id,
                            COALESCE(s.status_name, CONCAT('状态', a.status)) AS status_name,
                            COUNT(*) AS value
                     FROM asset_info a
                     LEFT JOIN asset_status s ON a.status = s.id
                     WHERE a.dept_id = :dept_id
                     GROUP BY a.status, s.status_name
                     ORDER BY a.status"""
            return self._execute(sql, {"dept_id": dept_id})
        sql = """SELECT a.status AS status_id,
                        COALESCE(s.status_name, CONCAT('状态', a.status)) AS status_name,
                        COUNT(*) AS value
                 FROM asset_info a
                 LEFT JOIN asset_status s ON a.status = s.id
                 GROUP BY a.status, s.status_name
                 ORDER BY a.status"""
        return self._execute(sql, {})

    def category_distribution(self, dept_id: int = 0) -> List[Dict]:
        if dept_id:
            sql = """SELECT c.category_name AS name, COUNT(a.asset_id) AS value
                     FROM asset_info a
                     JOIN asset_category c ON a.category_id = c.category_id
                     WHERE a.dept_id = :dept_id
                     GROUP BY c.category_name
                     ORDER BY value DESC"""
            return self._execute(sql, {"dept_id": dept_id})
        sql = """SELECT c.category_name AS name, COUNT(a.asset_id) AS value
                 FROM asset_info a
                 JOIN asset_category c ON a.category_id = c.category_id
                 GROUP BY c.category_name
                 ORDER BY value DESC"""
        return self._execute(sql, {})

    def total_count(self, dept_id: int = 0) -> int:
        if dept_id:
            sql = "SELECT COUNT(*) FROM asset_info WHERE dept_id = :dept_id"
            return self._execute_scalar(sql, {"dept_id": dept_id})
        sql = "SELECT COUNT(*) FROM asset_info"
        return self._execute_scalar(sql, {})

    def monthly_new_assets(self, dept_id: int = 0) -> List[Dict]:
        # SQLAlchemy text() 走 pymysql 不需要 %% 转义，直接写 %Y-%m
        if dept_id:
            sql = """SELECT DATE_FORMAT(create_time, '%Y-%m') AS month,
                            COUNT(*) AS count
                     FROM asset_info
                     WHERE dept_id = :dept_id
                       AND create_time >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
                     GROUP BY month
                     ORDER BY month"""
            return self._execute(sql, {"dept_id": dept_id})
        sql = """SELECT DATE_FORMAT(create_time, '%Y-%m') AS month,
                       COUNT(*) AS count
                FROM asset_info
                WHERE create_time >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
                GROUP BY month
                ORDER BY month"""
        return self._execute(sql, {})


class ReportRepairDAO(BaseDAO):
    """维修统计 — 仅查 repair_db"""

    def pending_count(self, dept_id: int = 0) -> int:
        if dept_id:
            sql = "SELECT COUNT(*) FROM repair_order WHERE status = 'PENDING_REPAIR' AND dept_id = :dept_id"
            return self._execute_scalar(sql, {"dept_id": dept_id}) or 0
        sql = "SELECT COUNT(*) FROM repair_order WHERE status = 'PENDING_REPAIR'"
        return self._execute_scalar(sql, {}) or 0

    def in_progress_count(self, dept_id: int = 0) -> int:
        """维修中的工单数 — 维修工已接单状态
        旧版用 'REPAIRING' (现已废弃为资产物理态)，改为 'REPAIR_ACCEPTED'
        """
        if dept_id:
            sql = "SELECT COUNT(*) FROM repair_order WHERE status = 'REPAIR_ACCEPTED' AND dept_id = :dept_id"
            return self._execute_scalar(sql, {"dept_id": dept_id}) or 0
        sql = "SELECT COUNT(*) FROM repair_order WHERE status = 'REPAIR_ACCEPTED'"
        return self._execute_scalar(sql, {}) or 0

    def pending_acceptance_count(self, dept_id: int = 0) -> int:
        if dept_id:
            sql = "SELECT COUNT(*) FROM repair_order WHERE status = 'PENDING_ACCEPTANCE' AND dept_id = :dept_id"
            return self._execute_scalar(sql, {"dept_id": dept_id}) or 0
        sql = "SELECT COUNT(*) FROM repair_order WHERE status = 'PENDING_ACCEPTANCE'"
        return self._execute_scalar(sql, {}) or 0

    def completed_this_month_count(self, dept_id: int = 0) -> int:
        if dept_id:
            sql = """SELECT COUNT(*) FROM repair_order
                     WHERE status IN ('ACCEPTANCE_PASSED','ACCEPTANCE_REJECTED')
                     AND MONTH(update_time) = MONTH(NOW())
                     AND YEAR(update_time) = YEAR(NOW())
                     AND dept_id = :dept_id"""
            return self._execute_scalar(sql, {"dept_id": dept_id}) or 0
        sql = """SELECT COUNT(*) FROM repair_order
                 WHERE status IN ('ACCEPTANCE_PASSED','ACCEPTANCE_REJECTED')
                 AND MONTH(update_time) = MONTH(NOW())
                 AND YEAR(update_time) = YEAR(NOW())"""
        return self._execute_scalar(sql, {}) or 0

    def monthly_stats(self, dept_id: int = 0) -> List[Dict]:
        if dept_id:
            sql = """SELECT DATE_FORMAT(create_time, '%Y-%m') AS month,
                            COUNT(*) AS submitted,
                            SUM(CASE WHEN status IN ('ACCEPTANCE_PASSED','ACCEPTANCE_REJECTED')
                                THEN 1 ELSE 0 END) AS completed
                     FROM repair_order
                     WHERE dept_id = :dept_id
                       AND create_time >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
                     GROUP BY month
                     ORDER BY month"""
            return self._execute(sql, {"dept_id": dept_id})
        sql = """SELECT DATE_FORMAT(create_time, '%Y-%m') AS month,
                       COUNT(*) AS submitted,
                       SUM(CASE WHEN status IN ('ACCEPTANCE_PASSED','ACCEPTANCE_REJECTED')
                           THEN 1 ELSE 0 END) AS completed
                FROM repair_order
                WHERE create_time >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
                GROUP BY month
                ORDER BY month"""
        return self._execute(sql, {})

    def status_summary(self, dept_id: int = 0) -> List[Dict]:
        if dept_id:
            sql = """SELECT status AS name, COUNT(*) AS value
                     FROM repair_order WHERE dept_id = :dept_id
                     GROUP BY status"""
            return self._execute(sql, {"dept_id": dept_id})
        sql = """SELECT status AS name, COUNT(*) AS value
                 FROM repair_order
                 GROUP BY status"""
        return self._execute(sql, {})

    def dept_repair_count(self, dept_id: int = 0) -> List[Dict]:
        if dept_id:
            sql = """SELECT dept_id AS dept_id, COUNT(*) AS count
                     FROM repair_order WHERE dept_id = :dept_id
                     GROUP BY dept_id
                     ORDER BY count DESC"""
            return self._execute(sql, {"dept_id": dept_id})
        sql = """SELECT dept_id AS dept_id, COUNT(*) AS count
                 FROM repair_order
                 GROUP BY dept_id
                 ORDER BY count DESC"""
        return self._execute(sql, {})

    def total_count(self, dept_id: int = 0) -> int:
        if dept_id:
            sql = "SELECT COUNT(*) FROM repair_order WHERE dept_id = :dept_id"
            return self._execute_scalar(sql, {"dept_id": dept_id})
        sql = "SELECT COUNT(*) FROM repair_order"
        return self._execute_scalar(sql, {})


class ReportInventoryDAO(BaseDAO):
    """盘点统计 — 仅查 inventory_db"""

    def quarterly_diff(self, dept_id: int = 0) -> List[Dict]:
        sql = """SELECT t.task_name AS label,
                        MAX(r.surplus_items) AS surplus,
                        MAX(r.shortage_items) AS shortage
                 FROM check_task t
                 LEFT JOIN check_diff_report r ON t.task_id = r.task_id
                 WHERE r.report_id IS NOT NULL
                 GROUP BY t.task_id
                 ORDER BY t.create_time DESC
                 LIMIT 8"""
        return self._execute(sql, {})

    def task_completion_stats(self, dept_id: int = 0) -> List[Dict]:
        sql = """SELECT status AS name, COUNT(*) AS value
                 FROM check_task
                 GROUP BY status"""
        return self._execute(sql, {})

    def total_task_count(self, dept_id: int = 0) -> int:
        sql = "SELECT COUNT(*) FROM check_task"
        return self._execute_scalar(sql, {})


class ReportApplyDAO(BaseDAO):
    """申请统计 — 仅查 workflow_db"""

    def pending_count(self, dept_id: int = 0) -> int:
        if dept_id:
            sql = "SELECT COUNT(*) FROM asset_apply WHERE status IN ('PENDING_COLLEGE','PENDING_SCHOOL') AND dept_id = :dept_id"
            return self._execute_scalar(sql, {"dept_id": dept_id}) or 0
        sql = "SELECT COUNT(*) FROM asset_apply WHERE status IN ('PENDING_COLLEGE','PENDING_SCHOOL')"
        return self._execute_scalar(sql, {}) or 0
