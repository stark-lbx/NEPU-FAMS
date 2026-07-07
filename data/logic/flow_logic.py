from data.basic.flow_dao import AuditFlowDao, BorrowDao, RepairDao, ScrapDao
from data.basic.asset_dao import AssetDao
from common.utils import generate_biz_id, now_str
from common.constants import *
from common.log import get_logger

logger = get_logger("flow_logic")


class FlowLogic:
    def __init__(self, db_path: str = "fams.db"):
        self.flow_dao = AuditFlowDao(db_path)
        self.borrow_dao = BorrowDao(db_path)
        self.repair_dao = RepairDao(db_path)
        self.scrap_dao = ScrapDao(db_path)
        self.asset_dao = AssetDao(db_path)

    def _check_asset_no_active_flow(self, asset_biz_id: str, caller: str):
        """同一资产只能存在于一条进行中的流程，检查三类业务表"""
        active = []
        for row in self.borrow_dao.active_by_asset(asset_biz_id):
            active.append(f"领用申请({row['biz_id']}, {row['borrow_status']})")
        for row in self.repair_dao.active_by_asset(asset_biz_id):
            active.append(f"报修工单({row['biz_id']}, {row['order_status']})")
        for row in self.scrap_dao.active_by_asset(asset_biz_id):
            active.append(f"报废申请({row['biz_id']}, {row['scrap_status']})")
        if active:
            raise ValueError(f"该资产已有进行中的流程：{'、'.join(active)}，请等待流程结束后再提交{caller}")

    def create_borrow_apply(self, borrow_data: dict) -> tuple:
        """创建领用申请+审批流"""
        asset_biz_id = borrow_data.get("asset_biz_id", "")
        self._check_asset_no_active_flow(asset_biz_id, "领用申请")

        borrow_biz_id = generate_biz_id()
        borrow_data["biz_id"] = borrow_biz_id
        borrow_data["borrow_status"] = "APPLY"

        # 创建领用单
        self.borrow_dao.insert(borrow_data)

        # 创建审批流
        flow_biz_id = generate_biz_id()
        flow_data = {
            "biz_id": flow_biz_id,
            "business_type": BUSINESS_TYPE_BORROW,
            "business_biz_id": borrow_biz_id,
            "apply_user_biz_id": borrow_data["borrow_user_biz_id"],
            "final_result": AUDIT_WAIT
        }
        self.flow_dao.insert(flow_data)

        # 关联审批流到领用单
        self.borrow_dao.update_by_biz_id(borrow_biz_id, {"flow_biz_id": flow_biz_id})

        logger.info(f"创建领用申请: {borrow_biz_id}, 审批流: {flow_biz_id}")
        return flow_biz_id, borrow_biz_id

    def create_repair_apply(self, repair_data: dict) -> tuple:
        """创建报修工单+审批流"""
        asset_biz_id = repair_data.get("asset_biz_id", "")
        self._check_asset_no_active_flow(asset_biz_id, "报修申请")

        repair_biz_id = generate_biz_id()
        repair_data["biz_id"] = repair_biz_id
        repair_data["order_status"] = "AUDITING"

        self.repair_dao.insert(repair_data)

        flow_biz_id = generate_biz_id()
        flow_data = {
            "biz_id": flow_biz_id,
            "business_type": BUSINESS_TYPE_REPAIR,
            "business_biz_id": repair_biz_id,
            "apply_user_biz_id": repair_data["report_user_biz_id"],
            "final_result": AUDIT_WAIT
        }
        self.flow_dao.insert(flow_data)
        self.repair_dao.update_by_biz_id(repair_biz_id, {"flow_biz_id": flow_biz_id})

        logger.info(f"创建报修工单: {repair_biz_id}, 审批流: {flow_biz_id}")
        return flow_biz_id, repair_biz_id

    def create_scrap_apply(self, scrap_data: dict) -> tuple:
        """创建报废申请+审批流"""
        asset_biz_id = scrap_data.get("asset_biz_id", "")
        self._check_asset_no_active_flow(asset_biz_id, "报废申请")

        scrap_biz_id = generate_biz_id()
        scrap_data["biz_id"] = scrap_biz_id
        scrap_data["scrap_status"] = "APPLY"

        self.scrap_dao.insert(scrap_data)

        flow_biz_id = generate_biz_id()
        flow_data = {
            "biz_id": flow_biz_id,
            "business_type": BUSINESS_TYPE_SCRAP,
            "business_biz_id": scrap_biz_id,
            "apply_user_biz_id": scrap_data["apply_user_biz_id"],
            "final_result": AUDIT_WAIT
        }
        self.flow_dao.insert(flow_data)
        self.scrap_dao.update_by_biz_id(scrap_biz_id, {"flow_biz_id": flow_biz_id})

        logger.info(f"创建报废申请: {scrap_biz_id}, 审批流: {flow_biz_id}")
        return flow_biz_id, scrap_biz_id

    def dept_audit(self, flow_biz_id: str, audit_user_biz_id: str, result: str) -> bool:
        """学院初审"""
        flow = self.flow_dao.select_by_biz_id(flow_biz_id)
        if not flow or flow["dept_audit_result"] != AUDIT_WAIT:
            raise Exception("审批单不存在或已审核")

        update_data = {
            "dept_audit_user_biz_id": audit_user_biz_id,
            "dept_audit_result": result,
            "dept_audit_time": now_str()
        }
        # 学院驳回则终审直接驳回
        if result == AUDIT_REJECT:
            update_data["final_result"] = AUDIT_REJECT
            update_data["finish_time"] = now_str()
            self._update_business_status(flow, result)

        self.flow_dao.update_by_biz_id(flow_biz_id, update_data)
        logger.info(f"学院审批完成: {flow_biz_id} 结果: {result}")
        return True

    def school_audit(self, flow_biz_id: str, audit_user_biz_id: str, result: str) -> bool:
        """校级复审"""
        flow = self.flow_dao.select_by_biz_id(flow_biz_id)
        if not flow or flow["dept_audit_result"] != AUDIT_PASS:
            raise Exception("学院未通过，不可复审")
        if flow["school_audit_result"] != AUDIT_WAIT:
            raise Exception("已复审")

        update_data = {
            "school_audit_user_biz_id": audit_user_biz_id,
            "school_audit_result": result,
            "school_audit_time": now_str(),
            "final_result": result,
            "finish_time": now_str()
        }
        self.flow_dao.update_by_biz_id(flow_biz_id, update_data)
        self._update_business_status(flow, result)
        logger.info(f"校级审批完成: {flow_biz_id} 结果: {result}")
        return True

    def dispatch_repair(self, workorder_biz_id: str, repair_user_biz_id: str, oper_user_biz_id: str) -> bool:
        """校级管理员派单给修理工"""
        repair = self.repair_dao.select_by_biz_id(workorder_biz_id)
        if not repair or repair["order_status"] != "APPROVED":
            raise Exception("工单状态异常，不可派单")
        self.repair_dao.update_by_biz_id(workorder_biz_id, {
            "order_status": "ASSIGNED",
            "repair_user_biz_id": repair_user_biz_id
        })
        logger.info(f"派单完成: {workorder_biz_id} -> {repair_user_biz_id}")
        return True

    def accept_repair(self, workorder_biz_id: str, repair_user_biz_id: str) -> bool:
        """修理工接单"""
        repair = self.repair_dao.select_by_biz_id(workorder_biz_id)
        if not repair or repair["order_status"] != "ASSIGNED":
            raise Exception("工单状态异常，不可接单")
        if repair["repair_user_biz_id"] != repair_user_biz_id:
            raise Exception("该工单未指派给您")
        self.repair_dao.update_by_biz_id(workorder_biz_id, {
            "order_status": "REPAIRING"
        })
        logger.info(f"修理工接单: {workorder_biz_id} by {repair_user_biz_id}")
        return True

    def complete_repair(self, workorder_biz_id: str, repair_user_biz_id: str,
                        repair_cost: float, repair_result: str) -> bool:
        """修理工完工"""
        repair = self.repair_dao.select_by_biz_id(workorder_biz_id)
        if not repair or repair["order_status"] != "REPAIRING":
            raise Exception("工单状态异常，不可完工")
        if repair["repair_user_biz_id"] != repair_user_biz_id:
            raise Exception("该工单未指派给您")
        self.repair_dao.update_by_biz_id(workorder_biz_id, {
            "order_status": "COMPLETED",
            "repair_cost": repair_cost,
            "repair_result": repair_result,
            "finish_time": now_str()
        })
        logger.info(f"维修完工: {workorder_biz_id} cost={repair_cost}")
        return True

    def _update_business_status(self, flow: dict, final_result: str):
        """审批完成后同步更新业务单据状态"""
        biz_type = flow["business_type"]
        biz_id = flow["business_biz_id"]

        if biz_type == BUSINESS_TYPE_BORROW:
            status = "BORROWING" if final_result == AUDIT_PASS else "REJECT"
            self.borrow_dao.update_by_biz_id(biz_id, {"borrow_status": status})
        elif biz_type == BUSINESS_TYPE_REPAIR:
            # 校级审核通过后进入"待派单"状态，而非直接进入维修
            status = "APPROVED" if final_result == AUDIT_PASS else "REJECT"
            self.repair_dao.update_by_biz_id(biz_id, {"order_status": status})
        elif biz_type == BUSINESS_TYPE_SCRAP:
            status = "SCRAPPED" if final_result == AUDIT_PASS else "REJECT"
            self.scrap_dao.update_by_biz_id(biz_id, {"scrap_status": status})
            if final_result == AUDIT_PASS:
                # 报废通过则更新资产状态为报废
                scrap = self.scrap_dao.select_by_biz_id(biz_id)
                self.asset_dao.update_by_biz_id(scrap["asset_biz_id"], {"current_status_code": "SCRAP"})

    def return_asset(self, borrow_biz_id: str, oper_user_biz_id: str) -> bool:
        """资产归还"""
        borrow = self.borrow_dao.select_by_biz_id(borrow_biz_id)
        if not borrow or borrow["borrow_status"] != "BORROWING":
            raise Exception("领用单状态异常，不可归还")

        self.borrow_dao.update_by_biz_id(borrow_biz_id, {
            "borrow_status": "RETURN",
            "actual_return_time": now_str()
        })
        # 归还后资产状态恢复为空闲
        self.asset_dao.update_by_biz_id(borrow["asset_biz_id"], {"current_status_code": "IDLE"})
        logger.info(f"资产归还完成: {borrow_biz_id}")
        return True

    def list_borrow(self, user_biz_id: str = "", dept_biz_id: str = ""):
        if dept_biz_id:
            return self.borrow_dao.list_by_dept(dept_biz_id)
        return self.borrow_dao.list_by_user(user_biz_id)

    def list_repair(self, user_biz_id: str = "", dept_biz_id: str = ""):
        if dept_biz_id:
            return self.repair_dao.list_by_dept(dept_biz_id)
        return self.repair_dao.list_by_report_user(user_biz_id)

    def list_scrap(self, user_biz_id: str = "", dept_biz_id: str = ""):
        if dept_biz_id:
            return self.scrap_dao.list_by_dept(dept_biz_id)
        return self.scrap_dao.list_by_apply_user(user_biz_id)

    def get_flow_progress(self, flow_biz_id: str) -> dict:
        flow = self.flow_dao.select_by_biz_id(flow_biz_id)
        if not flow:
            raise Exception("审批单不存在")
        steps = []
        if flow.get("dept_audit_result"):
            steps.append({
                "step_name": "学院初审",
                "auditor_user_biz_id": flow.get("dept_audit_user_biz_id", ""),
                "result": flow["dept_audit_result"],
                "audit_time": flow.get("dept_audit_time", "")
            })
        if flow.get("school_audit_result"):
            steps.append({
                "step_name": "校级复审",
                "auditor_user_biz_id": flow.get("school_audit_user_biz_id", ""),
                "result": flow["school_audit_result"],
                "audit_time": flow.get("school_audit_time", "")
            })
        return {"steps": steps, "final_result": flow.get("final_result", "WAIT")}