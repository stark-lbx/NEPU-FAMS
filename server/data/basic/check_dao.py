"""
盘点任务/明细/差异报告 DAO
所有SQL语句集中管理已全局修复时间格式问题：兼容前端ISO UTC时间、自动转MySQL标准时间格式
"""
from typing import Any, Dict, List, Optional
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from .base_dao import BaseDAO


def format_mysql_datetime(raw_val: Any) -> Optional[str]:
    """
    兼容：空值 / datetime对象 / UTC ISO字符串 / 普通时间字符串
    自动 UTC -> 北京时间(+8)
    """
    if not raw_val:
        return None

    # 原生datetime对象处理
    if isinstance(raw_val, datetime):
        if raw_val.tzinfo is None:
            return raw_val.strftime("%Y-%m-%d %H:%M:%S")
        bj_dt = raw_val.astimezone(ZoneInfo("Asia/Shanghai"))
        return bj_dt.strftime("%Y-%m-%d %H:%M:%S")
    val_str = str(raw_val).strip()

    # 处理前端UTC ISO格式 2026-07-10T16:00:00.000Z
    if "T" in val_str:
        iso_fixed = val_str.replace("Z", "+00:00")
        utc_dt = datetime.fromisoformat(iso_fixed)
        bj_dt = utc_dt.astimezone(ZoneInfo("Asia/Shanghai"))
        return bj_dt.strftime("%Y-%m-%d %H:%M:%S")

    # 已经是标准时间直接返回
    return val_str


def format_id_list(raw_val: Any) -> Optional[str]:
    """
    ID列表格式化：Python列表/元组 → 逗号分隔纯字符串
    彻底解决 [2,5] 带方括号存入数据库、导致 FIND_IN_SET 失效的问题
    """
    if not raw_val:
        return None

    if isinstance(raw_val, (list, tuple)):
        return ",".join(str(i) for i in raw_val if i is not None)

    val_str = str(raw_val).strip()
    if val_str.startswith("[") and val_str.endswith("]"):
        val_str = val_str[1:-1].strip()
    return val_str


def normalize_asset_status(status_code: Any) -> Optional[str]:
    """
    资产状态码标准化：对齐 asset_status 表的标准枚举
    兼容常见错误写法，自动映射为标准值
    """
    if not status_code:
        return None

    code = str(status_code).strip().upper()

    # 错误写法 → 标准值 映射表
    STATUS_MAP = {
        "IN_USE": "USING",
        "INUSE": "USING",
        "USING": "USING",
        "IDLE": "IDLE",
        "REPAIR": "REPAIRING",
        "REPAIRING": "REPAIRING",
        "ABANDONED": "ABANDON",
        "ABANDON": "ABANDON",
        "FLOW": "FLOWING",
        "FLOWING": "FLOWING",
        "UNKNOWN": "UNKNOWN",
    }

    return STATUS_MAP.get(code, "UNKNOWN")


class CheckTaskDAO(BaseDAO):
    """盘点任务数据访问"""

    def insert_task(self, task: Dict) -> int:
        task["start_time"] = format_mysql_datetime(task.get("start_time"))
        task["end_time"] = format_mysql_datetime(task.get("end_time"))
        task["scope_dept_ids"] = format_id_list(task.get("scope_dept_ids"))
        task["checker_ids"] = format_id_list(task.get("checker_ids"))

        sql = """INSERT INTO check_task (task_name, scope_type, scope_dept_ids, start_time,
                                         end_time, manager_id, checker_ids, status)
                 VALUES (:task_name, :scope_type, :scope_dept_ids, :start_time,
                         :end_time, :manager_id, :checker_ids, :status)"""
        return self._execute_insert(sql, task)

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        sql = """SELECT t.task_id, t.task_name, t.scope_type, t.scope_dept_ids, t.start_time, t.end_time, t.manager_id,
                     u.nickname AS manager_name, t.checker_ids, t.status, t.create_time
                 FROM check_task t
                 LEFT JOIN user_auth_db.sys_user u ON t.manager_id = u.user_id
                 WHERE t.task_id = :task_id"""
        return self._execute_one(sql, {"task_id": task_id})

    def list_tasks(self, status: str = "", manager_id: int = 0, dept_id: int = 0,
                   page_num: int = 1, page_size: int = 10,
                   current_user: Optional[Dict] = None) -> tuple:
        conditions = ["1=1"]
        params = {}

        if status:
            conditions.append("t.status = :status")
            params["status"] = status
        if manager_id:
            conditions.append("t.manager_id = :manager_id")
            params["manager_id"] = manager_id
        if dept_id:
            conditions.append(
                "(t.scope_type = 'ALL' OR (t.scope_type = 'DEPT' AND FIND_IN_SET(:dept_id_str, t.scope_dept_ids)))"
            )
            params["dept_id_str"] = str(dept_id)

        # 数据权限逻辑
        if current_user:
            user_roles = current_user.get("role_keys") or []
            user_id = current_user.get("user_id") or 0
            user_dept_id = current_user.get("dept_id") or 0

            if "admin" in user_roles or "SCHOOL_ADMIN" in user_roles:
                pass
            elif "college_admin" in user_roles and user_dept_id:
                conditions.append("(t.scope_type = 'ALL' OR FIND_IN_SET(:user_dept, t.scope_dept_ids))")
                params["user_dept"] = str(user_dept_id)
            elif user_id:
                conditions.append("FIND_IN_SET(:user_id, t.checker_ids)")
                params["user_id"] = str(user_id)

        where_clause = " AND ".join(conditions)

        count_sql = f"SELECT COUNT(*) FROM check_task t WHERE {where_clause}"
        total = self._execute_scalar(count_sql, params)

        params["offset"] = (page_num - 1) * page_size
        params["limit"] = page_size
        list_sql = f"""SELECT t.task_id, t.task_name, t.scope_type, t.scope_dept_ids,
                              t.start_time, t.end_time, t.manager_id,
                              u.nickname AS manager_name, t.checker_ids,
                              t.status, t.create_time
                       FROM check_task t
                       LEFT JOIN user_auth_db.sys_user u ON t.manager_id = u.user_id
                       WHERE {where_clause}
                       ORDER BY t.create_time DESC
                       LIMIT :limit OFFSET :offset"""
        data = self._execute(list_sql, params)
        return data, total

    def update_task_status(self, task_id: int, status: str) -> int:
        sql = """UPDATE check_task
                 SET status = :status
                 WHERE task_id = :task_id"""
        return self._execute_update(sql, {"task_id": task_id, "status": status})

    def delete_task(self, task_id: int) -> int:
        sql = """DELETE
                 FROM check_task
                 WHERE task_id = :task_id"""
        return self._execute_update(sql, {"task_id": task_id})

    def update_task(self, task: Dict) -> int:
        task["start_time"] = format_mysql_datetime(task.get("start_time"))
        task["end_time"] = format_mysql_datetime(task.get("end_time"))
        task["scope_dept_ids"] = format_id_list(task.get("scope_dept_ids"))
        task["checker_ids"] = format_id_list(task.get("checker_ids"))

        sql = """UPDATE check_task
                 SET task_name  = :task_name, scope_type = :scope_type, scope_dept_ids = :scope_dept_ids,
                     start_time = :start_time, end_time = :end_time, checker_ids = :checker_ids
                 WHERE task_id = :task_id"""
        return self._execute_update(sql, task)


