"""
文件元数据 DAO
所有SQL语句集中管理
"""
from typing import Any, Dict, List, Optional
from .base_dao import BaseDAO


class FileDAO(BaseDAO):
    """文件元数据访问"""

    def insert_file(self, file_info: Dict) -> int:
        sql = """INSERT INTO file_info (file_name, file_path, file_size, file_type,
                                        biz_type, biz_id, uploader_id)
                 VALUES (:file_name, :file_path, :file_size, :file_type,
                         :biz_type, :biz_id, :uploader_id)"""
        return self._execute_insert(sql, file_info)

    def get_file_by_id(self, file_id: int) -> Optional[Dict]:
        sql = """SELECT f.file_id, f.file_name, f.file_path, f.file_size, f.file_type,
                        f.biz_type, f.biz_id, f.uploader_id, u.nickname AS uploader_name,
                        f.create_time
                 FROM file_info f
                 LEFT JOIN sys_user u ON f.uploader_id = u.user_id
                 WHERE f.file_id = :file_id"""
        return self._execute_one(sql, {"file_id": file_id})

    def list_files(self, biz_type: str = "", biz_id: int = 0, uploader_id: int = 0,
                   page_num: int = 1, page_size: int = 20) -> tuple:
        conditions = ["1=1"]
        params = {}
        if biz_type:
            conditions.append("f.biz_type = :biz_type")
            params["biz_type"] = biz_type
        if biz_id:
            conditions.append("f.biz_id = :biz_id")
            params["biz_id"] = biz_id
        if uploader_id:
            conditions.append("f.uploader_id = :uploader_id")
            params["uploader_id"] = uploader_id
        where_clause = " AND ".join(conditions)

        count_sql = f"SELECT COUNT(*) FROM file_info f WHERE {where_clause}"
        total = self._execute_scalar(count_sql, params)

        params["offset"] = (page_num - 1) * page_size
        params["limit"] = page_size
        list_sql = f"""SELECT f.file_id, f.file_name, f.file_path, f.file_size, f.file_type,
                              f.biz_type, f.biz_id, f.uploader_id, u.nickname AS uploader_name,
                              f.create_time
                       FROM file_info f
                       LEFT JOIN sys_user u ON f.uploader_id = u.user_id
                       WHERE {where_clause}
                       ORDER BY f.create_time DESC
                       LIMIT :limit OFFSET :offset"""
        return self._execute(list_sql, params), total

    def delete_file(self, file_id: int) -> int:
        sql = """DELETE FROM file_info WHERE file_id = :file_id"""
        return self._execute_update(sql, {"file_id": file_id})
