"""
用户/角色/部门/菜单/操作日志 DAO
所有SQL语句集中管理，方法只返回原始数据（dict/list）
"""
from typing import Any, Dict, List, Optional
from .base_dao import BaseDAO


class UserDAO(BaseDAO):
    """用户相关数据访问"""

    # ========== 用户表 sys_user ==========

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        sql = """SELECT user_id, username, password, nickname, dept_id, phone, email,
                        repair_specialty, avatar, status, create_time, update_time
                 FROM sys_user WHERE user_id = :user_id"""
        return self._execute_one(sql, {"user_id": user_id})

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        sql = """SELECT user_id, username, password, nickname, dept_id, phone, email,
                        repair_specialty, avatar, status, create_time, update_time
                 FROM sys_user WHERE username = :username"""
        return self._execute_one(sql, {"username": username})

    def list_users(self, keyword: str = "", dept_id: int = 0, status: int = -1,
                   page_num: int = 1, page_size: int = 10) -> tuple:
        conditions = ["1=1"]
        params = {}
        if keyword:
            conditions.append("(u.username LIKE :keyword OR u.nickname LIKE :keyword OR u.phone LIKE :keyword)")
            params["keyword"] = f"%{keyword}%"
        if dept_id:
            conditions.append("u.dept_id = :dept_id")
            params["dept_id"] = dept_id
        if status >= 0:
            conditions.append("u.status = :status")
            params["status"] = status
        where_clause = " AND ".join(conditions)

        count_sql = f"""SELECT COUNT(*) FROM sys_user u WHERE {where_clause}"""
        total = self._execute_scalar(count_sql, params)

        params["offset"] = (page_num - 1) * page_size
        params["limit"] = page_size
        list_sql = f"""SELECT u.user_id, u.username, u.nickname, u.dept_id, d.dept_name,
                              u.phone, u.email, u.repair_specialty, u.status,
                              u.create_time, u.update_time
                       FROM sys_user u
                       LEFT JOIN sys_dept d ON u.dept_id = d.dept_id
                       WHERE {where_clause}
                       ORDER BY u.create_time DESC
                       LIMIT :limit OFFSET :offset"""
        return self._execute(list_sql, params), total

    def insert_user(self, user: Dict) -> int:
        sql = """INSERT INTO sys_user (username, password, nickname, dept_id, phone, email,
                                       repair_specialty, status)
                 VALUES (:username, :password, :nickname, :dept_id, :phone, :email,
                         :repair_specialty, :status)"""
        return self._execute_insert(sql, user)

    def update_user(self, user: Dict) -> int:
        sql = """UPDATE sys_user
                 SET nickname = :nickname, dept_id = :dept_id, phone = :phone,
                     email = :email, repair_specialty = :repair_specialty, status = :status
                 WHERE user_id = :user_id"""
        return self._execute_update(sql, user)

    def update_password(self, user_id: int, password: str) -> int:
        sql = """UPDATE sys_user SET password = :password WHERE user_id = :user_id"""
        return self._execute_update(sql, {"user_id": user_id, "password": password})

    def delete_user(self, user_id: int) -> int:
        sql = """DELETE FROM sys_user WHERE user_id = :user_id"""
        return self._execute_update(sql, {"user_id": user_id})

    def delete_user_roles(self, user_id: int) -> int:
        sql = """DELETE FROM sys_user_role WHERE user_id = :user_id"""
        return self._execute_update(sql, {"user_id": user_id})

    def insert_user_role(self, user_id: int, role_id: int) -> int:
        sql = """INSERT INTO sys_user_role (user_id, role_id) VALUES (:user_id, :role_id)"""
        return self._execute_insert(sql, {"user_id": user_id, "role_id": role_id})

    def get_user_roles(self, user_id: int) -> List[Dict]:
        sql = """SELECT r.role_id, r.role_name, r.role_key
                 FROM sys_user_role ur
                 JOIN sys_role r ON ur.role_id = r.role_id
                 WHERE ur.user_id = :user_id"""
        return self._execute(sql, {"user_id": user_id})

    def list_repairers(self) -> List[Dict]:
        sql = """SELECT u.user_id, u.nickname, u.phone, u.repair_specialty
                 FROM sys_user u
                 JOIN sys_user_role ur ON u.user_id = ur.user_id
                 JOIN sys_role r ON ur.role_id = r.role_id
                 WHERE r.role_key = 'repairer' AND u.status = 1"""
        return self._execute(sql)


