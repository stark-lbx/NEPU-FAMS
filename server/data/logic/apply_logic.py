"""
审批引擎、状态机、领用/归还/报废流程 业务逻辑
不得出现任何SQL语句

设计要点：
  1) 状态码统一引用 asset_status.status_code 字典（True Source of Truth）
  2) 审批动作联动更新 asset_info.status（process 态→FLOWING；终态→业务对应物理态）
  3) 审批节点由 logic 层根据当前 status 推断，调用方无须传 approve_node
  4) 状态机转移全部走 APPROVE_RULES 字典，禁止硬编码
"""
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from data.basic.apply_dao import ApplyDAO, ApproveRecordDAO


# ============================================================
# 状态码常量（与 asset_status.status_code 严格对应）
# ============================================================
class ApplyType(str, Enum):
    BORROW = "BORROW"
    RETURN = "RETURN"
    SCRAP = "SCRAP"


class ApplyStatus(str, Enum):
    PENDING_COLLEGE = "PENDING_COLLEGE"   # 待院级初审
    PENDING_SCHOOL = "PENDING_SCHOOL"     # 待校级复审
    APPROVED = "APPROVED"                 # 已通过
    REJECTED = "REJECTED"                 # 已驳回
    CANCELLED = "CANCELLED"               # 已撤回


class ApproveAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CANCEL = "CANCEL"


# 状态 ↔ 审批节点映射
# 节点 1=院审  节点 2=校审
STATUS_NODE_MAP = {
    ApplyStatus.PENDING_COLLEGE: 1,
    ApplyStatus.PENDING_SCHOOL: 2,
}

# 申请过程态 → asset_info 物理态 联动映射
# 终态 APPROVED 联动值由 apply_type 决定（BORROW→2, RETURN→1, SCRAP→4）
# 过程态 PENDING_* 统一 → 5 (FLOWING)
# 终态 REJECTED / CANCELLED → 1 (IDLE)
_APPROVED_ASSET_STATUS = {
    ApplyType.BORROW: 2,   # USING
    ApplyType.RETURN: 1,   # IDLE
    ApplyType.SCRAP: 4,    # ABANDON
}

# 状态机转移规则
APPROVE_RULES = {
    ApplyStatus.PENDING_COLLEGE: {
        ApproveAction.APPROVE: ApplyStatus.PENDING_SCHOOL,
        ApproveAction.REJECT: ApplyStatus.REJECTED,
        ApproveAction.CANCEL: ApplyStatus.CANCELLED,
    },
    ApplyStatus.PENDING_SCHOOL: {
        ApproveAction.APPROVE: ApplyStatus.APPROVED,
        ApproveAction.REJECT: ApplyStatus.REJECTED,
        ApproveAction.CANCEL: ApplyStatus.CANCELLED,
    },
}

# 校验可审批的中间态
APPROVABLE_STATUS = {ApplyStatus.PENDING_COLLEGE, ApplyStatus.PENDING_SCHOOL}

# 校验可撤回的中间态
CANCELLABLE_STATUS = {ApplyStatus.PENDING_COLLEGE, ApplyStatus.PENDING_SCHOOL}


