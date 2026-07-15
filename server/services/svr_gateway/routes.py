"""
API 网关 REST 路由
仅负责：参数校验、调用 Logic 层、组装响应、认证鉴权
禁止出现 SQL 语句，禁止直接导入 DAO 层
"""
import sys
import os
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form, Query, Request, Body
from fastapi.responses import JSONResponse
from typing import Optional, List
import jwt
from datetime import datetime

from services.config_loader import (
    get_database_config, get_jwt_config, get_file_storage_config,
    get_redis_config, get_etcd_config, get_rabbitmq_config, get_llm_config
)
from data.logic.user_logic import UserLogic
from data.logic.asset_logic import AssetLogic
from data.logic.apply_logic import ApplyLogic
from data.logic.repair_logic import RepairLogic
from data.logic.check_logic import CheckLogic
from data.logic.file_logic import FileLogic
from data.logic.report_logic import ReportLogic
from thirdparty.oper_log import log_operation, log_asset_operation

router = APIRouter(prefix="/api")

# ====== Logic 层实例（懒加载） ======
_user_logic = None
_asset_logic = None
_apply_logic = None
_repair_logic = None
_check_logic = None
_file_logic = None
_report_logic = None


def _get_user_logic():
    global _user_logic
    if _user_logic is None:
        _user_logic = UserLogic(get_database_config("user_auth"), get_jwt_config())
    return _user_logic


def _get_asset_logic():
    global _asset_logic
    if _asset_logic is None:
        _asset_logic = AssetLogic(get_database_config("asset_core"))
    return _asset_logic


def _get_apply_logic():
    global _apply_logic
    if _apply_logic is None:
        # 传入 asset_core 配置，使 apply_logic 能自动联动 asset_info.status
        _apply_logic = ApplyLogic(
            get_database_config("workflow"),
            asset_db_config=get_database_config("asset_core"),
        )
    return _apply_logic


def _get_repair_logic():
    global _repair_logic
    if _repair_logic is None:
        # 传入 asset_core 配置，使 repair_logic 能自动联动 asset_info.status
        _repair_logic = RepairLogic(
            get_database_config("repair"),
            asset_db_config=get_database_config("asset_core"),
        )
    return _repair_logic


def _get_check_logic():
    global _check_logic
    if _check_logic is None:
        _check_logic = CheckLogic(
            get_database_config("inventory"),
            asset_db_config=get_database_config("asset_core"),
        )
    return _check_logic


def _get_file_logic():
    global _file_logic
    if _file_logic is None:
        _file_logic = FileLogic(get_database_config("file_storage"), get_file_storage_config())
    return _file_logic


def _get_report_logic():
    global _report_logic
    if _report_logic is None:
        _report_logic = ReportLogic(
            get_database_config("user_auth"),
            get_database_config("asset_core"),
            get_database_config("repair"),
            get_database_config("inventory"),
            get_database_config("workflow"),
        )
    return _report_logic


# ====== 统一响应 ======
def success(data=None, message="操作成功"):
    return {"code": 200, "message": message, "data": data}


def error(message="操作失败", code=400):
    return {"code": code, "message": message, "data": None}


def page_response(items, total, page_num, page_size):
    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "list": items,
            "total": total,
            "page_num": page_num,
            "page_size": page_size,
        }
    }


# ====== JWT 认证依赖 ======
def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization.replace("Bearer ", "")
    jwt_cfg = get_jwt_config()
    try:
        payload = jwt.decode(token, jwt_cfg["secret_key"], algorithms=[jwt_cfg.get("algorithm", "HS256")])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token无效")


# ====== 权限辅助函数 ======

def is_admin(user: dict) -> bool:
    return "admin" in user.get("role_keys", [])


def is_college_admin(user: dict) -> bool:
    return "college_admin" in user.get("role_keys", [])


def is_repairer(user: dict) -> bool:
    return "repairer" in user.get("role_keys", [])


def require_roles(*role_keys: str):
    """依赖工厂：仅允许指定角色访问"""
    def check(current_user: dict = Depends(get_current_user)):
        user_roles = current_user.get("role_keys", [])
        if not any(r in user_roles for r in role_keys):
            raise HTTPException(status_code=403, detail="无权限")
        return current_user
    return check


def get_visible_dept_id(user: dict) -> int:
    """校级管理员看全部（返回0表示不过滤），其他人只看本部门"""
    if is_admin(user):
        return 0
    return user.get("dept_id", 0)


# ==================== 用户权限服务接口 ====================

@router.post("/auth/login")
async def login(request: Request, data: dict = Body(...)):
    logic = _get_user_logic()
    result = logic.login(data["username"], data["password"])
    if not result:
        return error("用户名或密码错误")
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), result["user_info"]["user_id"], data["username"],
                  "LOGIN", f"用户登录", oper_ip)
    return success(result)


