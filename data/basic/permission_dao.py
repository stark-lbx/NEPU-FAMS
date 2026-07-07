from .base_dao import BaseDao

class PermissionDao(BaseDao):
    table_name = "sys_permission"

    def list_by_parent(self, parent_biz_id: str):
        return self.list_by_condition({"parent_biz_id": parent_biz_id}, order_by="sort ASC")


class RolePermissionDao(BaseDao):
    table_name = "sys_role_permission"

    def list_by_role(self, role_biz_id: str):
        sql = """SELECT p.* FROM sys_role_permission rp
                 LEFT JOIN sys_permission p ON rp.perm_biz_id = p.biz_id
                 WHERE rp.role_biz_id = ? AND p.is_delete = 0"""
        conn = self._get_conn()
        rows = conn.execute(sql, (role_biz_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]