class RoleDAO(BaseDAO):
    """角色数据访问"""

    def list_roles(self, keyword: str = "", page_num: int = 1, page_size: int = 10) -> tuple:
        conditions = ["1=1"]
        params = {}
        if keyword:
            conditions.append("(role_name LIKE :keyword OR role_key LIKE :keyword)")
            params["keyword"] = f"%{keyword}%"
        where_clause = " AND ".join(conditions)

        count_sql = f"SELECT COUNT(*) FROM sys_role WHERE {where_clause}"
        total = self._execute_scalar(count_sql, params)

        params["offset"] = (page_num - 1) * page_size
        params["limit"] = page_size
        list_sql = f"""SELECT role_id, role_name, role_key, role_sort, status, remark, create_time
                       FROM sys_role WHERE {where_clause}
                       ORDER BY role_sort ASC
                       LIMIT :limit OFFSET :offset"""
        return self._execute(list_sql, params), total

    def get_role_by_id(self, role_id: int) -> Optional[Dict]:
        sql = """SELECT role_id, role_name, role_key, role_sort, status, remark
                 FROM sys_role WHERE role_id = :role_id"""
        return self._execute_one(sql, {"role_id": role_id})

    def get_all_roles(self) -> List[Dict]:
        sql = "SELECT role_id, role_name, role_key, role_sort, status FROM sys_role ORDER BY role_sort"
        return self._execute(sql)

    def get_role_menus(self, role_id: int) -> List[Dict]:
        sql = """SELECT rm.menu_id FROM sys_role_menu rm WHERE rm.role_id = :role_id"""
        return self._execute(sql, {"role_id": role_id})


class DeptDAO(BaseDAO):
    """部门数据访问"""

    def list_all_depts(self) -> List[Dict]:
        sql = """SELECT dept_id, dept_name, parent_id, order_num, leader, phone, status
                 FROM sys_dept ORDER BY order_num ASC"""
        return self._execute(sql)

    def get_dept_by_id(self, dept_id: int) -> Optional[Dict]:
        sql = """SELECT dept_id, dept_name, parent_id, order_num, leader, phone, status
                 FROM sys_dept WHERE dept_id = :dept_id"""
        return self._execute_one(sql, {"dept_id": dept_id})

    def get_dept_map(self, dept_ids: List[int]) -> Dict[int, str]:
        """批量获取 dept_id → dept_name 映射"""
        if not dept_ids:
            return {}
        placeholders = ",".join([f":id_{i}" for i in range(len(dept_ids))])
        params = {f"id_{i}": did for i, did in enumerate(dept_ids)}
        sql = f"""SELECT dept_id, dept_name FROM sys_dept
                  WHERE dept_id IN ({placeholders})"""
        rows = self._execute(sql, params)
        return {r["dept_id"]: r["dept_name"] for r in rows}


class MenuDAO(BaseDAO):
    """菜单数据访问"""

    def list_all_menus(self) -> List[Dict]:
        sql = """SELECT menu_id, menu_name, parent_id, order_num, path, component,
                        perms, icon, menu_type, status
                 FROM sys_menu ORDER BY order_num ASC"""
        return self._execute(sql)

    def get_menus_by_user_id(self, user_id: int) -> List[Dict]:
        sql = """SELECT DISTINCT m.menu_id, m.menu_name, m.parent_id, m.order_num, m.path,
                        m.component, m.perms, m.icon, m.menu_type, m.status
                 FROM sys_menu m
                 JOIN sys_role_menu rm ON m.menu_id = rm.menu_id
                 JOIN sys_user_role ur ON rm.role_id = ur.role_id
                 WHERE ur.user_id = :user_id AND m.status = 1
                 ORDER BY m.order_num ASC"""
        return self._execute(sql, {"user_id": user_id})


class OperLogDAO(BaseDAO):
    """操作日志数据访问"""

    def insert_log(self, log: Dict) -> int:
        sql = """INSERT INTO sys_oper_log (user_id, username, oper_type, oper_desc, oper_ip)
                 VALUES (:user_id, :username, :oper_type, :oper_desc, :oper_ip)"""
        return self._execute_insert(sql, log)

    def list_logs(self, page_num: int = 1, page_size: int = 20) -> tuple:
        count_sql = "SELECT COUNT(*) FROM sys_oper_log"
        total = self._execute_scalar(count_sql)

        params = {"offset": (page_num - 1) * page_size, "limit": page_size}
        list_sql = """SELECT log_id, user_id, username, oper_type, oper_desc, oper_ip, oper_time
                      FROM sys_oper_log ORDER BY oper_time DESC
                      LIMIT :limit OFFSET :offset"""
        return self._execute(list_sql, params), total