@router.get("/user/list")
async def user_list(keyword: str = Query(""), dept_id: int = Query(0),
                    status: int = Query(-1), page_num: int = Query(1),
                    page_size: int = Query(10),
                    current_user=Depends(get_current_user)):
    if not is_admin(current_user) and not is_college_admin(current_user):
        raise HTTPException(status_code=403, detail="无权限")

    visible_dept = get_visible_dept_id(current_user)
    if visible_dept:
        if dept_id and dept_id != visible_dept:
            raise HTTPException(status_code=403, detail="无权查看其他部门用户")
        dept_id = visible_dept

    logic = _get_user_logic()
    items, total = logic.list_users(keyword, dept_id, status, page_num, page_size)
    return page_response(items, total, page_num, page_size)


@router.post("/user")
async def create_user(request: Request, data: dict = Body(...), current_user=Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="无权限，仅管理员可创建用户")
    logic = _get_user_logic()
    logic.create_user(data)
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "CREATE_USER",
                  f"创建用户: {data.get('username')}", oper_ip)
    return success(None, "用户创建成功")


@router.put("/user")
async def update_user(request: Request, data: dict = Body(...), current_user=Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="无权限，仅管理员可修改用户")
    logic = _get_user_logic()
    if not logic.update_user(data):
        return error("用户不存在")
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "UPDATE_USER",
                  f"更新用户: {data.get('user_id')}", oper_ip)
    return success(None, "更新成功")


@router.delete("/user/{user_id}")
async def delete_user(request: Request, user_id: int, current_user=Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="无权限，仅管理员可删除用户")
    logic = _get_user_logic()
    logic.delete_user(user_id)
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "DELETE_USER",
                  f"删除用户: {user_id}", oper_ip)
    return success(None, "用户已删除")


@router.get("/user/profile")
async def user_profile(current_user=Depends(get_current_user)):
    logic = _get_user_logic()
    user = logic.get_user_info(current_user["user_id"])
    if not user:
        return error("用户不存在")
    return success(user)


@router.put("/user/password")
async def change_password(request: Request, data: dict = Body(...), current_user=Depends(get_current_user)):
    logic = _get_user_logic()
    if not logic.change_password(current_user["user_id"],
                                  data.get("old_password", ""),
                                  data.get("new_password", "")):
        return error("原密码错误或修改失败")
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "CHANGE_PASSWORD",
                  "修改密码", oper_ip)
    return success(None, "密码修改成功")


@router.get("/role/list")
async def role_list(keyword: str = Query(""), page_num: int = Query(1),
                    page_size: int = Query(10),
                    current_user=Depends(get_current_user)):
    logic = _get_user_logic()
    items, total = logic.list_roles(keyword, page_num, page_size)
    return page_response(items, total, page_num, page_size)


@router.get("/dept/tree")
async def dept_tree(current_user=Depends(get_current_user)):
    logic = _get_user_logic()
    tree = logic.get_dept_tree()
    return success(tree)


@router.get("/user/menus")
async def user_menus(current_user=Depends(get_current_user)):
    logic = _get_user_logic()
    menus = logic.get_user_menus(current_user["user_id"])
    return success(menus)


@router.get("/user/perms")
async def user_perms(current_user=Depends(get_current_user)):
    """前后端协同：返回当前用户扁平权限码列表

    前端用这份 perms + 自己路由表里的 meta.perms 做权限匹配与菜单过滤；
    后端不再关心菜单的 path/component。
    """
    logic = _get_user_logic()
    perms = logic.get_user_perms(current_user["user_id"])
    return success(perms)


@router.get("/user/repairers")
async def list_repairers(current_user=Depends(get_current_user)):
    logic = _get_user_logic()
    repairers = logic.list_repairers()
    return success(repairers)


# ==================== 资产核心服务接口 ====================

@router.get("/asset/list")
async def asset_list(keyword: str = Query(""), category_id: int = Query(0),
                     status: int = Query(0), dept_id: int = Query(0),
                     page_num: int = Query(1), page_size: int = Query(10),
                     # _auth=Depends(require_roles("admin", "college_admin")),
                     current_user=Depends(get_current_user)):
    visible_dept = get_visible_dept_id(current_user)
    if visible_dept:
        if dept_id and dept_id != visible_dept:
            raise HTTPException(status_code=403, detail="无权查看其他部门资产")
        dept_id = visible_dept

    logic = _get_asset_logic()
    items, total = logic.list_assets(keyword, category_id, status, dept_id, page_num, page_size)
    return page_response(items, total, page_num, page_size)


