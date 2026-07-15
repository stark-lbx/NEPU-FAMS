"""
资产/分类/变更日志 DAO
所有SQL语句集中管理
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from .base_dao import BaseDAO


class AssetDAO(BaseDAO):
    """资产数据访问"""

    # ========== 资产主表 asset_info ==========

    def list_assets(self, keyword: str = "", category_id: int = 0, status: int = 0,
                    dept_id: int = 0, page_num: int = 1, page_size: int = 10) -> tuple:
        conditions = ["1=1"]
        params = {}
        if keyword:
            conditions.append("(a.asset_name LIKE :keyword OR a.asset_code LIKE :keyword OR a.location LIKE :keyword)")
            params["keyword"] = f"%{keyword}%"
        if category_id:
            conditions.append("a.category_id = :category_id")
            params["category_id"] = category_id
        if status:
            # status 现在是asset_status主键id（数字）
            conditions.append("a.status = :status")
            params["status"] = status
        if dept_id:
            conditions.append("a.dept_id = :dept_id")
            params["dept_id"] = dept_id
        where_clause = " AND ".join(conditions)

        count_sql = f"SELECT COUNT(*) FROM asset_info a WHERE {where_clause}"
        total = self._execute_scalar(count_sql, params)

        params["offset"] = (page_num - 1) * page_size
        params["limit"] = page_size
        list_sql = f"""SELECT a.asset_id, a.asset_code, a.asset_name, a.spec,
                              a.category_id, c.category_name, a.purchase_date,
                              a.book_value, a.location, a.dept_id, d.dept_name,
                              a.user_id, u.nickname AS user_name,
                              a.status AS status_id, s.status_code, s.status_name,
                              a.remark, a.version, a.create_time, a.update_time
                       FROM asset_info a
                       LEFT JOIN asset_category c ON a.category_id = c.category_id
                       LEFT JOIN user_auth_db.sys_dept d ON a.dept_id = d.dept_id
                       LEFT JOIN user_auth_db.sys_user u ON a.user_id = u.user_id
                       LEFT JOIN asset_status s ON a.status = s.id
                       WHERE {where_clause}
                       ORDER BY a.create_time DESC
                       LIMIT :limit OFFSET :offset"""
        return self._execute(list_sql, params), total

    def get_asset_by_id(self, asset_id: int) -> Optional[Dict]:
        sql = """SELECT a.asset_id, a.asset_code, a.asset_name, a.spec,
                        a.category_id, c.category_name, a.purchase_date,
                        a.book_value, a.location, a.dept_id, d.dept_name,
                        a.user_id, u.nickname AS user_name,
                        a.status AS status, s.status_code, s.status_name,
                        a.remark, a.version, a.create_time, a.update_time
                 FROM asset_info a
                 LEFT JOIN asset_category c ON a.category_id = c.category_id
                 LEFT JOIN user_auth_db.sys_dept d ON a.dept_id = d.dept_id
                 LEFT JOIN user_auth_db.sys_user u ON a.user_id = u.user_id
                 LEFT JOIN asset_status s ON a.status = s.id
                 WHERE a.asset_id = :asset_id"""
        return self._execute_one(sql, {"asset_id": asset_id})

    def generate_asset_code(self) -> str:
        """生成唯一资产编号 ZC-YYYYMMDD-NNNNN"""
        date_str = datetime.now().strftime("%Y%m%d")
        sql = """SELECT MAX(asset_code) FROM asset_info
                 WHERE asset_code LIKE :prefix"""
        max_code = self._execute_scalar(sql, {"prefix": f"ZC-{date_str}-%"})
        if max_code:
            seq = int(max_code.split("-")[-1]) + 1
        else:
            seq = 1
        return f"ZC-{date_str}-{seq:05d}"

    def insert_asset(self, asset: Dict) -> int:
        # asset字典中status传入asset_status表数字id
        sql = """INSERT INTO asset_info (asset_code, asset_name, spec, category_id,
                                         purchase_date, book_value, location, dept_id,
                                         user_id, status, remark, version)
                 VALUES (:asset_code, :asset_name, :spec, :category_id, :purchase_date,
                         :book_value, :location, :dept_id, :user_id, :status, :remark, 1)"""
        return self._execute_insert(sql, asset)

    def update_asset(self, asset: Dict) -> int:
        # status传入asset_status数字id
        sql = """UPDATE asset_info
                 SET asset_name = :asset_name, spec = :spec, category_id = :category_id,
                     purchase_date = :purchase_date, book_value = :book_value,
                     location = :location, dept_id = :dept_id, user_id = :user_id,
                     status = :status, remark = :remark, version = version + 1
                 WHERE asset_id = :asset_id AND version = :version"""
        return self._execute_update(sql, asset)

    def update_asset_status(self, asset_id: int, status_id: int,
                             user_id: int = 0, version: int = 0) -> int:
        """
        更新资产状态
        :param asset_id: 资产ID
        :param status_id: asset_status表主键数字id（替换原字符串status）
        :param user_id: 操作人
        :param version: 乐观锁版本
        """
        sql = """UPDATE asset_info SET status = :status_id, user_id = :user_id, version = version + 1
                 WHERE asset_id = :asset_id AND version = :version"""
        return self._execute_update(sql, {
            "asset_id": asset_id, "status_id": status_id,
            "user_id": user_id, "version": version
        })

    def delete_asset(self, asset_id: int) -> int:
        sql = """DELETE FROM asset_info WHERE asset_id = :asset_id"""
        return self._execute_update(sql, {"asset_id": asset_id})

    def get_export_list(self, keyword: str = "", category_id: int = 0,
                        status: int = 0, dept_id: int = 0) -> List[Dict]:
        conditions = ["1=1"]
        params = {}
        if keyword:
            conditions.append("(a.asset_name LIKE :keyword OR a.asset_code LIKE :keyword)")
            params["keyword"] = f"%{keyword}%"
        if category_id:
            conditions.append("a.category_id = :category_id")
            params["category_id"] = category_id
        if status:
            # status为数字id筛选
            conditions.append("a.status = :status")
            params["status"] = status
        if dept_id:
            conditions.append("a.dept_id = :dept_id")
            params["dept_id"] = dept_id
        where_clause = " AND ".join(conditions)
        sql = f"""SELECT a.asset_code, a.asset_name, a.spec, c.category_name,
                         a.purchase_date, a.book_value, a.location, d.dept_name,
                         u.nickname AS user_name,
                         a.status AS status_id, s.status_code, s.status_name,
                         a.remark
                  FROM asset_info a
                  LEFT JOIN asset_category c ON a.category_id = c.category_id
                  LEFT JOIN user_auth_db.sys_dept d ON a.dept_id = d.dept_id
                  LEFT JOIN user_auth_db.sys_user u ON a.user_id = u.user_id
                  LEFT JOIN asset_status s ON a.status = s.id
                  WHERE {where_clause}
                  ORDER BY a.create_time DESC"""
        return self._execute(sql, params)

    # 新增：获取全部资产状态下拉列表（前端下拉框专用）
    def list_all_asset_status(self) -> List[Dict]:
        """查询所有资产状态字典表数据"""
        sql = """SELECT id AS status_id, status_code, status_name
                 FROM asset_status ORDER BY id ASC"""
        return self._execute(sql)


class CategoryDAO(BaseDAO):
    """资产分类数据访问"""

    def list_categories(self) -> List[Dict]:
        sql = """SELECT category_id, category_name, parent_id, sort, status
                 FROM asset_category ORDER BY sort ASC"""
        return self._execute(sql)

    def get_by_id(self, category_id: int) -> Optional[Dict]:
        sql = """SELECT category_id, category_name, parent_id, sort, status
                 FROM asset_category WHERE category_id = :category_id"""
        return self._execute_one(sql, {"category_id": category_id})


class AssetOperLogDAO(BaseDAO):
    """资产变更日志数据访问"""

    def insert_log(self, log: Dict) -> int:
        sql = """INSERT INTO asset_operation_log (asset_id, operator_id, oper_type,
                                                  field_name, old_value, new_value, oper_ip)
                 VALUES (:asset_id, :operator_id, :oper_type, :field_name,
                         :old_value, :new_value, :oper_ip)"""
        return self._execute_insert(sql, log)

    def list_logs_by_asset(self, asset_id: int) -> List[Dict]:
        sql = """SELECT l.log_id, l.asset_id, a.asset_name, l.operator_id,
                        u.nickname AS operator_name, l.oper_type, l.field_name,
                        l.old_value, l.new_value, l.oper_ip, l.oper_time
                 FROM asset_operation_log l
                 LEFT JOIN user_auth_db.sys_user u ON l.operator_id = u.user_id
                 LEFT JOIN asset_info a ON l.asset_id = a.asset_id
                 WHERE l.asset_id = :asset_id
                 ORDER BY l.oper_time DESC"""
        return self._execute(sql, {"asset_id": asset_id})