class ApplyLogic:
    """流程审批业务逻辑"""

    def __init__(self, db_config: Dict, asset_db_config: Optional[Dict] = None):
        """
        :param db_config: workflow_db 配置
        :param asset_db_config: asset_core_db 配置（用于联动更新 asset_info）
        """
        self.apply_dao = ApplyDAO(db_config)
        self.record_dao = ApproveRecordDAO(db_config)
        self._asset_db_config = asset_db_config
        # 延迟导入避免循环依赖
        self._asset_dao = None

    # --------------------------------------------------------
    # 资产联动
    # --------------------------------------------------------
    def _get_asset_dao(self):
        if self._asset_dao is None and self._asset_db_config is not None:
            from data.basic.asset_dao import AssetDAO
            self._asset_dao = AssetDAO(self._asset_db_config)
        return self._asset_dao

    def _sync_asset_status(self, asset_id: int, apply_type: str,
                           new_status: str, applicant_id: int = 0) -> None:
        """根据申请状态联动更新 asset_info.status
        关键设计：仅在终态时改 user_id；过程态 user_id 不变
        """
        asset_dao = self._get_asset_dao()
        if asset_dao is None or not asset_id:
            return

        # 查询当前资产（带 version）
        asset = asset_dao.get_asset_by_id(asset_id)
        if not asset:
            return

        # 计算目标状态
        if new_status == ApplyStatus.APPROVED.value:
            target_status = _APPROVED_ASSET_STATUS.get(apply_type, 1)
            target_user = applicant_id if apply_type == ApplyType.BORROW.value else 0
        elif new_status in (ApplyStatus.REJECTED.value, ApplyStatus.CANCELLED.value):
            target_status = 1   # IDLE
            target_user = 0
        else:
            # 过程态 PENDING_*
            target_status = 5   # FLOWING
            target_user = 0  # 过程态不改 user_id

        # 仅当状态真的需要变才更新
        if asset["status"] != target_status or asset.get("user_id", 0) != target_user:
            asset_dao.update_asset_status(
                asset_id=asset_id,
                status_id=target_status,
                user_id=target_user,
                version=asset["version"]
            )

    # --------------------------------------------------------
    # 业务方法
    # --------------------------------------------------------
    def submit_apply(self, data: Dict) -> Optional[Dict]:
        """提交申请，初始状态为待学院初审"""
        data["status"] = ApplyStatus.PENDING_COLLEGE.value
        data["current_node"] = STATUS_NODE_MAP[ApplyStatus.PENDING_COLLEGE]
        # 关键修复：前端发的是 remark，但 SQL 字段是 reason，这里兼容
        if "reason" not in data and "remark" in data:
            data["reason"] = data.pop("remark") or ""
        data.setdefault("reason", "")
        if "expect_return_time" not in data or not data["expect_return_time"]:
            data["expect_return_time"] = None
        elif isinstance(data["expect_return_time"], str) and "T" in data["expect_return_time"]:
            data["expect_return_time"] = data["expect_return_time"].replace("T", " ").replace("Z", "")[:19]

        apply_id = self.apply_dao.insert_apply(data)
        detail = self.get_apply_detail(apply_id)

        # 联动：资产进入流程中
        asset_id = data.get("asset_id", 0)
        if asset_id:
            self._sync_asset_status(
                asset_id=asset_id,
                apply_type=data.get("apply_type", ""),
                new_status=ApplyStatus.PENDING_COLLEGE.value,
                applicant_id=data.get("applicant_id", 0)
            )

        return detail

    def get_apply_detail(self, apply_id: int) -> Optional[Dict]:
        apply = self.apply_dao.get_apply_by_id(apply_id)
        if not apply:
            return None
        records = self.record_dao.list_by_apply(apply_id)
        # 关键：字段名对齐前端 ApplyDetail.vue 期望的 approve_records
        # 包含：approver_name, dept_name, action, opinion, approve_time
        for r in records:
            r["create_time"] = r.get("approve_time")  # 前端 timeline 用 create_time
            r["node_name"] = f"第{(r.get('approve_node') or 0) + 1}节点"

        # 关键修复：在审批记录最前面插入"提交申请"第一节点
        # 该节点不入 approve_record 表，是从 apply 表本身数据合成的
        submit_node = {
            "node_id": 0,
            "node_name": "提交申请",
            "approver_id": apply.get("applicant_id"),
            "approver_name": apply.get("applicant_name", ""),
            "dept_id": apply.get("dept_id"),
            "dept_name": apply.get("dept_name", ""),
            "action": "SUBMIT",
            "opinion": apply.get("reason", "") or "",  # 申请理由即 reason
            "create_time": apply.get("create_time"),
            "approve_time": apply.get("create_time"),
        }
        records.insert(0, submit_node)
        apply["approve_records"] = records
        return apply

    def list_my_applies(self, applicant_id: int = 0, apply_type: str = "",
                        status: str = "", dept_id: int = 0,
                        page_num: int = 1, page_size: int = 10) -> Tuple:
        return self.apply_dao.list_my_applies(
            applicant_id, apply_type, status, dept_id, page_num, page_size
        )

    def list_pending(self, approver_id: int, dept_id: int = 0,
                     apply_type: str = "", page_num: int = 1, page_size: int = 10,
                     approver_roles: Optional[List[str]] = None) -> Tuple:
        return self.apply_dao.list_pending(
            approver_id, dept_id, apply_type, page_num, page_size, approver_roles
        )

    def list_approved(self, dept_id: int = 0, status: str = "",
                      apply_type: str = "",
                      page_num: int = 1, page_size: int = 10) -> Tuple:
        return self.apply_dao.list_approved(dept_id, status, apply_type, page_num, page_size)

    def approve(self, apply_id: int, approver_id: int, action: str,
                opinion: str = "", approve_node: Optional[int] = None,
                approver_dept_id: int = 0,
                approver_roles: Optional[List[str]] = None) -> Dict:
        """审批操作，状态机流转，自动推断节点
        :param approve_node: 可选；不传则根据当前 status 自动推断
        :param approver_dept_id: 审批人所属部门（用于节点1的部门归属校验）
        :param approver_roles: 审批人角色列表（如 ['admin', 'college_admin']）
                              用于节点级别的角色越权防护
        """
        apply = self.apply_dao.get_apply_by_id(apply_id)
        if not apply:
            return {"error": "申请不存在"}

        current_status_str = apply["status"]
        try:
            current_status = ApplyStatus(current_status_str)
        except ValueError:
            return {"error": f"未知状态: {current_status_str}"}

        # 校验动作合法性
        try:
            action_enum = ApproveAction(action)
        except ValueError:
            return {"error": f"非法的审批动作: {action}"}

        # CANCEL 走单独通道（仅申请人自己可撤回）
        if action_enum == ApproveAction.CANCEL:
            return self.cancel_apply(apply_id, approver_id, opinion)

        # 校验当前状态可审批
        if current_status not in APPROVABLE_STATUS:
            return {"error": f"当前状态不可审批: {current_status.value}"}

        # 校验节点：若前端传了，则必须与当前状态一致；否则自动推断
        expect_node = STATUS_NODE_MAP[current_status]
        if approve_node is not None and approve_node != expect_node:
            return {"error": f"审批节点不匹配，当前应为第{expect_node}节点审批"}

        # ====================================================================
        # 关键修复：节点级别的角色越权防护
        # 节点 1（院级初审 PENDING_COLLEGE）：严格仅 college_admin
        # 节点 2（校级复审 PENDING_SCHOOL）：严格仅 admin
        # 节点 1 还要求 college_admin 必须属于申请所属部门
        # ====================================================================
        if approver_roles is None:
            approver_roles = []
        roles_set = set(approver_roles)

        if current_status == ApplyStatus.PENDING_COLLEGE:
            # 院级初审：严格仅 college_admin，校管（admin）不允许越权代审
            if "college_admin" not in roles_set:
                return {"error": "无权限：节点1(院级初审)仅院级管理员可审批"}
            # 部门归属校验：college_admin 必须 = 申请部门
            apply_dept_id = apply.get("dept_id") or 0
            if not approver_dept_id or apply_dept_id == 0:
                return {"error": "申请或审批人部门信息缺失，无法核验部门归属"}
            if apply_dept_id != approver_dept_id:
                return {"error": f"无权限：您属于部门#{approver_dept_id}，不能审批部门#{apply_dept_id}的申请"}
        elif current_status == ApplyStatus.PENDING_SCHOOL:
            # 校级复审：严格仅 admin，院管不允许越权
            if "admin" not in roles_set:
                return {"error": "无权限：节点2(校级复审)仅校级管理员可审批"}

        # 状态流转
        new_status = APPROVE_RULES[current_status][action_enum]

        # 计算下一节点：
        #   - 进入 PENDING_SCHOOL：节点 = 2
        #   - 进入终态（APPROVED / REJECTED / CANCELLED）：保持当前节点
        new_node = (
            STATUS_NODE_MAP[new_status]
            if new_status in (ApplyStatus.PENDING_COLLEGE, ApplyStatus.PENDING_SCHOOL)
            else expect_node
        )

        # 记录审批日志
        self.record_dao.insert_record({
            "apply_id": apply_id,
            "approver_id": approver_id,
            "action": action,
            "opinion": opinion,
            "approve_node": expect_node,
        })

        # 更新申请主表
        self.apply_dao.update_apply_status(apply_id, new_status.value, new_node)

        # 联动资产状态
        self._sync_asset_status(
            asset_id=apply.get("asset_id", 0),
            apply_type=apply.get("apply_type", ""),
            new_status=new_status.value,
            applicant_id=apply.get("applicant_id", 0)
        )

        return {
            "status": new_status.value,
            "node": new_node,
            "message": "审批操作成功" if action_enum == ApproveAction.APPROVE else "已驳回"
        }

    def cancel_apply(self, apply_id: int, operator_id: int, opinion: str = "") -> Dict:
        """申请人主动撤回"""
        apply = self.apply_dao.get_apply_by_id(apply_id)
        if not apply:
            return {"error": "申请不存在"}

        # 仅申请人本人可撤回
        if apply.get("applicant_id") != operator_id:
            return {"error": "仅申请人可撤回"}

        try:
            current_status = ApplyStatus(apply["status"])
        except ValueError:
            return {"error": f"未知状态: {apply['status']}"}

        if current_status not in CANCELLABLE_STATUS:
            return {"error": f"当前状态不可撤回: {current_status.value}"}

        # 记录一条 CANCEL 审批记录
        self.record_dao.insert_record({
            "apply_id": apply_id,
            "approver_id": operator_id,
            "action": ApproveAction.CANCEL.value,
            "opinion": opinion or "申请人主动撤回",
            "approve_node": STATUS_NODE_MAP.get(current_status, 1),
        })

        # 更新主表
        self.apply_dao.update_apply_status(
            apply_id, ApplyStatus.CANCELLED.value, STATUS_NODE_MAP.get(current_status, 1)
        )

        # 联动资产回 IDLE
        self._sync_asset_status(
            asset_id=apply.get("asset_id", 0),
            apply_type=apply.get("apply_type", ""),
            new_status=ApplyStatus.CANCELLED.value,
            applicant_id=operator_id
        )

        return {"status": ApplyStatus.CANCELLED.value, "message": "已撤回"}