@router.get("/asset/{asset_id}")
async def asset_detail(asset_id: int, current_user=Depends(get_current_user)):
    logic = _get_asset_logic()
    detail = logic.get_asset_detail(asset_id)
    if not detail:
        return error("资产不存在")
    return success(detail)


@router.post("/asset")
async def create_asset(request: Request, data: dict = Body(...), current_user=Depends(get_current_user)):
    if not is_admin(current_user) and not is_college_admin(current_user):
        raise HTTPException(status_code=403, detail="无权限，仅管理员和院级管理员可创建资产")
    logic = _get_asset_logic()
    result = logic.create_asset(data, current_user["user_id"])
    oper_ip = request.client.host if request.client else "127.0.0.1"
    asset_id = result.get("asset_id") if isinstance(result, dict) else 0
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "CREATE_ASSET",
                  f"新增资产: {data.get('asset_name', '')}", oper_ip)
    if asset_id:
        log_asset_operation(get_database_config("asset_core"), asset_id,
                            current_user["user_id"], "CREATE",
                            "", "", "", oper_ip)
    return success(result, "资产创建成功")


@router.put("/asset")
async def update_asset(request: Request, data: dict = Body(...), current_user=Depends(get_current_user)):
    if not is_admin(current_user) and not is_college_admin(current_user):
        raise HTTPException(status_code=403, detail="无权限，仅管理员和院级管理员可修改资产")
    logic = _get_asset_logic()
    result = logic.update_asset(data, current_user["user_id"])
    if result and "error" in result:
        return error(f"并发冲突，当前版本: {result.get('current_version')}")
    oper_ip = request.client.host if request.client else "127.0.0.1"
    asset_id = data.get("asset_id", 0)
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "UPDATE_ASSET",
                  f"更新资产: asset_id={asset_id}", oper_ip)
    if asset_id and result and "error" not in result:
        log_asset_operation(get_database_config("asset_core"), asset_id,
                            current_user["user_id"], "UPDATE",
                            "", "", "", oper_ip)
    return success(result, "更新成功")


@router.delete("/asset/{asset_id}")
async def delete_asset(request: Request, asset_id: int, current_user=Depends(get_current_user)):
    if not is_admin(current_user) and not is_college_admin(current_user):
        raise HTTPException(status_code=403, detail="无权限，仅管理员和院级管理员可删除资产")
    logic = _get_asset_logic()
    logic.delete_asset(asset_id)
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "DELETE_ASSET",
                  f"删除资产: asset_id={asset_id}", oper_ip)
    log_asset_operation(get_database_config("asset_core"), asset_id,
                        current_user["user_id"], "DELETE",
                        "", "", "", oper_ip)
    return success(None, "资产已删除")


@router.post("/asset/import")
async def import_assets(request: Request, file: UploadFile = File(...), _auth=Depends(require_roles("admin", "college_admin")), current_user=Depends(get_current_user)):
    logic = _get_asset_logic()
    temp_path = f"/tmp/asset_import_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    content = await file.read()
    with open(temp_path, "wb") as f:
        f.write(content)
    result = logic.import_assets(temp_path, current_user["user_id"])
    os.remove(temp_path)
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "IMPORT_ASSET",
                  f"批量导入资产: 成功{result['success_count']}条, 失败{result['fail_count']}条", oper_ip)
    return success(result, f"导入完成: 成功{result['success_count']}条, 失败{result['fail_count']}条")


@router.get("/asset/export")
async def export_assets(request: Request, keyword: str = Query(""), category_id: int = Query(0),
                        status: int = Query(0), dept_id: int = Query(0),
                        location: str = Query(""), page_num: int = Query(1), page_size: int = Query(10),
                        _auth=Depends(require_roles("admin", "college_admin")),
                        current_user=Depends(get_current_user)):
    logic = _get_asset_logic()
    output_path = logic.export_assets(keyword, category_id, status, dept_id)
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "EXPORT_ASSET",
                  "导出资产", oper_ip)
    return success({"file_path": output_path}, "导出成功")


@router.get("/asset/category/list")
async def category_list(current_user=Depends(get_current_user)):
    logic = _get_asset_logic()
    categories = logic.get_category_list()
    return success(categories)


@router.get("/asset/status/list")
async def asset_status_list(current_user=Depends(get_current_user)):
    logic = _get_asset_logic()
    status_list = logic.get_status_list()
    return success(status_list)


# ==================== 流程审批服务接口 ====================

