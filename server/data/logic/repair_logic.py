"""
工单全生命周期、状态流转、派单验收 业务逻辑
不得出现任何SQL语句

设计要点：
  1) 工单状态用 asset_status.status_code 字符串表示（与字典严格对应）
  2) 状态推进时联动更新 asset_info.status（过程态→5 FLOWING；维修态→3 REPAIRING；终态按业务联动）
  3) 状态机转移全部走 ALLOWED_TRANSITIONS 字典，禁止硬编码
"""
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from data.basic.repair_dao import RepairOrderDAO, RepairOperLogDAO


# ============================================================
# 状态码常量（与 asset_status.status_code 严格对应）
# 工单过程态全部对应 asset_status 中 biz_flow='repair' 的记录
# ============================================================
class RepairOrderStatus(str, Enum):
    PENDING_COLLEGE_APPROVE = "PENDING_COLLEGE_APPROVE"   # 待院级初审
    PENDING_SCHOOL_APPROVE = "PENDING_SCHOOL_APPROVE"     # 待校级复审
    PENDING_DISPATCH = "PENDING_DISPATCH"                 # 待派单
    PENDING_REPAIR = "PENDING_REPAIR"                     # 已派单待接
    REPAIR_ACCEPTED = "REPAIR_ACCEPTED"                   # 维修工接单，维修中
    PENDING_ACCEPTANCE = "PENDING_ACCEPTANCE"             # 待验收
    ACCEPTANCE_PASSED = "ACCEPTANCE_PASSED"               # 验收通过
    ACCEPTANCE_REJECTED = "ACCEPTANCE_REJECTED"           # 验收驳回


# 状态 ↔ asset_info 物理态 联动映射
ASSET_STATUS_MAP = {
    RepairOrderStatus.PENDING_COLLEGE_APPROVE: 5,  # FLOWING
    RepairOrderStatus.PENDING_SCHOOL_APPROVE: 5,   # FLOWING
    RepairOrderStatus.PENDING_DISPATCH: 5,         # FLOWING
    RepairOrderStatus.PENDING_REPAIR: 3,           # REPAIRING
    RepairOrderStatus.REPAIR_ACCEPTED: 3,          # REPAIRING
    RepairOrderStatus.PENDING_ACCEPTANCE: 3,       # REPAIRING
    RepairOrderStatus.ACCEPTANCE_PASSED: 1,        # IDLE 终态
    RepairOrderStatus.ACCEPTANCE_REJECTED: 3,      # REPAIRING 返工
}

# 状态机转移规则：(action, current_status) -> new_status
# 关键修复：校级驳回走 ACCEPTANCE_REJECTED 终态而非 COLLEGE_REJECTED（之前的严重 bug）
ALLOWED_TRANSITIONS = {
    ("COLLEGE_APPROVE_PASS",   RepairOrderStatus.PENDING_COLLEGE_APPROVE): RepairOrderStatus.PENDING_SCHOOL_APPROVE,
    ("COLLEGE_APPROVE_REJECT", RepairOrderStatus.PENDING_COLLEGE_APPROVE): RepairOrderStatus.ACCEPTANCE_REJECTED,
    ("SCHOOL_APPROVE_PASS",    RepairOrderStatus.PENDING_SCHOOL_APPROVE):  RepairOrderStatus.PENDING_DISPATCH,
    ("SCHOOL_APPROVE_REJECT",  RepairOrderStatus.PENDING_SCHOOL_APPROVE):  RepairOrderStatus.ACCEPTANCE_REJECTED,
    ("DISPATCH",               RepairOrderStatus.PENDING_DISPATCH):        RepairOrderStatus.PENDING_REPAIR,
    ("ACCEPT",                 RepairOrderStatus.PENDING_REPAIR):          RepairOrderStatus.REPAIR_ACCEPTED,
    ("FINISH",                 RepairOrderStatus.REPAIR_ACCEPTED):         RepairOrderStatus.PENDING_ACCEPTANCE,
    ("ACCEPTANCE_PASS",        RepairOrderStatus.PENDING_ACCEPTANCE):      RepairOrderStatus.ACCEPTANCE_PASSED,
    ("ACCEPTANCE_REJECT",      RepairOrderStatus.PENDING_ACCEPTANCE):      RepairOrderStatus.ACCEPTANCE_REJECTED,
    ("RESUBMIT",               RepairOrderStatus.ACCEPTANCE_REJECTED):     RepairOrderStatus.PENDING_ACCEPTANCE,
}


