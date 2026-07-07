from .base_dao import BaseDao

class DictDao(BaseDao):
    table_name = "sys_dict"

    def list_by_type(self, dict_type: str):
        return self.list_by_condition({"dict_type": dict_type}, order_by="sort ASC")

    def list_types(self):
        """获取所有字典分类"""
        sql = "SELECT DISTINCT dict_type FROM sys_dict WHERE is_delete = 0 ORDER BY dict_type"
        conn = self._get_conn()
        rows = conn.execute(sql).fetchall()
        conn.close()
        return [r["dict_type"] for r in rows]

    def get_by_code(self, dict_type: str, dict_code: str):
        sql = "SELECT * FROM sys_dict WHERE dict_type = ? AND dict_code = ? AND is_delete = 0"
        conn = self._get_conn()
        row = conn.execute(sql, (dict_type, dict_code)).fetchone()
        conn.close()
        return dict(row) if row else None