# 通用申请提交工具（合并 borrow/return/scrap 三个端点，消除重复代码）
async def _submit_apply_internal(apply_type: str, request: Request, data: dict, current_user: dict):
    """统一处理三种申请（BORROW/RETURN/SCRAP）的提交
    资产状态联动交给 ApplyLogic.submit_apply 内部完成
    """
    logic = _get_apply_logic()
    data["apply_type"] = apply_type
    data["applicant_id"] = current_user["user_id"]
    data["dept_id"] = current_user.get("dept_id", 0)

    # 业务校验：仅 IDLE/USING 状态的资产可领用/归还/报废
    asset_id = data.get("asset_id", 0)
    if asset_id:
        asset_logic = _get_asset_logic()
        asset = asset_logic.get_asset_detail(asset_id)
        if not asset:
            return error("资产不存在")
        # print(asset)
        cur_status = asset.get("status")
        # 1=IDLE, 2=USING
        if apply_type in ("BORROW", "SCRAP") and cur_status != 1:
            return error(f"当前资产状态({cur_status})不允许{apply_type}申请，仅IDLE可申请")
        if apply_type == "RETURN" and cur_status != 2:
            return error(f"当前资产状态({cur_status})不允许归还申请，仅USING可归还")
        # === 角色 / 归属校验 ===
        user_roles = current_user.get("role_keys", [])
        user_id = current_user.get("user_id", 0)
        user_dept = current_user.get("dept_id", 0)
        is_staff = "admin" in user_roles or "college_admin" in user_roles  # 校管 / 院管

        # 报废：仅校管/院管可发起
        if apply_type == "SCRAP" and not is_staff:
            return error("报废申请仅校管/院管可发起")

        # 归还：必须是当前使用人本人（校管/院管也不允许代发起——东西不在他手里）
        # 关键规则：谁借的谁还，绝对不允许代发起
        if apply_type == "RETURN":
            asset_user = asset.get("user_id", 0)
            if asset_user != user_id:
                return error("仅资产当前使用人本人可发起归还，无法代他人发起")

        # 领用/报废：非校管/院管必须在本部门
        if apply_type in ("BORROW", "SCRAP") and not is_staff:
            asset_dept = asset.get("dept_id", 0)
            if user_dept and asset_dept and asset_dept != user_dept:
                return error("仅可对本部门资产发起申请")

    result = logic.submit_apply(data)

    oper_ip = request.client.host if request.client else "127.0.0.1"
    type_cn = {"BORROW": "领用", "RETURN": "归还", "SCRAP": "报废"}.get(apply_type, apply_type)
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], f"APPLY_{apply_type}",
                  f"提交{type_cn}申请: asset_id={asset_id}", oper_ip)
    return success(result, f"{type_cn}申请已提交")


@router.post("/apply/borrow")
async def apply_borrow(request: Request, data: dict = Body(...), current_user=Depends(get_current_user)):
    return await _submit_apply_internal("BORROW", request, data, current_user)


@router.post("/apply/return")
async def apply_return(request: Request, data: dict = Body(...), current_user=Depends(get_current_user)):
    return await _submit_apply_internal("RETURN", request, data, current_user)


@router.post("/apply/scrap")
async def apply_scrap(request: Request, data: dict = Body(...), current_user=Depends(get_current_user)):
    return await _submit_apply_internal("SCRAP", request, data, current_user)


@router.get("/apply/my")
async def my_applies(apply_type: str = Query(""), status: str = Query(""),
                     page_num: int = Query(1), page_size: int = Query(10),
                     current_user=Depends(get_current_user)):
    print(dict(current_user))
    logic = _get_apply_logic()
    items, total = logic.list_my_applies(
        applicant_id=current_user["user_id"],
        dept_id=current_user["dept_id"],
        apply_type=apply_type, status=status,
        page_num=page_num, page_size=page_size,
    )
    return page_response(items, total, page_num, page_size)


@router.get("/apply/pending")
async def pending_applies(apply_type: str = Query(""), page_num: int = Query(1),
                          page_size: int = Query(10),
                          current_user=Depends(get_current_user)):
    if not is_admin(current_user) and not is_college_admin(current_user):
        raise HTTPException(status_code=403, detail="无权限")
    dept_id = get_visible_dept_id(current_user)
    logic = _get_apply_logic()
    items, total = logic.list_pending(
        approver_id=current_user["user_id"],
        dept_id=dept_id,
        apply_type=apply_type, page_num=page_num, page_size=page_size,
        approver_roles=current_user.get("role_keys", []),
    )
    return page_response(items, total, page_num, page_size)


