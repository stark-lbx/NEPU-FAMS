"""
申请审批 DAO
所有SQL语句集中管理
"""
from typing import Any, Dict, List, Optional, Tuple
from .base_dao import BaseDAO


class ApplyDAO(BaseDAO):
    """申请主表DAO"""

    def insert_apply(self, data: Dict) -> int:
        sql = """INSERT INTO asset_apply (apply_type, applicant_id, dept_id, asset_id,
                                          reason, expect_return_time, status, current_node)
                 VALUES (:apply_type, :applicant_id, :dept_id, :asset_id,
                         :reason, :expect_return_time, :status, :current_node)"""
        return self._execute_insert(sql, data)

    def get_apply_by_id(self, apply_id: int) -> Optional[Dict]:
        sql = """SELECT a.apply_id, a.apply_type, a.applicant_id, u.nickname AS applicant_name,
                        a.dept_id, d.dept_name, a.asset_id, ast.asset_code, ast.asset_name,
                        a.reason, a.expect_return_time, a.status, a.current_node,
                        a.create_time, a.update_time
                 FROM asset_apply a
                 LEFT JOIN user_auth_db.sys_user u ON a.applicant_id = u.user_id
                 LEFT JOIN user_auth_db.sys_dept d ON a.dept_id = d.dept_id
                 LEFT JOIN asset_core_db.asset_info ast ON a.asset_id = ast.asset_id
                 WHERE a.apply_id = :apply_id"""
        return self._execute_one(sql, {"apply_id": apply_id})

    def list_my_applies(self, applicant_id: int, apply_type: str, status: str,
                        dept_id: int, page_num: int, page_size: int) -> Tuple:
        conditions = ["1=1"]
        params = {}
        if applicant_id:
            conditions.append("a.applicant_id = :applicant_id")
            params["applicant_id"] = applicant_id
        if apply_type:
            conditions.append("a.apply_type = :apply_type")
            params["apply_type"] = apply_type
        if status:
            conditions.append("a.status = :status")
            params["status"] = status
        if dept_id:
            conditions.append("a.dept_id = :dept_id")
            params["dept_id"] = dept_id
        where_clause = " AND ".join(conditions)

        count_sql = f"SELECT COUNT(*) FROM asset_apply a WHERE {where_clause}"
        total = self._execute_scalar(count_sql, params)

        params["offset"] = (page_num - 1) * page_size
        params["limit"] = page_size
        list_sql = f"""SELECT a.apply_id, a.apply_type, a.applicant_id, u.nickname AS applicant_name,
                              a.dept_id, d.dept_name, a.asset_id, ast.asset_code, ast.asset_name,
                              a.reason, a.expect_return_time, a.status, a.current_node, a.create_time
                       FROM asset_apply a
                       LEFT JOIN user_auth_db.sys_user u ON a.applicant_id = u.user_id
                       LEFT JOIN user_auth_db.sys_dept d ON a.dept_id = d.dept_id
                       LEFT JOIN asset_core_db.asset_info ast ON a.asset_id = ast.asset_id
                       WHERE {where_clause}
                       ORDER BY a.create_time DESC
                       LIMIT :limit OFFSET :offset"""
        return self._execute(list_sql, params), total

    def list_pending(self, approver_id: int, dept_id: int, apply_type: str,
                     page_num: int, page_size: int,
                     approver_roles: Optional[List[str]] = None) -> Tuple:
        """待审批列表：仅查询待院审、待校审两种状态

        严格按节点-角色匹配过滤可见范围：
          - college_admin：仅看 PENDING_COLLEGE
          - admin        ：仅看 PENDING_SCHOOL
          - 同时具备两者：可看全部（兼容角色并存场景）
        """
        roles = set(approver_roles or [])
        if "admin" in roles and "college_admin" in roles:
            allowed_statuses = ("PENDING_COLLEGE", "PENDING_SCHOOL")
        elif "admin" in roles:
            allowed_statuses = ("PENDING_SCHOOL",)
        elif "college_admin" in roles:
            allowed_statuses = ("PENDING_COLLEGE",)
        else:
            # 无任何审批角色：无可见待办
            return [], 0

        placeholders = ", ".join([f":pending_status_{i}" for i in range(len(allowed_statuses))])
        conditions = [f"a.status IN ({placeholders})"]
        params = {f"pending_status_{i}": s for i, s in enumerate(allowed_statuses)}
        if apply_type:
            conditions.append("a.apply_type = :apply_type")
            params["apply_type"] = apply_type
        # 院管额外受部门限制（校管不过滤，看全量 PENDING_SCHOOL）
        if dept_id and "admin" not in roles:
            conditions.append("a.dept_id = :dept_id")
            params["dept_id"] = dept_id
        where_clause = " AND ".join(conditions)

        count_sql = f"SELECT COUNT(*) FROM asset_apply a WHERE {where_clause}"
        total = self._execute_scalar(count_sql, params)

        params["offset"] = (page_num - 1) * page_size
        params["limit"] = page_size
        list_sql = f"""SELECT a.apply_id, a.apply_type, a.applicant_id, u.nickname AS applicant_name,
                              a.dept_id, d.dept_name, a.asset_id, ast.asset_code, ast.asset_name,
                              a.reason, a.expect_return_time, a.status, a.current_node, a.create_time
                       FROM asset_apply a
                       LEFT JOIN user_auth_db.sys_user u ON a.applicant_id = u.user_id
                       LEFT JOIN user_auth_db.sys_dept d ON a.dept_id = d.dept_id
                       LEFT JOIN asset_core_db.asset_info ast ON a.asset_id = ast.asset_id
                       WHERE {where_clause}
                       ORDER BY a.create_time DESC
                       LIMIT :limit OFFSET :offset"""
        return self._execute(list_sql, params), total

    def list_approved(self, dept_id: int, status: str, apply_type: str,
                      page_num: int, page_size: int) -> Tuple:
        """已审批记录列表（终态）
        :param status: 申请状态筛选。空=全部终态(APPROVED/REJECTED/CANCELLED)；
                       否则按指定 status 精确过滤
        :param apply_type: 申请类型筛选。空=全部；否则按 BORROW/RETURN/SCRAP 精确过滤
        """
        params = {}
        if status:
            # 按指定状态过滤（单个终态）
            conditions = ["a.status = :status"]
            params["status"] = status
        else:
            # 不传 status 时，返回全部终态
            conditions = ["a.status IN ('APPROVED', 'REJECTED', 'CANCELLED')"]
        if apply_type:
            conditions.append("a.apply_type = :apply_type")
            params["apply_type"] = apply_type
        if dept_id:
            conditions.append("a.dept_id = :dept_id")
            params["dept_id"] = dept_id
        where_clause = " AND ".join(conditions)

        count_sql = f"SELECT COUNT(*) FROM asset_apply a WHERE {where_clause}"
        total = self._execute_scalar(count_sql, params)

        params["offset"] = (page_num - 1) * page_size
        params["limit"] = page_size
        list_sql = f"""SELECT a.apply_id, a.apply_type, a.applicant_id, u.nickname AS applicant_name,
                              a.dept_id, d.dept_name, a.asset_id, ast.asset_code, ast.asset_name,
                              a.reason, a.expect_return_time, a.status, a.create_time
                       FROM asset_apply a
                       LEFT JOIN user_auth_db.sys_user u ON a.applicant_id = u.user_id
                       LEFT JOIN user_auth_db.sys_dept d ON a.dept_id = d.dept_id
                       LEFT JOIN asset_core_db.asset_info ast ON a.asset_id = ast.asset_id
                       WHERE {where_clause}
                       ORDER BY a.create_time DESC
                       LIMIT :limit OFFSET :offset"""
        return self._execute(list_sql, params), total

    def update_apply_status(self, apply_id: int, status: str, current_node: int) -> int:
        sql = """UPDATE asset_apply SET status = :status, current_node = :current_node
                 WHERE apply_id = :apply_id"""
        return self._execute_update(sql, {
            "apply_id": apply_id,
            "status": status,
            "current_node": current_node
        })

    def cancel_apply(self, apply_id: int) -> int:
        sql = """UPDATE asset_apply SET status = 'CANCELLED' WHERE apply_id = :apply_id"""
        return self._execute_update(sql, {"apply_id": apply_id})


class ApproveRecordDAO(BaseDAO):
    """审批记录DAO"""

    def insert_record(self, data: Dict) -> int:
        sql = """INSERT INTO approve_record (apply_id, approver_id, action, opinion, approve_node)
                 VALUES (:apply_id, :approver_id, :action, :opinion, :approve_node)"""
        return self._execute_insert(sql, data)

    def list_by_apply(self, apply_id: int) -> List[Dict]:
        sql = """SELECT r.record_id, r.apply_id, r.approver_id, u.nickname AS approver_name,
                        u.dept_id, d.dept_name,
                        r.action, r.opinion, r.approve_node, r.approve_time
                 FROM approve_record r
                 LEFT JOIN user_auth_db.sys_user u ON r.approver_id = u.user_id
                 LEFT JOIN user_auth_db.sys_dept d ON u.dept_id = d.dept_id
                 WHERE r.apply_id = :apply_id
                 ORDER BY r.approve_time ASC"""
        return self._execute(sql, {"apply_id": apply_id})