from .base_dao import BaseDao, _strip_internal

class UserDao(BaseDao):
    table_name = "sys_user"
    pk_field = "id"

    def select_by_username(self, username: str):
        sql = "SELECT * FROM sys_user WHERE username = ? AND is_delete = 0"
        conn = self._get_conn()
        row = conn.execute(sql, (username,)).fetchone()
        conn.close()
        return _strip_internal(dict(row)) if row else None

    def select_by_biz_id(self, biz_id: str):
        sql = "SELECT * FROM sys_user WHERE biz_id = ? AND is_delete = 0"
        conn = self._get_conn()
        row = conn.execute(sql, (biz_id,)).fetchone()
        conn.close()
        return _strip_internal(dict(row)) if row else None

    def list_by_dept(self, dept_biz_id: str):
        sql = "SELECT * FROM sys_user WHERE dept_biz_id = ? AND is_delete = 0"
        conn = self._get_conn()
        rows = conn.execute(sql, (dept_biz_id,)).fetchall()
        conn.close()
        return [_strip_internal(dict(r)) for r in rows]

    def update_by_biz_id(self, biz_id: str, data: dict) -> bool:
        """按 biz_id 更新用户字段"""
        if not data:
            return False
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [biz_id]
        sql = f"UPDATE sys_user SET {set_clause} WHERE biz_id = ? AND is_delete = 0"
        conn = self._get_conn()
        conn.execute(sql, values)
        conn.commit()
        conn.close()
        return True