@router.put("/apply/approve")
async def approve_apply(
        request: Request, data: dict = Body(...),
        current_user=Depends(get_current_user)
):
    # 关键修复：不再用 require_roles 装饰器（它会同时放行 admin 和 college_admin）
    # 角色越权防护下沉到 ApplyLogic.approve 内部：
    #   节点1（院级初审 PENDING_COLLEGE）：仅 college_admin / admin
    #   节点2（校级复审 PENDING_SCHOOL）：严格仅 admin
    logic = _get_apply_logic()
    # approve_node 改为可选：logic 层会按当前 status 自动推断
    # 前端若传了，会与 logic 推断结果强校验，确保节点不被绕过
    approve_node = data.get("approve_node")
    result = logic.approve(
        apply_id=data["apply_id"],
        approver_id=current_user["user_id"],
        action=data["action"],
        opinion=data.get("opinion", ""),
        approve_node=approve_node,
        approver_dept_id=current_user.get("dept_id", 0),
        approver_roles=current_user.get("role_keys", []),
    )
    if "error" in result:
        return error(result["error"])

    # 资产状态联动已由 ApplyLogic.approve 内部完成，无需路由层重复处理

    oper_ip = request.client.host if request.client else "127.0.0.1"
    action_label = "通过" if data.get("action") == "APPROVE" else "驳回"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "APPROVE_APPLY",
                  f"审批申请{action_label}: apply_id={data['apply_id']}", oper_ip)
    return success(None, result["message"])


# 申请人主动撤回申请
@router.put("/apply/cancel/{apply_id}")
async def cancel_apply_route(
        request: Request, apply_id: int,
        data: dict = Body(default={}),
        current_user=Depends(get_current_user)
):
    """申请人主动撤回未完成的申请"""
    logic = _get_apply_logic()
    result = logic.cancel_apply(
        apply_id=apply_id,
        operator_id=current_user["user_id"],
        opinion=data.get("opinion", "") if isinstance(data, dict) else ""
    )
    if "error" in result:
        return error(result["error"])
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "CANCEL_APPLY",
                  f"撤回申请: apply_id={apply_id}", oper_ip)
    return success(None, result["message"])


@router.get("/apply/approved")
async def approved_applies(apply_type: str = Query(""), status: str = Query(""),
                           page_num: int = Query(1),
                           page_size: int = Query(10), current_user=Depends(get_current_user)):
    # 校验 status 只能是已审批终态（不允许 PENDING_* 等中间态）
    if status and status not in ("APPROVED", "REJECTED", "CANCELLED"):
        return error(f"不支持的状态过滤: {status}")
    # 校验 apply_type（仅允许 BORROW/RETURN/SCRAP；空=全部）
    if apply_type and apply_type not in ("BORROW", "RETURN", "SCRAP"):
        return error(f"不支持的申请类型: {apply_type}")
    logic = _get_apply_logic()
    dept_id = 0 if "admin" in current_user.get("role_keys", []) else current_user.get("dept_id", 0)
    items, total = logic.list_approved(
        dept_id=dept_id, status=status, apply_type=apply_type,
        page_num=page_num, page_size=page_size,
    )
    return page_response(items, total, page_num, page_size)


@router.get("/apply/{apply_id}")
async def apply_detail(apply_id: int, current_user=Depends(get_current_user)):
    logic = _get_apply_logic()
    detail = logic.get_apply_detail(apply_id)
    if not detail:
        return error("申请不存在")
    return success(detail)


# ==================== 维修工单服务接口 ====================

@router.post("/repair/submit")
async def submit_repair(request: Request, data: dict = Body(...), current_user=Depends(get_current_user)):
    logic = _get_repair_logic()
    data["reporter_id"] = current_user["user_id"]
    data["dept_id"] = current_user.get("dept_id", 0)

    # 业务校验：仅 IDLE 闲置状态的资产可报修（避免流程中重复报修）
    asset_id = data.get("asset_id", 0)
    if asset_id:
        asset_logic = _get_asset_logic()
        asset = asset_logic.get_asset_detail(asset_id)
        if not asset:
            return error("资产不存在")
        cur_status = asset.get("status")
        if cur_status != 1:  # 1=IDLE 闲置
            return error(f"当前资产状态({cur_status})不允许报修，仅【闲置】状态可发起报修")
        # 部门归属校验：非校管/院管只能报修本部门资产
        user_roles = current_user.get("role_keys", [])
        user_dept = current_user.get("dept_id", 0)
        is_staff = "admin" in user_roles or "college_admin" in user_roles
        if not is_staff:
            asset_dept = asset.get("dept_id", 0)
            if user_dept and asset_dept and asset_dept != user_dept:
                return error("仅可对本部门资产发起报修")

    result = logic.submit_order(data)

    oper_ip = request.client.host if request.client else "127.0.0.1"
    order_id = result.get("order_id") if isinstance(result, dict) else 0
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "SUBMIT_REPAIR",
                  f"提交报修工单: order_id={order_id}", oper_ip)
    # 维修工单日志已由 RepairLogic._add_log() 写入（含"提交报修"），路由层不再重复写
    return success(result, "报修工单已提交")


