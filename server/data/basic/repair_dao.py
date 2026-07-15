"""
维修工单/工单操作日志 DAO
所有SQL语句集中管理
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo  # Python3.9+内置时区，无需pytz
from .base_dao import BaseDAO


def format_mysql_datetime(raw_val: Any) -> Optional[str]:
    """
    统一格式化时间为MySQL DATETIME标准格式 YYYY-MM-DD HH:MM:SS
    兼容：空值 / datetime对象 / ISO字符串(2026-07-10T16:00:00.000Z)
    UTC时间自动转为北京时间(+8时区)
    """
    if not raw_val:
        return None

    # 1. 如果已经是datetime对象直接处理
    if isinstance(raw_val, datetime):
        if raw_val.tzinfo is None:
            # 无时区，直接输出
            return raw_val.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # 带时区，转北京时间
            bj_dt = raw_val.astimezone(ZoneInfo("Asia/Shanghai"))
            return bj_dt.strftime("%Y-%m-%d %H:%M:%S")

    # 2. 处理前端传来的ISO字符串（带Z UTC）
    val_str = str(raw_val).strip()
    if "T" in val_str:
        # 替换Z为+00:00，解析UTC时间
        iso_fixed = val_str.replace("Z", "+00:00")
        utc_dt = datetime.fromisoformat(iso_fixed)
        # UTC转北京时间
        bj_dt = utc_dt.astimezone(ZoneInfo("Asia/Shanghai"))
        return bj_dt.strftime("%Y-%m-%d %H:%M:%S")

    # 3. 已经是标准mysql时间字符串，直接返回
    return val_str


class RepairOrderDAO(BaseDAO):
    """维修工单数据访问"""

    def insert_order(self, order: Dict) -> int:
        sql = """INSERT INTO repair_order (asset_id, reporter_id, fault_desc, fault_images,
                                           status, dept_id)
                 VALUES (:asset_id, :reporter_id, :fault_desc, :fault_images,
                         :status, :dept_id)"""
        return self._execute_insert(sql, order)

    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        sql = """SELECT r.order_id, r.asset_id, a.asset_name, a.asset_code, a.spec AS asset_spec,
                        a.location AS asset_location,
                        r.reporter_id, u1.nickname AS reporter_name, r.dept_id, d.dept_name,
                        r.fault_desc, r.fault_images, r.status,
                        r.college_approver_id, u2.nickname AS college_approver_name,
                        r.college_opinion,
                        r.school_approver_id, u6.nickname AS school_approver_name,
                        r.school_opinion,
                        r.dispatch_user_id, u3.nickname AS dispatch_user_name,
                        r.dispatch_time, r.dispatch_remark,
                        r.repairer_id, u4.nickname AS repairer_name,
                        r.deadline, r.repair_start_time, r.repair_end_time,
                        r.repair_detail, r.repair_cost, r.parts_detail, r.invoice_files,
                        r.acceptor_id, u5.nickname AS acceptor_name, r.accept_opinion,
                        r.create_time, r.update_time
                 FROM repair_order r
                 LEFT JOIN asset_core_db.asset_info a ON r.asset_id = a.asset_id
                 LEFT JOIN user_auth_db.sys_user u1 ON r.reporter_id = u1.user_id
                 LEFT JOIN user_auth_db.sys_dept d ON r.dept_id = d.dept_id
                 LEFT JOIN user_auth_db.sys_user u2 ON r.college_approver_id = u2.user_id
                 LEFT JOIN user_auth_db.sys_user u3 ON r.dispatch_user_id = u3.user_id
                 LEFT JOIN user_auth_db.sys_user u4 ON r.repairer_id = u4.user_id
                 LEFT JOIN user_auth_db.sys_user u5 ON r.acceptor_id = u5.user_id
                 LEFT JOIN user_auth_db.sys_user u6 ON r.school_approver_id = u6.user_id
                 WHERE r.order_id = :order_id"""
        return self._execute_one(sql, {"order_id": order_id})

    def list_orders(self, status: str = "", dept_id: int = 0, repairer_id: int = 0,
                    reporter_id: int = 0, keyword: str = "",
                    page_num: int = 1, page_size: int = 10) -> tuple:
        conditions = ["1=1"]
        params = {}
        if status:
            # 支持逗号分隔的多个状态，例如 "PENDING_SCHOOL_APPROVE,PENDING_DISPATCH"
            if "," in status:
                status_list = [s.strip() for s in status.split(",") if s.strip()]
                placeholders = ", ".join([f":status_{i}" for i in range(len(status_list))])
                conditions.append(f"r.status IN ({placeholders})")
                for i, s in enumerate(status_list):
                    params[f"status_{i}"] = s
            else:
                conditions.append("r.status = :status")
                params["status"] = status
        if dept_id:
            conditions.append("r.dept_id = :dept_id")
            params["dept_id"] = dept_id
        if repairer_id:
            conditions.append("r.repairer_id = :repairer_id")
            params["repairer_id"] = repairer_id
        if reporter_id:
            conditions.append("r.reporter_id = :reporter_id")
            params["reporter_id"] = reporter_id
        if keyword:
            conditions.append("(a.asset_name LIKE :keyword OR r.order_id LIKE :keyword)")
            params["keyword"] = f"%{keyword}%"
        where_clause = " AND ".join(conditions)

        count_sql = f"SELECT COUNT(*) FROM repair_order r LEFT JOIN asset_core_db.asset_info a ON r.asset_id = a.asset_id WHERE {where_clause}"
        total = self._execute_scalar(count_sql, params)

        params["offset"] = (page_num - 1) * page_size
        params["limit"] = page_size
        list_sql = f"""SELECT r.order_id, r.asset_id, a.asset_name, a.asset_code, a.spec AS asset_spec,
                              r.reporter_id, u1.nickname AS reporter_name, r.dept_id, d.dept_name,
                              r.fault_desc, r.status, r.repairer_id, u4.nickname AS repairer_name,
                              r.college_opinion, r.school_opinion,
                              r.dispatch_time, r.deadline, r.repair_end_time,
                              r.repair_cost, r.create_time, r.update_time
                       FROM repair_order r
                       LEFT JOIN asset_core_db.asset_info a ON r.asset_id = a.asset_id
                       LEFT JOIN user_auth_db.sys_user u1 ON r.reporter_id = u1.user_id
                       LEFT JOIN user_auth_db.sys_dept d ON r.dept_id = d.dept_id
                       LEFT JOIN user_auth_db.sys_user u4 ON r.repairer_id = u4.user_id
                       WHERE {where_clause}
                       ORDER BY r.create_time DESC
                       LIMIT :limit OFFSET :offset"""
        return self._execute(list_sql, params), total

    def college_approve(self, order_id: int, approver_id: int, opinion: str, status: str) -> int:
        """学院初审：写初审人/意见/状态"""
        sql = """UPDATE repair_order
                 SET college_approver_id = :approver_id,
                     college_opinion = :opinion,
                     status = :status
                 WHERE order_id = :order_id"""
        return self._execute_update(sql, {
            "order_id": order_id, "approver_id": approver_id,
            "opinion": opinion, "status": status
        })

    def school_approve(self, order_id: int, approver_id: int, opinion: str, status: str) -> int:
        """校级复审：写复审人/意见/状态
        关键修复：校级驳回时 status 应该是 ACCEPTANCE_REJECTED 而非 COLLEGE_REJECTED
        """
        sql = """UPDATE repair_order
                 SET school_approver_id = :approver_id,
                     school_opinion = :opinion,
                     status = :status
                 WHERE order_id = :order_id"""
        return self._execute_update(sql, {
            "order_id": order_id, "approver_id": approver_id,
            "opinion": opinion, "status": status
        })

    def update_order_status(self, order_id: int, status: str, extra_set: str = "") -> int:
        """通用状态更新：可附带额外 SET 子句（如 repair_start_time = NOW()）
        用于接单/完成/重新提交等不写特定审批人字段的状态推进
        """
        set_clause = "status = :status"
        if extra_set:
            set_clause += ", " + extra_set
        sql = f"""UPDATE repair_order SET {set_clause}
                  WHERE order_id = :order_id"""
        return self._execute_update(sql, {
            "order_id": order_id, "status": status
        })

    def dispatch_order(self, order_id: int, dispatch_user_id: int,
                       repairer_id: int, deadline: Any, remark: str) -> int:
        sql = """UPDATE repair_order
                 SET dispatch_user_id = :dispatch_user_id, repairer_id = :repairer_id,
                     deadline = :deadline, dispatch_remark = :remark, status = 'PENDING_REPAIR'
                 WHERE order_id = :order_id"""
        # 关键修复：统一格式化deadline时间
        fmt_deadline = format_mysql_datetime(deadline)
        params = {
            "order_id": order_id,
            "dispatch_user_id": dispatch_user_id,
            "repairer_id": repairer_id,
            "deadline": fmt_deadline,
            "remark": remark
        }
        return self._execute_update(sql, params)

    def accept_order(self, order_id: int, repairer_id: int) -> int:
        """维修工接单：状态从 PENDING_REPAIR → REPAIR_ACCEPTED
        注：Logic 层已改用 update_order_status + 状态机校验，不推荐直接调用本方法
        """
        sql = """UPDATE repair_order
                 SET status = 'REPAIR_ACCEPTED', repair_start_time = NOW()
                 WHERE order_id = :order_id AND repairer_id = :repairer_id"""
        return self._execute_update(sql, {
            "order_id": order_id, "repairer_id": repairer_id
        })

    def update_repair_info(self, order_id: int, repairer_id: int,
                           detail: str, cost: float, parts: str, invoices: str) -> int:
        sql = """UPDATE repair_order
                 SET repair_detail = :detail, repair_cost = :cost,
                     parts_detail = :parts, invoice_files = :invoices
                 WHERE order_id = :order_id AND repairer_id = :repairer_id"""
        return self._execute_update(sql, {
            "order_id": order_id, "repairer_id": repairer_id,
            "detail": detail, "cost": cost, "parts": parts, "invoices": invoices
        })

    def finish_repair(self, order_id: int, repairer_id: int) -> int:
        sql = """UPDATE repair_order
                 SET status = 'PENDING_ACCEPTANCE', repair_end_time = NOW()
                 WHERE order_id = :order_id AND repairer_id = :repairer_id"""
        return self._execute_update(sql, {
            "order_id": order_id, "repairer_id": repairer_id
        })

    def acceptance(self, order_id: int, acceptor_id: int,
                   is_pass: bool, opinion: str, new_status: str = None) -> int:
        """验收：状态由 logic 层显式传入，避免 logic 与 DAO 中状态值不同步
        :param new_status: logic 层算出的目标状态（默认按 is_pass 推断，保持向后兼容）
        """
        if new_status is None:
            new_status = "ACCEPTANCE_PASSED" if is_pass else "ACCEPTANCE_REJECTED"
        sql = """UPDATE repair_order
                 SET acceptor_id = :acceptor_id, accept_opinion = :opinion,
                     status = :status
                 WHERE order_id = :order_id"""
        return self._execute_update(sql, {
            "order_id": order_id, "acceptor_id": acceptor_id,
            "opinion": opinion, "status": new_status
        })

    def get_statistics(self, repairer_id: int) -> Dict:
        sql = """SELECT
                   SUM(CASE WHEN status = 'PENDING_REPAIR' THEN 1 ELSE 0 END) AS pending_count,
                   SUM(CASE WHEN status = 'REPAIR_ACCEPTED' THEN 1 ELSE 0 END) AS repairing_count,
                   SUM(CASE WHEN status = 'PENDING_ACCEPTANCE' THEN 1 ELSE 0 END) AS acceptance_count,
                   SUM(CASE WHEN status = 'ACCEPTANCE_PASSED'
                            AND MONTH(repair_end_time) = MONTH(NOW())
                            AND YEAR(repair_end_time) = YEAR(NOW())
                            THEN 1 ELSE 0 END) AS month_completed_count
                 FROM repair_order
                 WHERE repairer_id = :repairer_id"""
        return self._execute_one(sql, {"repairer_id": repairer_id})

    def list_by_asset(self, asset_id: int, page_num: int = 1, page_size: int = 10) -> tuple:
        params = {"asset_id": asset_id}
        count_sql = "SELECT COUNT(*) FROM repair_order WHERE asset_id = :asset_id"
        total = self._execute_scalar(count_sql, params)

        params["offset"] = (page_num - 1) * page_size
        params["limit"] = page_size
        list_sql = """SELECT r.order_id, r.asset_id, a.asset_name,
                              r.repair_detail, r.repair_cost,
                              r.repair_end_time, r.status
                       FROM repair_order r
                       LEFT JOIN asset_core_db.asset_info a ON r.asset_id = a.asset_id
                       WHERE r.asset_id = :asset_id AND r.status = 'ACCEPTANCE_PASSED'
                       ORDER BY r.repair_end_time DESC
                       LIMIT :limit OFFSET :offset"""
        return self._execute(list_sql, params), total


class RepairOperLogDAO(BaseDAO):
    """工单操作日志数据访问"""

    def insert_log(self, log: Dict) -> int:
        sql = """INSERT INTO repair_operation_log (order_id, operator_id, oper_type, oper_desc, oper_ip)
                 VALUES (:order_id, :operator_id, :oper_type, :oper_desc, :oper_ip)"""
        return self._execute_insert(sql, log)

    def list_by_order(self, order_id: int) -> List[Dict]:
        sql = """SELECT l.log_id, l.order_id, l.operator_id, u.nickname AS operator_name,
                        u.dept_id, d.dept_name,
                        l.oper_type, l.oper_desc, l.oper_ip, l.oper_time,
                        l.oper_time AS create_time
                 FROM repair_operation_log l
                 LEFT JOIN user_auth_db.sys_user u ON l.operator_id = u.user_id
                 LEFT JOIN user_auth_db.sys_dept d ON u.dept_id = d.dept_id
                 WHERE l.order_id = :order_id
                 ORDER BY l.oper_time ASC"""
        return self._execute(sql, {"order_id": order_id})