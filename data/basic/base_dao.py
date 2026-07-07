import sqlite3
from abc import ABC
from typing import List, Dict, Any, Optional
from common.utils import now_str

# 数据库内部字段，永远不应出现在 proto message 中
_INTERNAL_COLUMNS = {"id", "is_delete"}


def _strip_internal(row: Dict[str, Any]) -> Dict[str, Any]:
    """剔除数据库内部字段，避免 proto 构建时报错"""
    return {k: v for k, v in row.items() if k not in _INTERNAL_COLUMNS}


class BaseDao(ABC):
    table_name: str = ""
    pk_field: str = "id"

    def __init__(self, db_path: str = "fams.db"):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def insert(self, data: Dict[str, Any]) -> int:
        fields = ",".join(data.keys())
        placeholders = ",".join(["?"] * len(data))
        sql = f"INSERT INTO {self.table_name} ({fields}) VALUES ({placeholders})"
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(sql, list(data.values()))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def select_by_biz_id(self, biz_id: str) -> Optional[Dict[str, Any]]:
        sql = f"SELECT * FROM {self.table_name} WHERE biz_id = ? AND is_delete = 0"
        conn = self._get_conn()
        row = conn.execute(sql, (biz_id,)).fetchone()
        conn.close()
        return _strip_internal(dict(row)) if row else None

    def update_by_biz_id(self, biz_id: str, data: Dict[str, Any]) -> bool:
        data['update_time'] = now_str()
        set_clause = ",".join([f"{k}=?" for k in data.keys()])
        sql = f"UPDATE {self.table_name} SET {set_clause} WHERE biz_id = ?"
        conn = self._get_conn()
        cursor = conn.execute(sql, list(data.values()) + [biz_id])
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def delete_by_biz_id(self, biz_id: str) -> bool:
        """软删除"""
        return self.update_by_biz_id(biz_id, {"is_delete": 1})

    def list_by_condition(self, condition: Dict[str, Any],
                          order_by: str = "create_time DESC",
                          limit: int = 0, offset: int = 0) -> List[Dict[str, Any]]:
        conditions = []
        params = list(condition.values())
        for k in condition.keys():
            conditions.append(f"{k}=?")
        if "is_delete" not in condition:
            conditions.append("is_delete = 0")
        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM {self.table_name} WHERE {where_clause} ORDER BY {order_by}"
        if limit > 0:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        conn = self._get_conn()
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [_strip_internal(dict(r)) for r in rows]

    def count_by_condition(self, condition: Dict[str, Any]) -> int:
        conditions = []
        params = list(condition.values())
        for k in condition.keys():
            conditions.append(f"{k}=?")
        if "is_delete" not in condition:
            conditions.append("is_delete = 0")
        where_clause = " AND ".join(conditions)
        sql = f"SELECT COUNT(*) as cnt FROM {self.table_name} WHERE {where_clause}"
        conn = self._get_conn()
        row = conn.execute(sql, params).fetchone()
        conn.close()
        return row['cnt']