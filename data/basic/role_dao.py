from .base_dao import BaseDao

class RoleDao(BaseDao):
    table_name = "sys_role"

    def select_by_code(self, role_code: str):
        sql = "SELECT * FROM sys_role WHERE role_code = ? AND is_delete = 0"
        conn = self._get_conn()
        row = conn.execute(sql, (role_code,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def list_all(self):
        return self.list_by_condition({})


class UserRoleDao(BaseDao):
    table_name = "sys_user_role"

    def bind_user_role(self, user_biz_id: str, role_biz_id: str):
        return self.insert({"user_biz_id": user_biz_id, "role_biz_id": role_biz_id})

    def list_by_user(self, user_biz_id: str):
        sql = """SELECT r.* FROM sys_user_role ur
                 LEFT JOIN sys_role r ON ur.role_biz_id = r.biz_id
                 WHERE ur.user_biz_id = ? AND r.is_delete = 0"""
        conn = self._get_conn()
        rows = conn.execute(sql, (user_biz_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]