@router.get("/repair/list")
async def repair_list(status: str = Query(""), dept_id: int = Query(0),
                      repairer_id: int = Query(0), keyword: str = Query(""),
                      page_num: int = Query(1), page_size: int = Query(10),
                      current_user=Depends(get_current_user)):
    logic = _get_repair_logic()
    user_dept = get_visible_dept_id(current_user)
    reporter_id = 0
    repairer_filter = repairer_id
    dept_filter = dept_id

    if is_admin(current_user):
        # 校管默认看待复审，已指定 status 则尊重参数
        if not status:
            status = "PENDING_SCHOOL_APPROVE"
    elif is_repairer(current_user):
        # repairer 看派给自己的
        repairer_filter = current_user["user_id"]
    elif is_college_admin(current_user):
        # 院管默认看待初审本学院
        if not status:
            status = "PENDING_COLLEGE_APPROVE"
        if dept_filter and dept_filter != user_dept:
            raise HTTPException(status_code=403, detail="无权查看其他部门工单")
        dept_filter = user_dept
    else:
        # 普通用户看自己报修的
        reporter_id = current_user["user_id"]

    items, total = logic.list_orders(
        status=status, dept_id=dept_filter, repairer_id=repairer_filter,
        reporter_id=reporter_id, keyword=keyword, page_num=page_num, page_size=page_size
    )
    return page_response(items, total, page_num, page_size)


@router.get("/repair/{order_id}")
async def repair_detail(order_id: int, current_user=Depends(get_current_user)):
    logic = _get_repair_logic()
    detail = logic.get_order_detail(order_id)
    if not detail:
        return error("工单不存在")
    return success(detail)


@router.put("/repair/college-approve")
async def college_approve(request: Request, data: dict = Body(...), current_user=Depends(get_current_user)):
    if not is_college_admin(current_user):
        raise HTTPException(status_code=403, detail="无权限，仅院级管理员可初审")
    logic = _get_repair_logic()
    order = logic.get_order_detail(data["order_id"])
    if order and order.get("dept_id") != current_user.get("dept_id", 0):
        raise HTTPException(status_code=403, detail="无权审核其他学院的工单")
    result = logic.college_approve(
        order_id=data["order_id"],
        approver_id=current_user["user_id"],
        is_pass=data["is_pass"],
        opinion=data.get("opinion", ""),
    )
    if "error" in result:
        return error(result["error"])

    # 资产状态联动已由 RepairLogic 内部完成
    # 维修操作日志已由 RepairLogic._add_log() 写入（含中文描述），路由层不再重复写

    return success(None, result["message"])


@router.put("/repair/school-approve")
async def school_approve(request: Request, data: dict = Body(...), current_user=Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="无权限，仅校级管理员可复审")
    logic = _get_repair_logic()
    result = logic.school_approve(
        order_id=data["order_id"],
        approver_id=current_user["user_id"],
        is_pass=data["is_pass"],
        opinion=data.get("opinion", ""),
    )
    if "error" in result:
        return error(result["error"])

    # 资产状态联动已由 RepairLogic 内部完成
    # 校级驳回 → ACCEPTANCE_REJECTED → asset 保持 REPAIRING（返工）
    # 维修操作日志已由 RepairLogic._add_log() 写入，路由层不再重复写

    return success(None, result["message"])


@router.put("/repair/dispatch")
async def dispatch_order(request: Request, data: dict = Body(...), _auth=Depends(require_roles("admin")), current_user=Depends(get_current_user)):
    logic = _get_repair_logic()
    deadline = data.get("deadline")
    result = logic.dispatch_order(
        order_id=data["order_id"],
        dispatch_user_id=current_user["user_id"],
        repairer_id=data["repairer_id"],
        deadline=deadline,
        remark=data.get("remark", ""),
        dispatch_user_roles=current_user.get("role_keys", []),
    )
    if "error" in result:
        return error(result["error"])

    # 资产状态联动已由 RepairLogic 内部完成（→ REPAIRING）
    # 维修操作日志已由 RepairLogic._add_log() 写入，路由层不再重复写

    return success(None, result["message"])


@router.put("/repair/accept")
async def accept_order(request: Request, data: dict = Body(...), _auth=Depends(require_roles("repairer")), current_user=Depends(get_current_user)):
    logic = _get_repair_logic()
    result = logic.accept_order(
        order_id=data["order_id"],
        repairer_id=current_user["user_id"],
    )
    if "error" in result:
        return error(result["error"])
    # 维修操作日志已由 RepairLogic._add_log() 写入，路由层不再重复写
    return success(None, result["message"])