class CheckDetailDAO(BaseDAO):
    """盘点明细数据访问"""

    def batch_insert(self, details: List[Dict]) -> int:
        """批量插入盘点明细，自动标准化资产状态码"""
        for item in details:
            if item.get("create_time"):
                item["create_time"] = format_mysql_datetime(item["create_time"])
            # 核心修复：标准化账面状态、实盘状态，对齐 asset_status 表
            item["book_status"] = normalize_asset_status(item.get("book_status"))
            item["actual_status"] = normalize_asset_status(item.get("actual_status"))

        sql = """INSERT INTO check_detail (task_id, asset_id, asset_code, asset_name,
                                           asset_spec, book_location, book_status,
                                           actual_location, actual_status, diff_type, remark)
                 VALUES (:task_id, :asset_id, :asset_code, :asset_name, :asset_spec,
                         :book_location, :book_status, :actual_location, :actual_status,
                         :diff_type, :remark)"""
        return self._execute_batch(sql, details)

    def list_by_task(self, task_id: int) -> List[Dict]:
        sql = """SELECT detail_id, task_id, asset_id, asset_code, asset_name, asset_spec, book_location, book_status,
                     actual_location, actual_status, diff_type, remark, update_time
                 FROM check_detail
                 WHERE task_id = :task_id
                 ORDER BY detail_id"""
        return self._execute(sql, {"task_id": task_id})

    def upsert_detail(self, detail: Dict) -> int:
        """更新盘点明细，自动标准化资产状态码"""
        # 核心修复：写入前标准化状态值
        detail["book_status"] = normalize_asset_status(detail.get("book_status"))
        detail["actual_status"] = normalize_asset_status(detail.get("actual_status"))

        sql = """INSERT INTO check_detail (task_id, asset_id, asset_code, asset_name,
                                           asset_spec, book_location, book_status,
                                           actual_location, actual_status, diff_type, remark)
                 VALUES (:task_id, :asset_id, :asset_code, :asset_name, :asset_spec,
                         :book_location, :book_status, :actual_location, :actual_status,
                         :diff_type, :remark)
                 ON DUPLICATE KEY UPDATE 
                     actual_location = VALUES(actual_location),
                     actual_status = VALUES(actual_status),
                     diff_type = VALUES(diff_type),
                     remark = VALUES(remark),
                     update_time = NOW()"""
        return self._execute_update(sql, detail)

    def delete_by_task(self, task_id: int) -> int:
        sql = """DELETE
                 FROM check_detail
                 WHERE task_id = :task_id"""
        return self._execute_update(sql, {"task_id": task_id})

    def update_diff_type(self, detail_id: int, diff_type: str) -> int:
        """差异分析时回写单行 diff_type（独立方法避免 upsert 覆盖其他字段）"""
        sql = """UPDATE check_detail SET diff_type = :diff_type
                 WHERE detail_id = :detail_id"""
        return self._execute_update(sql, {"detail_id": detail_id, "diff_type": diff_type})


class CheckDiffReportDAO(BaseDAO):
    """盘点差异报告数据访问"""

    def insert_report(self, report: Dict) -> int:
        sql = """INSERT INTO check_diff_report (task_id, task_name, total_items, matched_items,
                                                surplus_items, shortage_items, mismatch_items,
                                                llm_analysis)
                 VALUES (:task_id, :task_name, :total_items, :matched_items,
                         :surplus_items, :shortage_items, :mismatch_items,
                         :llm_analysis)"""
        return self._execute_insert(sql, report)

    def get_by_task(self, task_id: int) -> Optional[Dict]:
        sql = """SELECT diff.report_id, diff.task_id, t.status as status, diff.task_name, 
                        diff.total_items, diff.matched_items, diff.surplus_items, diff.shortage_items,
                        diff.mismatch_items, diff.llm_analysis, diff.create_time
                 FROM check_diff_report diff
                 LEFT JOIN check_task t ON t.task_id = diff.task_id
                 WHERE diff.task_id = :task_id"""
        return self._execute_one(sql, {"task_id": task_id})