class RepairLogic:
    """维修工单业务逻辑"""

    def __init__(self, db_config: Dict, asset_db_config: Optional[Dict] = None):
        self.order_dao = RepairOrderDAO(db_config)
        self.oper_log_dao = RepairOperLogDAO(db_config)
        self._asset_db_config = asset_db_config
        self._asset_dao = None

    def _get_asset_dao(self):
        if self._asset_dao is None and self._asset_db_config is not None:
            from data.basic.asset_dao import AssetDAO
            self._asset_dao = AssetDAO(self._asset_db_config)
        return self._asset_dao

    def _sync_asset_status(self, asset_id: int, new_status: str) -> None:
        """根据工单状态联动更新 asset_info.status"""
        asset_dao = self._get_asset_dao()
        if asset_dao is None or not asset_id:
            return
        try:
            st = RepairOrderStatus(new_status)
        except ValueError:
            return
        target = ASSET_STATUS_MAP.get(st)
        if target is None:
            return

        asset = asset_dao.get_asset_by_id(asset_id)
        if not asset:
            return
        if asset["status"] != target:
            asset_dao.update_asset_status(
                asset_id=asset_id,
                status_id=target,
                user_id=0,
                version=asset["version"]
            )

    def _ensure_transition(self, current_status: str, action: str) -> Optional[RepairOrderStatus]:
        """校验状态机转移合法性，返回新状态或 None"""
        try:
            cur = RepairOrderStatus(current_status)
        except ValueError:
            return None
        new_status = ALLOWED_TRANSITIONS.get((action, cur))
        return new_status

    def submit_order(self, data: Dict) -> Optional[Dict]:
        """提交报修工单"""
        data["status"] = RepairOrderStatus.PENDING_COLLEGE_APPROVE.value
        if "fault_images" in data and isinstance(data["fault_images"], list):
            data["fault_images"] = ",".join(data["fault_images"])
        else:
            data["fault_images"] = ""
        order_id = self.order_dao.insert_order(data)
        self._add_log(order_id, data.get("reporter_id", 0), "SUBMIT", "提交报修工单")

        # 联动资产进入流程中
        asset_id = data.get("asset_id", 0)
        if asset_id:
            self._sync_asset_status(asset_id, RepairOrderStatus.PENDING_COLLEGE_APPROVE.value)

        return self.get_order_detail(order_id)

    def get_order_detail(self, order_id: int) -> Optional[Dict]:
        order = self.order_dao.get_order_by_id(order_id)
        if not order:
            return None
        logs = self.oper_log_dao.list_by_order(order_id)
        # 关键：字段名对齐前端 RepairDetail.vue 期望的 operation_logs
        # oper_type 是英文代码，action 转中文给前端展示
        _OP_CN = {
            "SUBMIT": "提交报修",
            "COLLEGE_APPROVE_PASS": "院级通过",
            "COLLEGE_APPROVE_REJECT": "院级驳回",
            "SCHOOL_APPROVE_PASS": "校级通过",
            "SCHOOL_APPROVE_REJECT": "校级驳回",
            "DISPATCH": "派单",
            "ACCEPT": "接单",
            "UPDATE_REPAIR": "更新维修",
            "FINISH_REPAIR": "维修完成",
            "ACCEPTANCE_PASS": "验收通过",
            "ACCEPTANCE_REJECT": "验收驳回",
            "RESUBMIT": "返工重提",
        }
        for l in logs:
            l["action"] = _OP_CN.get(l.get("oper_type", ""), l.get("oper_type", ""))
        order["operation_logs"] = logs
        return order

    def list_orders(self, status: str = "", dept_id: int = 0, repairer_id: int = 0,
                    reporter_id: int = 0, keyword: str = "",
                    page_num: int = 1, page_size: int = 10) -> Tuple[List, int]:
        return self.order_dao.list_orders(
            status, dept_id, repairer_id, reporter_id, keyword, page_num, page_size
        )

    def college_approve(self, order_id: int, approver_id: int,
                        is_pass: bool, opinion: str) -> Dict:
        """学院初审（原籍出身）"""
        order = self.order_dao.get_order_by_id(order_id)
        if not order:
            return {"error": "工单不存在"}

        action = "COLLEGE_APPROVE_PASS" if is_pass else "COLLEGE_APPROVE_REJECT"
        new_status = self._ensure_transition(order["status"], action)
        if new_status is None:
            return {"error": f"当前状态({order['status']})不可初审"}

        self.order_dao.college_approve(order_id, approver_id, opinion, new_status.value)
        self._add_log(order_id, approver_id, action,
                      f"学院初审{'通过' if is_pass else '驳回'}: {opinion}")

        # 联动资产
        self._sync_asset_status(order.get("asset_id", 0), new_status.value)

        return {"status": new_status.value, "message": "初审操作完成"}

    def school_approve(self, order_id: int, approver_id: int,
                       is_pass: bool, opinion: str) -> Dict:
        """校级复审
        关键修复：校级驳回后状态是 ACCEPTANCE_REJECTED（之前错误地写为 COLLEGE_REJECTED）
        """
        order = self.order_dao.get_order_by_id(order_id)
        if not order:
            return {"error": "工单不存在"}

        action = "SCHOOL_APPROVE_PASS" if is_pass else "SCHOOL_APPROVE_REJECT"
        new_status = self._ensure_transition(order["status"], action)
        if new_status is None:
            return {"error": f"当前状态({order['status']})不可复审"}

        self.order_dao.school_approve(order_id, approver_id, opinion, new_status.value)
        self._add_log(order_id, approver_id, action,
                      f"校级复审{'通过' if is_pass else '驳回'}: {opinion}")

        # 联动资产
        self._sync_asset_status(order.get("asset_id", 0), new_status.value)

        return {"status": new_status.value, "message": "复审操作完成"}

    def dispatch_order(self, order_id: int, dispatch_user_id: int,
                       repairer_id: int, deadline: Any, remark: str,
                       dispatch_user_roles: Optional[List[str]] = None) -> Dict:
        """派单
        关键设计：仅校管（admin）可派单
        """
        order = self.order_dao.get_order_by_id(order_id)
        if not order:
            return {"error": "工单不存在"}

        # 关键修复：派单是终态前的关键环节，仅校管可执行
        # 院管有初审权但不掌握"指派维修工"这一步骤
        if dispatch_user_roles is None or "admin" not in set(dispatch_user_roles):
            return {"error": "无权限：派单仅校级管理员可执行"}

        new_status = self._ensure_transition(order["status"], "DISPATCH")
        if new_status is None:
            return {"error": f"当前状态({order['status']})不可派单"}

        # DAO 中 SQL 已硬编码 status='PENDING_REPAIR'，与 ALLOWED_TRANSITIONS 一致
        self.order_dao.dispatch_order(order_id, dispatch_user_id, repairer_id, deadline, remark)
        self._add_log(order_id, dispatch_user_id, "DISPATCH",
                      f"派单至维修工{repairer_id}, 要求完成时间{deadline}")

        # 联动资产 → REPAIRING
        self._sync_asset_status(order.get("asset_id", 0), new_status.value)

        return {"status": new_status.value, "message": "派单成功"}

    def accept_order(self, order_id: int, repairer_id: int) -> Dict:
        """维修工接单"""
        order = self.order_dao.get_order_by_id(order_id)
        if not order:
            return {"error": "工单不存在"}

        new_status = self._ensure_transition(order["status"], "ACCEPT")
        if new_status is None:
            return {"error": f"当前状态({order['status']})不可接单"}

        if order["repairer_id"] != repairer_id:
            return {"error": "该工单未派单给您"}

        # DAO 中 SQL 硬编码 status='REPAIRING'，需要更新为 REPAIR_ACCEPTED
        # 但原 SQL 写的是 REPAIRING，逻辑层这里直接走 status 更新
        # 为了与 redesign 状态机一致，这里用 update_order_status
        self.order_dao.update_order_status(order_id, new_status.value,
                                           extra_set="repair_start_time = NOW()")
        self._add_log(order_id, repairer_id, "ACCEPT", "维修工接单，开始维修")

        # 资产状态保持 REPAIRING
        self._sync_asset_status(order.get("asset_id", 0), new_status.value)

        return {"status": new_status.value, "message": "接单成功"}

    def update_repair_info(self, order_id: int, repairer_id: int,
                           detail: str, cost: float,
                           parts: str, invoices: str) -> Dict:
        """更新维修信息（不改变工单状态）"""
        order = self.order_dao.get_order_by_id(order_id)
        if not order:
            return {"error": "工单不存在"}
        if order["status"] != RepairOrderStatus.REPAIR_ACCEPTED.value:
            return {"error": "当前状态不可编辑维修信息"}
        if order["repairer_id"] != repairer_id:
            return {"error": "该工单不属于您"}

        if isinstance(invoices, list):
            invoices = ",".join(invoices)
        self.order_dao.update_repair_info(order_id, repairer_id, detail, cost, parts, invoices)
        self._add_log(order_id, repairer_id, "UPDATE_REPAIR", "更新维修信息")
        return {"message": "维修信息更新成功"}

    def finish_repair(self, order_id: int, repairer_id: int) -> Dict:
        """提交维修完成"""
        order = self.order_dao.get_order_by_id(order_id)
        if not order:
            return {"error": "工单不存在"}

        new_status = self._ensure_transition(order["status"], "FINISH")
        if new_status is None:
            return {"error": f"当前状态({order['status']})不可提交完成"}
        if order["repairer_id"] != repairer_id:
            return {"error": "该工单不属于您"}

        # DAO 中 SQL 硬编码 status='PENDING_ACCEPTANCE'，一致
        self.order_dao.update_order_status(order_id, new_status.value,
                                           extra_set="repair_end_time = NOW()")
        self._add_log(order_id, repairer_id, "FINISH_REPAIR", "提交维修完成，等待验收")

        # 资产状态保持 REPAIRING
        self._sync_asset_status(order.get("asset_id", 0), new_status.value)

        return {"status": new_status.value, "message": "维修完成已提交"}

    def acceptance(self, order_id: int, acceptor_id: int,
                   is_pass: bool, opinion: str) -> Dict:
        """验收"""
        order = self.order_dao.get_order_by_id(order_id)
        if not order:
            return {"error": "工单不存在"}

        action = "ACCEPTANCE_PASS" if is_pass else "ACCEPTANCE_REJECT"
        new_status = self._ensure_transition(order["status"], action)
        if new_status is None:
            return {"error": f"当前状态({order['status']})不可验收"}

        self.order_dao.acceptance(order_id, acceptor_id, is_pass, opinion, new_status.value)
        oper_type = "ACCEPTANCE_PASS" if is_pass else "ACCEPTANCE_REJECT"
        self._add_log(order_id, acceptor_id, oper_type,
                      f"验收{'通过' if is_pass else '驳回'}: {opinion}")

        # 联动资产：通过→IDLE；驳回→REPAIRING（返工）
        self._sync_asset_status(order.get("asset_id", 0), new_status.value)

        return {"status": new_status.value, "message": "验收通过" if is_pass else "验收驳回"}

    def resubmit_for_acceptance(self, order_id: int, repairer_id: int) -> Dict:
        """验收驳回后维修工重新提交验收"""
        order = self.order_dao.get_order_by_id(order_id)
        if not order:
            return {"error": "工单不存在"}

        new_status = self._ensure_transition(order["status"], "RESUBMIT")
        if new_status is None:
            return {"error": f"当前状态({order['status']})不可重新提交验收"}
        if order["repairer_id"] != repairer_id:
            return {"error": "该工单不属于您"}

        self.order_dao.update_order_status(order_id, new_status.value)
        self._add_log(order_id, repairer_id, "RESUBMIT", "返工后重新提交验收")

        self._sync_asset_status(order.get("asset_id", 0), new_status.value)
        return {"status": new_status.value, "message": "已重新提交验收"}

    def get_my_statistics(self, repairer_id: int) -> Dict:
        stats = self.order_dao.get_statistics(repairer_id)
        return stats or {
            "pending_count": 0, "repairing_count": 0,
            "acceptance_count": 0, "month_completed_count": 0,
        }

    def list_by_asset(self, asset_id: int, page_num: int = 1, page_size: int = 10) -> Tuple[List, int]:
        return self.order_dao.list_by_asset(asset_id, page_num, page_size)

    def _add_log(self, order_id: int, operator_id: int, oper_type: str, desc: str) -> None:
        try:
            self.oper_log_dao.insert_log({
                "order_id": order_id,
                "operator_id": operator_id,
                "oper_type": oper_type,
                "oper_desc": desc,
                "oper_ip": "127.0.0.1",
            })
        except Exception:
            pass