@router.put("/repair/update-repair")
async def update_repair_info(request: Request, data: dict = Body(...), _auth=Depends(require_roles("repairer")), current_user=Depends(get_current_user)):
    logic = _get_repair_logic()
    result = logic.update_repair_info(
        order_id=data["order_id"],
        repairer_id=current_user["user_id"],
        detail=data.get("repair_detail", ""),
        cost=data.get("repair_cost", 0),
        parts=data.get("parts_detail", ""),
        invoices=data.get("invoice_files", ""),
    )
    if "error" in result:
        return error(result["error"])
    # 维修操作日志已由 RepairLogic._add_log() 写入，路由层不再重复写
    return success(None, result["message"])


@router.put("/repair/finish")
async def finish_repair(request: Request, data: dict = Body(...), _auth=Depends(require_roles("repairer")), current_user=Depends(get_current_user)):
    logic = _get_repair_logic()
    result = logic.finish_repair(
        order_id=data["order_id"],
        repairer_id=current_user["user_id"],
    )
    if "error" in result:
        return error(result["error"])
    # 维修操作日志已由 RepairLogic._add_log() 写入，路由层不再重复写
    return success(None, result["message"])


@router.put("/repair/acceptance")
async def acceptance(request: Request, data: dict = Body(...), current_user=Depends(get_current_user)):
    # 关键修复：验收是工单终态环节（资产回 IDLE），仅校管可执行
    # 院管(初审权限)不能再越权做终态验收
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="无权限，仅校级管理员可验收")
    logic = _get_repair_logic()
    result = logic.acceptance(
        order_id=data["order_id"],
        acceptor_id=current_user["user_id"],
        is_pass=data["is_pass"],
        opinion=data.get("opinion", ""),
    )
    if "error" in result:
        return error(result["error"])

    # 资产状态联动已由 RepairLogic 内部完成
    # 通过 → asset IDLE；驳回 → asset 保持 REPAIRING（返工）
    # 维修操作日志已由 RepairLogic._add_log() 写入，路由层不再重复写

    return success(None, result["message"])


# 维修工返工后重新提交验收
@router.put("/repair/resubmit/{order_id}")
async def repair_resubmit(request: Request, order_id: int, current_user=Depends(get_current_user)):
    if not is_repairer(current_user):
        raise HTTPException(status_code=403, detail="无权限，仅维修工可重新提交")
    logic = _get_repair_logic()
    result = logic.resubmit_for_acceptance(
        order_id=order_id,
        repairer_id=current_user["user_id"]
    )
    if "error" in result:
        return error(result["error"])
    # 维修操作日志已由 RepairLogic._add_log() 写入，路由层不再重复写
    return success(None, result["message"])


@router.get("/repair/statistics/my")
async def my_statistics(current_user=Depends(get_current_user)):
    logic = _get_repair_logic()
    stats = logic.get_my_statistics(current_user["user_id"])
    return success(stats)


# ==================== 协同盘点服务接口 ====================

@router.post("/check/task")
async def create_check_task(request: Request, data: dict = Body(...), _auth=Depends(require_roles("admin", "college_admin")), current_user=Depends(get_current_user)):
    logic = _get_check_logic()
    data["manager_id"] = current_user["user_id"]
    result = logic.create_task(data)
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "CREATE_CHECK_TASK",
                  f"创建盘点任务: {data.get('task_name', '')}", oper_ip)
    return success(result, "盘点任务已创建")


@router.put("/check/task/{task_id}/start")
async def start_check_task(request: Request, task_id: int, _auth=Depends(require_roles("admin", "college_admin")), current_user=Depends(get_current_user)):
    logic = _get_check_logic()
    result = logic.start_task(task_id)
    if "error" in result:
        return error(result["error"])
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "START_CHECK_TASK",
                  f"启动盘点任务: {task_id}", oper_ip)
    return success(result, "盘点任务已开始")


@router.get("/check/task/list")
async def check_task_list(request: Request, status: str = Query(""), page_num: int = Query(1),
                          page_size: int = Query(10),
                          _auth=Depends(require_roles("admin", "college_admin")),
                          current_user=Depends(get_current_user)):
    logic = _get_check_logic()
    dept_id = get_visible_dept_id(current_user)
    # 传入当前用户信息用于数据权限过滤
    items, total = logic.list_tasks(
        status=status,
        dept_id=dept_id,
        page_num=page_num,
        page_size=page_size,
        current_user=current_user
    )
    return page_response(items, total, page_num, page_size)



@router.get("/check/sheet/{task_id}")
async def get_sheet_data(task_id: int, _auth=Depends(require_roles("admin", "college_admin")), current_user=Depends(get_current_user)):
    logic = _get_check_logic()
    result = logic.get_sheet_data(task_id)
    if "error" in result:
        return error(result["error"])
    return success(result)


@router.post("/check/sheet/save")
async def save_sheet_data(request: Request, data: dict = Body(...), _auth=Depends(require_roles("admin", "college_admin")), current_user=Depends(get_current_user)):
    logic = _get_check_logic()
    result = logic.save_sheet_data(data["task_id"], data.get("details", []))
    if "error" in result:
        return error(result["error"])
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "SAVE_CHECK_SHEET",
                  f"保存盘点数据: task_id={data['task_id']}", oper_ip)
    return success(None, result["message"])


@router.post("/check/diff/analyze")
async def analyze_diff(request: Request, data: dict = Body(...), _auth=Depends(require_roles("admin", "college_admin")), current_user=Depends(get_current_user)):
    logic = _get_check_logic()
    result = logic.analyze_diff(data["task_id"])
    if "error" in result:
        return error(result["error"])
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "ANALYZE_DIFF",
                  f"差异分析: task_id={data['task_id']}", oper_ip)
    return success(result, "差异分析完成")


@router.get("/check/diff/{task_id}")
async def get_diff_report(task_id: int, _auth=Depends(require_roles("admin", "college_admin")), current_user=Depends(get_current_user)):
    logic = _get_check_logic()
    report = logic.get_diff_report(task_id)
    if not report:
        return error("暂无差异报告")
    return success(report)


@router.put("/check/confirm")
async def confirm_check(request: Request, data: dict = Body(...), _auth=Depends(require_roles("admin", "college_admin")), current_user=Depends(get_current_user)):
    logic = _get_check_logic()
    result = logic.confirm_result(data["task_id"])
    if "error" in result:
        return error(result["error"])
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "CONFIRM_CHECK",
                  f"确认盘点结果: task_id={data['task_id']}", oper_ip)
    return success(None, result["message"])


# ==================== 文件存储服务接口 ====================

@router.post("/file/upload")
async def upload_file(request: Request, file: UploadFile = File(...), biz_type: str = Form(""),
                      biz_id: int = Form(0), current_user=Depends(get_current_user)):
    logic = _get_file_logic()
    content = await file.read()
    result = logic.upload_file(content, file.filename, biz_type, biz_id, current_user["user_id"])
    if result and "error" in result:
        return error(result["error"])
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "UPLOAD_FILE",
                  f"上传文件: {file.filename}, biz_type={biz_type}", oper_ip)
    return success(result, "上传成功")


@router.get("/file/{file_id}")
async def get_file_info(file_id: int, current_user=Depends(get_current_user)):
    logic = _get_file_logic()
    info = logic.get_file_info(file_id)
    if not info:
        return error("文件不存在")
    return success(info)


@router.get("/file/list")
async def file_list(biz_type: str = Query(""), biz_id: int = Query(0),
                    page_num: int = Query(1), page_size: int = Query(20),
                    current_user=Depends(get_current_user)):
    logic = _get_file_logic()
    items, total = logic.list_files(biz_type, biz_id,
                                     uploader_id=0, page_num=page_num, page_size=page_size)
    return page_response(items, total, page_num, page_size)


# ==================== 统计报表服务接口 ====================

@router.get("/report/asset")
async def report_asset(_auth=Depends(require_roles("admin", "college_admin")), current_user=Depends(get_current_user)):
    logic = _get_report_logic()
    dept_id = get_visible_dept_id(current_user)
    result = logic.get_asset_report(dept_id=dept_id)
    return success(result)


@router.get("/report/repair")
async def report_repair(_auth=Depends(require_roles("admin", "college_admin")), current_user=Depends(get_current_user)):
    logic = _get_report_logic()
    dept_id = get_visible_dept_id(current_user)
    result = logic.get_repair_report(dept_id=dept_id)
    return success(result)


@router.get("/report/inventory")
async def report_inventory(_auth=Depends(require_roles("admin", "college_admin")), current_user=Depends(get_current_user)):
    logic = _get_report_logic()
    dept_id = get_visible_dept_id(current_user)
    result = logic.get_inventory_report(dept_id=dept_id)
    return success(result)


@router.get("/report/dashboard")
async def dashboard_overview(_auth=Depends(require_roles("admin", "college_admin")), current_user=Depends(get_current_user)):
    logic = _get_report_logic()
    dept_id = get_visible_dept_id(current_user)
    result = logic.get_dashboard_overview(dept_id=dept_id)
    return success(result)


@router.get("/report/export")
async def export_report(request: Request, _auth=Depends(require_roles("admin", "college_admin")), current_user=Depends(get_current_user)):
    logic = _get_report_logic()
    file_path = logic.export_report()
    if not file_path:
        return error("导出失败，请安装 openpyxl")
    oper_ip = request.client.host if request.client else "127.0.0.1"
    log_operation(get_database_config("user_auth"), current_user["user_id"],
                  current_user["username"], "EXPORT_REPORT",
                  "导出综合报表", oper_ip)
    return success({"file_path": file_path}, "导出成功")