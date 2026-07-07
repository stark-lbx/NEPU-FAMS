from flask import Blueprint, request, jsonify, send_file
from services.svc_gateway.auth import login_required
from common.rpc_client import RpcClientManager
from common.oper_log import oper_log
from proto.generated import user_pb2, user_pb2_grpc
from proto.generated import asset_pb2, asset_pb2_grpc
from proto.generated import flow_pb2, flow_pb2_grpc
from data.logic.flow_logic import FlowLogic
from data.basic.flow_dao import AuditFlowDao
from proto.generated import storage_pb2, storage_pb2_grpc
import io
import sqlite3
import os

api_bp = Blueprint("api", __name__)
rpc_mgr = RpcClientManager()

# 数据库路径（与 gateway 同级目录下的 fams.db）
_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fams.db")


# ==================== 通用工具函数 ====================
def _get_stub(service_name: str, stub_class):
    """获取gRPC客户端stub"""
    channel = rpc_mgr.get_channel(service_name)
    return stub_class(channel)


def _pb_node_to_dict(node):
    """将 protobuf 节点递归转为 dict"""
    d = {}
    for field in node.DESCRIPTOR.fields:
        val = getattr(node, field.name)
        if field.label == field.LABEL_REPEATED:
            d[field.name] = [_pb_node_to_dict(v) for v in val]
        elif field.type == field.TYPE_MESSAGE:
            d[field.name] = _pb_node_to_dict(val) if val else None
        else:
            d[field.name] = val
    return d


def _pb_list_to_list(pb_list):
    """将 protobuf RepeatedCompositeFieldContainer 转为 Python list[dict]"""
    return [_pb_node_to_dict(node) for node in pb_list]


def _success(data=None, msg="success"):
    return jsonify({"code": 200, "msg": msg, "data": data})


def _error(msg="error", code=400):
    return jsonify({"code": code, "msg": msg}), code


def _user_biz_id():
    return request.user.get("user_biz_id", "")


def _user_role():
    return request.user.get("role_code", "")

def _get_current_user():
    """获取当前登录用户的完整信息（从 request.user 中提取）"""
    return dict(request.user) if request.user else {}


# ==================== 1. 用户认证模块 ====================
@api_bp.route("/user/login", methods=["POST"])
def login():
    """用户登录"""
    data = request.json
    if not data.get("username") or not data.get("password"):
        return _error("用户名和密码不能为空")

    try:
        stub = _get_stub("user", user_pb2_grpc.UserServiceStub)
        resp = stub.Login(user_pb2.LoginRequest(
            username=data["username"],
            password=data["password"]
        ))
        oper_log("", "用户认证", "登录", f"用户 {data['username']} 登录成功")
        return _success({
            "token": resp.token,
            "user": {
                "biz_id": resp.user.biz_id,
                "username": resp.user.username,
                "real_name": resp.user.real_name,
                "dept_biz_id": resp.user.dept_biz_id,
                "phone": resp.user.phone,
                "email": resp.user.email
            }
        })
    except Exception as e:
        return _error(f"登录失败：{e}", 401)


@api_bp.route("/user/register", methods=["POST"])
def register():
    """用户注册"""
    data = request.json
    required = ["username", "password", "real_name", "dept_biz_id"]
    if not all(k in data for k in required):
        return _error("缺少必填参数")

    if data.get("password") != data.get("confirm_password", ""):
        return _error("两次密码输入不一致")

    # role_code 仅允许 teacher / student
    role_code = data.get("role_code", "teacher")
    if role_code not in ("teacher", "student"):
        return _error("角色类型无效，仅可选老师或学生")

    try:
        stub = _get_stub("user", user_pb2_grpc.UserServiceStub)
        resp = stub.CreateUser(user_pb2.CreateUserRequest(
            username=data["username"],
            password=data["password"],
            real_name=data["real_name"],
            dept_biz_id=data["dept_biz_id"],
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            role_code=role_code
        ))
        oper_log(resp.biz_id, "用户管理", "注册", f"新用户 {data['username']} 注册成功，角色 {role_code}")
        return _success({"biz_id": resp.biz_id}, "注册成功")
    except Exception as e:
        return _error(f"注册失败：{e}")


@api_bp.route("/user/info", methods=["GET"])
@login_required
def user_info():
    """获取当前登录用户信息"""
    try:
        stub = _get_stub("user", user_pb2_grpc.UserServiceStub)
        resp = stub.GetUserByBizId(user_pb2.GetUserRequest(biz_id=_user_biz_id()))
        return _success({
            "biz_id": resp.user.biz_id,
            "username": resp.user.username,
            "real_name": resp.user.real_name,
            "dept_biz_id": resp.user.dept_biz_id,
            "phone": resp.user.phone,
            "email": resp.user.email,
            "user_status": resp.user.user_status
        })
    except Exception as e:
        return _error(f"获取用户信息失败：{e}")


@api_bp.route("/user/create", methods=["POST"])
@login_required
def create_user():
    """创建新用户"""
    data = request.json
    required = ["username", "password", "real_name", "dept_biz_id"]
    if not all(k in data for k in required):
        return _error("缺少必填参数")

    role_code = data.get("role_code", "teacher")
    if role_code not in ("teacher", "student"):
        return _error("角色类型无效")

    try:
        stub = _get_stub("user", user_pb2_grpc.UserServiceStub)
        resp = stub.CreateUser(user_pb2.CreateUserRequest(**{
            **data, "role_code": role_code
        }))
        oper_log(_user_biz_id(), "用户管理", "创建", f"创建用户 {data['username']}")
        return _success({"biz_id": resp.biz_id}, "用户创建成功")
    except Exception as e:
        return _error(f"创建用户失败：{e}")


@api_bp.route("/user/list", methods=["GET"])
@login_required
def list_user():
    """用户列表（按权限过滤）"""
    try:
        stub = _get_stub("user", user_pb2_grpc.UserServiceStub)
        resp = stub.ListUsersByRole(user_pb2.ListUsersByRoleRequest(
            viewer_role_code=_user_role()
        ))
        user_list = [{
            "biz_id": u.biz_id,
            "username": u.username,
            "real_name": u.real_name,
            "dept_biz_id": u.dept_biz_id,
            "phone": u.phone,
            "email": u.email,
            "user_status": u.user_status
        } for u in resp.list]
        return _success({"list": user_list, "total": resp.total})
    except Exception as e:
        return _error(f"查询用户列表失败：{e}")


@api_bp.route("/user/roles", methods=["GET"])
@login_required
def user_roles():
    """获取用户角色列表"""
    user_biz_id = request.args.get("user_biz_id", _user_biz_id())
    try:
        stub = _get_stub("user", user_pb2_grpc.UserServiceStub)
        resp = stub.GetUserRoles(user_pb2.GetUserRolesRequest(user_biz_id=user_biz_id))
        role_list = [{
            "biz_id": r.biz_id,
            "role_name": r.role_name,
            "role_code": r.role_code
        } for r in resp.list]
        return _success(role_list)
    except Exception as e:
        return _error(f"获取角色失败：{e}")


@api_bp.route("/user/permissions", methods=["GET"])
@login_required
def user_permissions():
    """获取当前用户的所有权限码列表"""
    try:
        user_biz_id = _user_biz_id()
        conn = sqlite3.connect(_DB_PATH)
        cur = conn.cursor()
        # 通过 user_role → role_permission → permission 三级关联
        cur.execute("""
            SELECT DISTINCT p.biz_id, p.perm_name, p.perm_url, p.perm_type, p.parent_biz_id
            FROM sys_role_permission rp
            JOIN sys_user_role ur ON ur.role_biz_id = rp.role_biz_id
            JOIN sys_permission p ON p.biz_id = rp.perm_biz_id AND p.is_delete = 0
            WHERE ur.user_biz_id = ?
        """, (user_biz_id,))
        rows = cur.fetchall()
        conn.close()

        perms = [{
            "biz_id": r[0],
            "perm_name": r[1],
            "perm_url": r[2],
            "perm_type": r[3],
            "parent_biz_id": r[4]
        } for r in rows]
        perm_ids = [r[0] for r in rows]

        # 还包括父级菜单权限（用于前端菜单显示）
        parent_ids = set()
        for r in rows:
            if r[4]:  # parent_biz_id
                parent_ids.add(r[4])
        all_perm_ids = list(set(perm_ids + list(parent_ids)))

        oper_log(user_biz_id, "权限管理", "查询", "查询用户权限列表")
        return _success({"perms": perms, "perm_ids": all_perm_ids})
    except Exception as e:
        return _error(f"查询权限失败：{e}")


@api_bp.route("/user/role/promote", methods=["POST"])
@login_required
def promote_user_role():
    """提升/变更用户角色"""
    data = request.json
    if not data.get("target_biz_id") or not data.get("new_role_code"):
        return _error("缺少必填参数")

    # 防止越权提升
    allowed = {"teacher": ["teacher"], "dept_admin": ["teacher", "student"],
               "school_admin": ["dept_admin", "teacher", "student", "repair_worker"]}
    viewer_role = _user_role()
    new_role = data["new_role_code"]
    if new_role not in allowed.get(viewer_role, []):
        return _error("无权设置该角色")

    try:
        stub = _get_stub("user", user_pb2_grpc.UserServiceStub)
        resp = stub.PromoteUserRole(user_pb2.PromoteRoleRequest(
            target_biz_id=data["target_biz_id"],
            new_role_code=new_role,
            operator_biz_id=_user_biz_id()
        ))
        if resp.success:
            oper_log(_user_biz_id(), "用户管理", "角色变更",
                     f"将用户 {data['target_biz_id']} 角色变更为 {new_role}")
            return _success(msg=resp.msg)
        return _error(resp.msg)
    except Exception as e:
        return _error(f"角色变更失败：{e}")


@api_bp.route("/user/update", methods=["POST"])
@login_required
def update_user():
    """编辑用户信息"""
    data = request.json
    if not data.get("biz_id"):
        return _error("用户ID不能为空")

    try:
        stub = _get_stub("user", user_pb2_grpc.UserServiceStub)
        resp = stub.UpdateUser(user_pb2.UpdateUserRequest(
            biz_id=data["biz_id"],
            real_name=data.get("real_name", ""),
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            dept_biz_id=data.get("dept_biz_id", ""),
            user_status=data.get("user_status", 0),
            editor_role_code=_user_role(),
            editor_biz_id=_user_biz_id()
        ))
        if resp.success:
            oper_log(_user_biz_id(), "用户管理", "编辑", f"编辑用户 {data['biz_id']}")
            return _success(msg=resp.msg)
        return _error(resp.msg)
    except Exception as e:
        return _error(f"更新用户失败：{e}")


# ==================== 2. 部门管理模块 ====================
@api_bp.route("/dept/public-list", methods=["GET"])
def dept_public_list():
    """获取部门列表（公开接口）"""
    try:
        stub = _get_stub("user", user_pb2_grpc.DeptServiceStub)
        resp = stub.GetDeptTree(user_pb2.GetDeptTreeRequest())
        def flatten(nodes):
            result = []
            for node in nodes:
                result.append({"biz_id": node.biz_id, "dept_name": node.dept_name})
                if node.children:
                    result.extend(flatten(node.children))
            return result
        dept_list = flatten(resp.list)
        return _success(dept_list)
    except Exception as e:
        return _error(f"获取部门列表失败：{e}")


@api_bp.route("/dept/tree", methods=["GET"])
@login_required
def dept_tree():
    """获取部门树"""
    try:
        stub = _get_stub("user", user_pb2_grpc.DeptServiceStub)
        resp = stub.GetDeptTree(user_pb2.GetDeptTreeRequest())
        return _success(_pb_list_to_list(resp.list))
    except Exception as e:
        return _error(f"获取部门树失败：{e}")


@api_bp.route("/dept/create", methods=["POST"])
@login_required
def create_dept():
    """新增部门"""
    data = request.json
    if not data.get("dept_name"):
        return _error("部门名称不能为空")
    try:
        stub = _get_stub("user", user_pb2_grpc.DeptServiceStub)
        resp = stub.CreateDept(user_pb2.CreateDeptRequest(**data))
        oper_log(_user_biz_id(), "部门管理", "新增", f"创建部门 {data['dept_name']}")
        return _success({"biz_id": resp.biz_id}, "部门创建成功")
    except Exception as e:
        return _error(f"创建部门失败：{e}")


@api_bp.route("/dept/update", methods=["POST"])
@login_required
def update_dept():
    """更新部门"""
    data = request.json
    if not data.get("biz_id"):
        return _error("部门ID不能为空")
    try:
        stub = _get_stub("user", user_pb2_grpc.DeptServiceStub)
        resp = stub.UpdateDept(user_pb2.UpdateDeptRequest(**data))
        if resp.success:
            oper_log(_user_biz_id(), "部门管理", "编辑", f"编辑部门 {data['biz_id']}")
            return _success(msg=resp.msg)
        return _error(resp.msg)
    except Exception as e:
        return _error(f"更新部门失败：{e}")


@api_bp.route("/dept/delete", methods=["DELETE"])
@login_required
def delete_dept():
    """删除部门"""
    biz_id = request.args.get("biz_id", "")
    if not biz_id:
        return _error("部门ID不能为空")
    try:
        stub = _get_stub("user", user_pb2_grpc.DeptServiceStub)
        resp = stub.DeleteDept(user_pb2.DeleteDeptRequest(biz_id=biz_id))
        if resp.success:
            oper_log(_user_biz_id(), "部门管理", "删除", f"删除部门 {biz_id}")
            return _success(msg=resp.msg)
        return _error(resp.msg)
    except Exception as e:
        return _error(f"删除部门失败：{e}")


# ==================== 3. 字典管理模块 ====================
@api_bp.route("/dict/types", methods=["GET"])
@login_required
def dict_types():
    """获取所有字典分类"""
    try:
        stub = _get_stub("user", user_pb2_grpc.DictServiceStub)
        resp = stub.ListDictTypes(user_pb2.GetDictTypesRequest())
        return _success(list(resp.dict_types))
    except Exception as e:
        return _error(f"查询字典分类失败：{e}")


@api_bp.route("/dict/list", methods=["GET"])
@login_required
def dict_list():
    """按类型查询字典列表"""
    dict_type = request.args.get("dict_type", "")
    if not dict_type:
        return _error("字典类型不能为空")
    try:
        stub = _get_stub("user", user_pb2_grpc.DictServiceStub)
        resp = stub.ListDictByType(user_pb2.ListDictRequest(dict_type=dict_type))
        dict_list = [{
            "biz_id": d.biz_id,
            "dict_code": d.dict_code,
            "dict_name": d.dict_name,
            "sort": d.sort
        } for d in resp.list]
        return _success({"list": dict_list, "total": resp.total})
    except Exception as e:
        return _error(f"查询字典失败：{e}")


@api_bp.route("/dict/create", methods=["POST"])
@login_required
def create_dict():
    """新增字典项"""
    data = request.json
    required = ["dict_type", "dict_code", "dict_name"]
    if not all(k in data for k in required):
        return _error("缺少必填参数")
    try:
        stub = _get_stub("user", user_pb2_grpc.DictServiceStub)
        resp = stub.CreateDict(user_pb2.CreateDictRequest(**data))
        oper_log(_user_biz_id(), "字典管理", "新增", f"新增字典 {data['dict_name']}")
        return _success({"biz_id": resp.biz_id}, "字典创建成功")
    except Exception as e:
        return _error(f"创建字典失败：{e}")


@api_bp.route("/dict/update", methods=["POST"])
@login_required
def update_dict():
    """更新字典项"""
    data = request.json
    if not data.get("biz_id"):
        return _error("字典ID不能为空")
    try:
        stub = _get_stub("user", user_pb2_grpc.DictServiceStub)
        resp = stub.UpdateDict(user_pb2.UpdateDictRequest(**data))
        if resp.success:
            oper_log(_user_biz_id(), "字典管理", "编辑", f"编辑字典 {data['biz_id']}")
            return _success(msg=resp.msg)
        return _error(resp.msg)
    except Exception as e:
        return _error(f"更新字典失败：{e}")


@api_bp.route("/dict/delete", methods=["DELETE"])
@login_required
def delete_dict():
    """删除字典项"""
    biz_id = request.args.get("biz_id", "")
    if not biz_id:
        return _error("字典ID不能为空")
    try:
        stub = _get_stub("user", user_pb2_grpc.DictServiceStub)
        resp = stub.DeleteDict(user_pb2.DeleteDictRequest(biz_id=biz_id))
        if resp.success:
            oper_log(_user_biz_id(), "字典管理", "删除", f"删除字典 {biz_id}")
            return _success(msg=resp.msg)
        return _error(resp.msg)
    except Exception as e:
        return _error(f"删除字典失败：{e}")


# ==================== 4. 资产管理模块 ====================
@api_bp.route("/asset/create", methods=["POST"])
@login_required
def asset_create():
    """新增固定资产"""
    data = request.json
    required = ["asset_code", "asset_name", "asset_type_code", "buy_time",
                "asset_price", "store_location", "dept_biz_id", "current_status_code"]
    if not all(k in data for k in required):
        return _error("缺少必填参数")
    try:
        stub = _get_stub("asset", asset_pb2_grpc.AssetServiceStub)
        resp = stub.CreateAsset(asset_pb2.CreateAssetRequest(
            **data,
            create_user_biz_id=_user_biz_id()
        ))
        oper_log(_user_biz_id(), "资产管理", "新增",
                 f"新增资产 {data['asset_name']}（{data['asset_code']}）")
        return _success({"biz_id": resp.biz_id}, "资产录入成功")
    except Exception as e:
        return _error(f"资产创建失败：{e}")


@api_bp.route("/asset/detail", methods=["GET"])
@login_required
def asset_detail():
    """查询资产详情"""
    biz_id = request.args.get("biz_id", "")
    if not biz_id:
        return _error("资产ID不能为空")
    try:
        stub = _get_stub("asset", asset_pb2_grpc.AssetServiceStub)
        resp = stub.GetAssetByBizId(asset_pb2.GetAssetRequest(biz_id=biz_id))
        return _success({
            "biz_id": resp.asset.biz_id,
            "asset_code": resp.asset.asset_code,
            "asset_name": resp.asset.asset_name,
            "asset_type_code": resp.asset.asset_type_code,
            "buy_time": resp.asset.buy_time,
            "asset_price": resp.asset.asset_price,
            "store_location": resp.asset.store_location,
            "dept_biz_id": resp.asset.dept_biz_id,
            "current_status_code": resp.asset.current_status_code,
            "use_user_biz_id": resp.asset.use_user_biz_id,
            "supplier": resp.asset.supplier,
            "spec": resp.asset.spec,
            "remark": resp.asset.remark,
            "create_time": resp.asset.create_time
        })
    except Exception as e:
        return _error(f"查询资产失败：{e}")


@api_bp.route("/asset/list", methods=["GET"])
@login_required
def asset_list():
    """分页查询部门资产列表（school_admin不传dept_biz_id时查全量）"""
    dept_biz_id = request.args.get("dept_biz_id", "")
    status_code = request.args.get("status_code", "")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    
    # 校级管理员不传dept_biz_id时查看全校范围
    if not dept_biz_id and _user_role() != "school_admin":
        return _error("部门ID不能为空")
        
    try:
        stub = _get_stub("asset", asset_pb2_grpc.AssetServiceStub)
        resp = stub.ListAssetByDept(asset_pb2.ListAssetRequest(
            dept_biz_id=dept_biz_id,
            status_code=status_code,
            page=page,
            page_size=page_size
        ))
        asset_list = [{
            "biz_id": a.biz_id,
            "asset_code": a.asset_code,
            "asset_name": a.asset_name,
            "asset_type_code": a.asset_type_code,
            "asset_price": a.asset_price,
            "store_location": a.store_location,
            "current_status_code": a.current_status_code,
            "use_user_biz_id": a.use_user_biz_id
        } for a in resp.list]
        return _success({"list": asset_list, "total": resp.total})
    except Exception as e:
        return _error(f"查询资产列表失败：{e}")


@api_bp.route("/asset/status", methods=["POST"])
@login_required
def update_asset_status():
    """更新资产状态"""
    data = request.json
    required = ["asset_biz_id", "new_status_code", "oper_desc"]
    if not all(k in data for k in required):
        return _error("缺少必填参数")
    try:
        stub = _get_stub("asset", asset_pb2_grpc.AssetServiceStub)
        resp = stub.UpdateAssetStatus(asset_pb2.UpdateStatusRequest(
            asset_biz_id=data["asset_biz_id"],
            new_status_code=data["new_status_code"],
            oper_user_biz_id=_user_biz_id(),
            oper_desc=data["oper_desc"]
        ))
        if resp.success:
            oper_log(_user_biz_id(), "资产管理", "状态变更",
                     f"资产 {data['asset_biz_id']} → {data['new_status_code']}")
            return _success(msg=resp.msg)
        return _error(resp.msg)
    except Exception as e:
        return _error(f"状态更新失败：{e}")


@api_bp.route("/asset/status_log", methods=["GET"])
@login_required
def asset_status_log():
    """查询资产状态变更流水"""
    asset_biz_id = request.args.get("asset_biz_id", "")
    if not asset_biz_id:
        return _error("资产ID不能为空")
    try:
        stub = _get_stub("asset", asset_pb2_grpc.AssetServiceStub)
        resp = stub.GetStatusLogList(asset_pb2.GetStatusLogRequest(asset_biz_id=asset_biz_id))
        log_list = [{
            "old_status_code": l.old_status_code,
            "new_status_code": l.new_status_code,
            "oper_user_biz_id": l.oper_user_biz_id,
            "oper_desc": l.oper_desc,
            "create_time": l.create_time
        } for l in resp.list]
        return _success({"list": log_list, "total": resp.total})
    except Exception as e:
        return _error(f"查询状态日志失败：{e}")


# ==================== 5. 流程审批模块 ====================
@api_bp.route("/flow/borrow", methods=["POST"])
@login_required
def create_borrow():
    """提交领用申请"""
    data = request.json
    required = ["asset_biz_id", "borrow_start_time", "borrow_desc"]
    if not all(k in data for k in required):
        return _error("缺少必填参数")
    try:
        stub = _get_stub("flow", flow_pb2_grpc.FlowServiceStub)
        resp = stub.CreateBorrow(flow_pb2.CreateBorrowRequest(
            **data,
            borrow_user_biz_id=_user_biz_id()
        ))
        oper_log(_user_biz_id(), "流程审批", "领用申请",
                 f"申请领用资产 {data['asset_biz_id']}")
        return _success({
            "flow_biz_id": resp.flow_biz_id,
            "business_biz_id": resp.business_biz_id
        }, "领用申请提交成功")
    except Exception as e:
        return _error(f"提交申请失败：{e}")


@api_bp.route("/flow/repair", methods=["POST"])
@login_required
def create_repair():
    """提交报修申请"""
    data = request.json
    required = ["asset_biz_id", "fault_desc"]
    if not all(k in data for k in required):
        return _error("缺少必填参数")
    try:
        stub = _get_stub("flow", flow_pb2_grpc.FlowServiceStub)
        resp = stub.CreateRepair(flow_pb2.CreateRepairRequest(
            **data,
            report_user_biz_id=_user_biz_id()
        ))
        oper_log(_user_biz_id(), "流程审批", "报修申请",
                 f"报修资产 {data['asset_biz_id']}")
        return _success({
            "flow_biz_id": resp.flow_biz_id,
            "business_biz_id": resp.business_biz_id
        }, "报修工单提交成功")
    except Exception as e:
        return _error(f"提交报修失败：{e}")


@api_bp.route("/flow/scrap", methods=["POST"])
@login_required
def create_scrap():
    """提交报废申请"""
    data = request.json
    required = ["asset_biz_id", "scrap_reason"]
    if not all(k in data for k in required):
        return _error("缺少必填参数")
    try:
        stub = _get_stub("flow", flow_pb2_grpc.FlowServiceStub)
        resp = stub.CreateScrap(flow_pb2.CreateScrapRequest(
            **data,
            apply_user_biz_id=_user_biz_id()
        ))
        oper_log(_user_biz_id(), "流程审批", "报废申请",
                 f"申请报废资产 {data['asset_biz_id']}")
        return _success({
            "flow_biz_id": resp.flow_biz_id,
            "business_biz_id": resp.business_biz_id
        }, "报废申请提交成功")
    except Exception as e:
        return _error(f"提交报废失败：{e}")


@api_bp.route("/flow/audit/dept", methods=["POST"])
@login_required
def dept_audit():
    """学院初审"""
    data = request.json
    required = ["flow_biz_id", "result"]
    if not all(k in data for k in required):
        return _error("缺少必填参数")
    try:
        stub = _get_stub("flow", flow_pb2_grpc.FlowServiceStub)
        resp = stub.DeptAudit(flow_pb2.DeptAuditRequest(
            flow_biz_id=data["flow_biz_id"],
            audit_user_biz_id=_user_biz_id(),
            result=data["result"]
        ))
        if resp.success:
            oper_log(_user_biz_id(), "流程审批", "学院初审",
                     f"流程 {data['flow_biz_id']} 初审 {data['result']}")
            return _success(msg=resp.msg)
        return _error(resp.msg)
    except Exception as e:
        return _error(f"审核失败：{e}")


@api_bp.route("/flow/audit/school", methods=["POST"])
@login_required
def school_audit():
    """校级复审"""
    data = request.json
    required = ["flow_biz_id", "result"]
    if not all(k in data for k in required):
        return _error("缺少必填参数")
    try:
        stub = _get_stub("flow", flow_pb2_grpc.FlowServiceStub)
        resp = stub.SchoolAudit(flow_pb2.SchoolAuditRequest(
            flow_biz_id=data["flow_biz_id"],
            audit_user_biz_id=_user_biz_id(),
            result=data["result"]
        ))
        if resp.success:
            oper_log(_user_biz_id(), "流程审批", "校级复审",
                     f"流程 {data['flow_biz_id']} 复审 {data['result']}")
            return _success(msg=resp.msg)
        return _error(resp.msg)
    except Exception as e:
        return _error(f"审核失败：{e}")


@api_bp.route("/flow/return", methods=["POST"])
@login_required
def return_asset():
    """资产归还"""
    data = request.json
    if not data.get("borrow_biz_id"):
        return _error("领用单ID不能为空")
    try:
        stub = _get_stub("flow", flow_pb2_grpc.FlowServiceStub)
        resp = stub.ReturnAsset(flow_pb2.ReturnRequest(
            borrow_biz_id=data["borrow_biz_id"],
            oper_user_biz_id=_user_biz_id()
        ))
        if resp.success:
            oper_log(_user_biz_id(), "流程审批", "资产归还",
                     f"归还领用单 {data['borrow_biz_id']}")
            return _success(msg=resp.msg)
        return _error(resp.msg)
    except Exception as e:
        return _error(f"归还失败：{e}")


# ==================== 报修派单/接单/完工 ====================
_flow_logic = FlowLogic(_DB_PATH)


@api_bp.route("/flow/repair/dispatch", methods=["POST"])
@login_required
def repair_dispatch():
    """校级管理员派单"""
    data = request.json
    if not data.get("workorder_biz_id") or not data.get("repair_user_biz_id"):
        return _error("缺少必填参数")
    if _user_role() != "school_admin":
        return _error("仅校级管理员可派单")
    try:
        _flow_logic.dispatch_repair(data["workorder_biz_id"], data["repair_user_biz_id"], _user_biz_id())
        oper_log(_user_biz_id(), "报修流程", "派单",
                 f"工单 {data['workorder_biz_id']} -> {data['repair_user_biz_id']}")
        return _success(msg="派单成功")
    except Exception as e:
        return _error(f"派单失败：{e}")


@api_bp.route("/flow/repair/accept", methods=["POST"])
@login_required
def repair_accept():
    """修理工接单"""
    data = request.json
    if not data.get("workorder_biz_id"):
        return _error("工单ID不能为空")
    if _user_role() != "repair_worker":
        return _error("仅修理工可接单")
    try:
        _flow_logic.accept_repair(data["workorder_biz_id"], _user_biz_id())
        oper_log(_user_biz_id(), "报修流程", "接单", f"工单 {data['workorder_biz_id']}")
        return _success(msg="接单成功")
    except Exception as e:
        return _error(f"接单失败：{e}")


@api_bp.route("/flow/repair/complete", methods=["POST"])
@login_required
def repair_complete():
    """修理工完工"""
    data = request.json
    if not data.get("workorder_biz_id"):
        return _error("工单ID不能为空")
    if _user_role() != "repair_worker":
        return _error("仅修理工可完工")
    try:
        _flow_logic.complete_repair(
            data["workorder_biz_id"],
            _user_biz_id(),
            data.get("repair_cost", 0),
            data.get("repair_result", "")
        )
        oper_log(_user_biz_id(), "报修流程", "完工",
                 f"工单 {data['workorder_biz_id']} 费用 {data.get('repair_cost', 0)}")
        return _success(msg="完工")
    except Exception as e:
        return _error(f"完工失败：{e}")


@api_bp.route("/flow/repair/workers", methods=["GET"])
@login_required
def repair_workers():
    """获取修理工列表（供派单选择）"""
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT u.biz_id, u.real_name, u.username, u.phone, u.dept_biz_id,
                   d.dept_name
            FROM sys_user u
            JOIN sys_user_role ur ON u.biz_id = ur.user_biz_id
            JOIN sys_role r ON ur.role_biz_id = r.biz_id AND r.role_code = 'repair_worker'
            LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
            WHERE u.is_delete = 0
        """).fetchall()
        conn.close()
        workers = [dict(r) for r in rows]
        return _success({"list": workers, "total": len(workers)})
    except Exception as e:
        return _error(f"查询修理工列表失败：{e}")


@api_bp.route("/flow/repair/my-tasks", methods=["GET"])
@login_required
def my_repair_tasks():
    """修理工我的工单"""
    if _user_role() != "repair_worker":
        return _error("仅修理工可查看工单")
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT r.biz_id, r.asset_biz_id, r.report_user_biz_id, r.fault_desc,
                   r.order_status, r.flow_biz_id, r.repair_user_biz_id, r.repair_cost,
                   r.repair_result, r.report_time, r.finish_time, r.create_time,
                   u.real_name AS user_name,
                   d.dept_name AS dept_name,
                   a.asset_name, a.asset_type_code
            FROM fams_repair_workorder r
            LEFT JOIN fams_asset a ON r.asset_biz_id = a.biz_id
            LEFT JOIN sys_user u ON r.report_user_biz_id = u.biz_id
            LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
            WHERE r.repair_user_biz_id = ? AND r.order_status IN ('ASSIGNED', 'REPAIRING', 'COMPLETED')
              AND r.is_delete = 0
            ORDER BY r.create_time DESC
        """, (_user_biz_id(),)).fetchall()
        conn.close()
        tasks = [dict(r) for r in rows]
        return _success({"list": tasks, "total": len(tasks)})
    except Exception as e:
        return _error(f"查询工单失败：{e}")


@api_bp.route("/flow/borrow/list", methods=["GET"])
@login_required
def borrow_list():
    """我的领用列表"""
    dept_biz_id = request.args.get("dept_biz_id", "")
    user_biz_id = _user_biz_id()
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # 新增：scope参数，school_admin可传"department_all"查看全校范围
        scope = request.args.get("scope", "")
        is_school_admin = _user_role() == "school_admin"
        
        if dept_biz_id:
            # 部门管理员查看本部门所有记录
            rows = conn.execute("""
                SELECT b.biz_id, b.asset_biz_id, b.borrow_user_biz_id, b.borrow_start_time,
                       b.borrow_end_time, b.borrow_status, b.flow_biz_id, b.actual_return_time, b.borrow_desc,
                       b.create_time,
                       u.real_name AS user_name, u.dept_biz_id AS user_dept_biz_id,
                       d.dept_name AS dept_name,
                       a.asset_name, a.asset_type_code
                FROM fams_asset_borrow b
                LEFT JOIN fams_asset a ON b.asset_biz_id = a.biz_id
                LEFT JOIN sys_user u ON b.borrow_user_biz_id = u.biz_id
                LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
                WHERE a.dept_biz_id = ? AND b.is_delete = 0
                ORDER BY b.create_time DESC
            """, (dept_biz_id,)).fetchall()
        elif is_school_admin and scope == "department_all":
            # 校级管理员查看全校范围
            rows = conn.execute("""
                SELECT b.biz_id, b.asset_biz_id, b.borrow_user_biz_id, b.borrow_start_time,
                       b.borrow_end_time, b.borrow_status, b.flow_biz_id, b.actual_return_time, b.borrow_desc,
                       b.create_time,
                       u.real_name AS user_name, u.dept_biz_id AS user_dept_biz_id,
                       d.dept_name AS dept_name,
                       a.asset_name, a.asset_type_code
                FROM fams_asset_borrow b
                LEFT JOIN fams_asset a ON b.asset_biz_id = a.biz_id
                LEFT JOIN sys_user u ON b.borrow_user_biz_id = u.biz_id
                LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
                WHERE b.is_delete = 0
                ORDER BY b.create_time DESC
            """).fetchall()
        elif is_school_admin:
            # 校级管理员默认查看自己所在部门（与部门管理员相同）
            user = _get_current_user()
            user_dept = user.get("dept_biz_id") if user else ""
            if user_dept:
                rows = conn.execute("""
                    SELECT b.biz_id, b.asset_biz_id, b.borrow_user_biz_id, b.borrow_start_time,
                           b.borrow_end_time, b.borrow_status, b.flow_biz_id, b.actual_return_time, b.borrow_desc,
                           b.create_time,
                           u.real_name AS user_name, u.dept_biz_id AS user_dept_biz_id,
                           d.dept_name AS dept_name,
                           a.asset_name, a.asset_type_code
                    FROM fams_asset_borrow b
                    LEFT JOIN fams_asset a ON b.asset_biz_id = a.biz_id
                    LEFT JOIN sys_user u ON b.borrow_user_biz_id = u.biz_id
                    LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
                    WHERE a.dept_biz_id = ? AND b.is_delete = 0
                    ORDER BY b.create_time DESC
                """, (user_dept,)).fetchall()
            else:
                rows = []
        else:
            # 普通用户只查看自己的记录
            rows = conn.execute("""
                SELECT b.biz_id, b.asset_biz_id, b.borrow_user_biz_id, b.borrow_start_time,
                       b.borrow_end_time, b.borrow_status, b.flow_biz_id, b.actual_return_time, b.borrow_desc,
                       b.create_time,
                       u.real_name AS user_name,
                       d.dept_name AS dept_name,
                       a.asset_name, a.asset_type_code
                FROM fams_asset_borrow b
                LEFT JOIN fams_asset a ON b.asset_biz_id = a.biz_id
                LEFT JOIN sys_user u ON b.borrow_user_biz_id = u.biz_id
                LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
                WHERE b.borrow_user_biz_id = ? AND b.is_delete = 0
                ORDER BY b.create_time DESC
            """, (user_biz_id,)).fetchall()
        conn.close()
        borrow_list = [dict(r) for r in rows]
        return _success({"list": borrow_list, "total": len(borrow_list)})
    except Exception as e:
        return _error(f"查询领用列表失败：{e}")


@api_bp.route("/flow/repair/list", methods=["GET"])
@login_required
def repair_list():
    """我的报修列表"""
    dept_biz_id = request.args.get("dept_biz_id", "")
    user_biz_id = _user_biz_id()
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # 新增：scope参数，school_admin可传"department_all"查看全校范围
        scope = request.args.get("scope", "")
        is_school_admin = _user_role() == "school_admin"
        
        if dept_biz_id:
            # 部门管理员查看本部门所有记录
            rows = conn.execute("""
                SELECT r.biz_id, r.asset_biz_id, r.report_user_biz_id, r.fault_desc,
                       r.order_status, r.flow_biz_id, r.repair_user_biz_id, r.repair_cost,
                       r.repair_result, r.report_time, r.finish_time, r.create_time,
                       u.real_name AS user_name, u.dept_biz_id AS user_dept_biz_id,
                       d.dept_name AS dept_name,
                       a.asset_name, a.asset_type_code
                FROM fams_repair_workorder r
                LEFT JOIN fams_asset a ON r.asset_biz_id = a.biz_id
                LEFT JOIN sys_user u ON r.report_user_biz_id = u.biz_id
                LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
                WHERE a.dept_biz_id = ? AND r.is_delete = 0
                ORDER BY r.create_time DESC
            """, (dept_biz_id,)).fetchall()
        elif is_school_admin and scope == "department_all":
            # 校级管理员查看全校范围
            rows = conn.execute("""
                SELECT r.biz_id, r.asset_biz_id, r.report_user_biz_id, r.fault_desc,
                       r.order_status, r.flow_biz_id, r.repair_user_biz_id, r.repair_cost,
                       r.repair_result, r.report_time, r.finish_time, r.create_time,
                       u.real_name AS user_name, u.dept_biz_id AS user_dept_biz_id,
                       d.dept_name AS dept_name,
                       a.asset_name, a.asset_type_code
                FROM fams_repair_workorder r
                LEFT JOIN fams_asset a ON r.asset_biz_id = a.biz_id
                LEFT JOIN sys_user u ON r.report_user_biz_id = u.biz_id
                LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
                WHERE r.is_delete = 0
                ORDER BY r.create_time DESC
            """).fetchall()
        elif is_school_admin:
            # 校级管理员默认查看自己所在部门（与部门管理员相同）
            user = _get_current_user()
            user_dept = user.get("dept_biz_id") if user else ""
            if user_dept:
                rows = conn.execute("""
                    SELECT r.biz_id, r.asset_biz_id, r.report_user_biz_id, r.fault_desc,
                           r.order_status, r.flow_biz_id, r.repair_user_biz_id, r.repair_cost,
                           r.repair_result, r.report_time, r.finish_time, r.create_time,
                           u.real_name AS user_name, u.dept_biz_id AS user_dept_biz_id,
                           d.dept_name AS dept_name,
                           a.asset_name, a.asset_type_code
                    FROM fams_repair_workorder r
                    LEFT JOIN fams_asset a ON r.asset_biz_id = a.biz_id
                    LEFT JOIN sys_user u ON r.report_user_biz_id = u.biz_id
                    LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
                    WHERE a.dept_biz_id = ? AND r.is_delete = 0
                    ORDER BY r.create_time DESC
                """, (user_dept,)).fetchall()
            else:
                rows = []
        else:
            # 普通用户只查看自己的记录
            rows = conn.execute("""
                SELECT r.biz_id, r.asset_biz_id, r.report_user_biz_id, r.fault_desc,
                       r.order_status, r.flow_biz_id, r.repair_user_biz_id, r.repair_cost,
                       r.repair_result, r.report_time, r.finish_time, r.create_time,
                       u.real_name AS user_name,
                       d.dept_name AS dept_name,
                       a.asset_name, a.asset_type_code
                FROM fams_repair_workorder r
                LEFT JOIN fams_asset a ON r.asset_biz_id = a.biz_id
                LEFT JOIN sys_user u ON r.report_user_biz_id = u.biz_id
                LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
                WHERE r.report_user_biz_id = ? AND r.is_delete = 0
                ORDER BY r.create_time DESC
            """, (user_biz_id,)).fetchall()
        conn.close()
        repair_list = [dict(r) for r in rows]
        return _success({"list": repair_list, "total": len(repair_list)})
    except Exception as e:
        return _error(f"查询报修列表失败：{e}")


@api_bp.route("/flow/scrap/list", methods=["GET"])
@login_required
def scrap_list():
    """我的报废列表"""
    dept_biz_id = request.args.get("dept_biz_id", "")
    user_biz_id = _user_biz_id()
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # 新增：scope参数，school_admin可传"department_all"查看全校范围
        scope = request.args.get("scope", "")
        is_school_admin = _user_role() == "school_admin"
        
        if dept_biz_id:
            # 部门管理员查看本部门所有记录
            rows = conn.execute("""
                SELECT s.biz_id, s.asset_biz_id, s.apply_user_biz_id, s.scrap_reason,
                       s.scrap_status, s.flow_biz_id, s.create_time,
                       u.real_name AS user_name, u.dept_biz_id AS user_dept_biz_id,
                       d.dept_name AS dept_name,
                       a.asset_name, a.asset_type_code
                FROM fams_asset_scrap s
                LEFT JOIN fams_asset a ON s.asset_biz_id = a.biz_id
                LEFT JOIN sys_user u ON s.apply_user_biz_id = u.biz_id
                LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
                WHERE a.dept_biz_id = ? AND s.is_delete = 0
                ORDER BY s.create_time DESC
            """, (dept_biz_id,)).fetchall()
        elif is_school_admin and scope == "department_all":
            # 校级管理员查看全校范围
            rows = conn.execute("""
                SELECT s.biz_id, s.asset_biz_id, s.apply_user_biz_id, s.scrap_reason,
                       s.scrap_status, s.flow_biz_id, s.create_time,
                       u.real_name AS user_name, u.dept_biz_id AS user_dept_biz_id,
                       d.dept_name AS dept_name,
                       a.asset_name, a.asset_type_code
                FROM fams_asset_scrap s
                LEFT JOIN fams_asset a ON s.asset_biz_id = a.biz_id
                LEFT JOIN sys_user u ON s.apply_user_biz_id = u.biz_id
                LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
                WHERE s.is_delete = 0
                ORDER BY s.create_time DESC
            """).fetchall()
        elif is_school_admin:
            # 校级管理员默认查看自己所在部门（与部门管理员相同）
            user = _get_current_user()
            user_dept = user.get("dept_biz_id") if user else ""
            if user_dept:
                rows = conn.execute("""
                    SELECT s.biz_id, s.asset_biz_id, s.apply_user_biz_id, s.scrap_reason,
                           s.scrap_status, s.flow_biz_id, s.create_time,
                           u.real_name AS user_name, u.dept_biz_id AS user_dept_biz_id,
                           d.dept_name AS dept_name,
                           a.asset_name, a.asset_type_code
                    FROM fams_asset_scrap s
                    LEFT JOIN fams_asset a ON s.asset_biz_id = a.biz_id
                    LEFT JOIN sys_user u ON s.apply_user_biz_id = u.biz_id
                    LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
                    WHERE a.dept_biz_id = ? AND s.is_delete = 0
                    ORDER BY s.create_time DESC
                """, (user_dept,)).fetchall()
            else:
                rows = []
        else:
            # 普通用户只查看自己的记录
            rows = conn.execute("""
                SELECT s.biz_id, s.asset_biz_id, s.apply_user_biz_id, s.scrap_reason,
                       s.scrap_status, s.flow_biz_id, s.create_time,
                       u.real_name AS user_name,
                       d.dept_name AS dept_name,
                       a.asset_name, a.asset_type_code
                FROM fams_asset_scrap s
                LEFT JOIN fams_asset a ON s.asset_biz_id = a.biz_id
                LEFT JOIN sys_user u ON s.apply_user_biz_id = u.biz_id
                LEFT JOIN sys_department d ON u.dept_biz_id = d.biz_id
                WHERE s.apply_user_biz_id = ? AND s.is_delete = 0
                ORDER BY s.create_time DESC
            """, (user_biz_id,)).fetchall()
        conn.close()
        scrap_list = [dict(r) for r in rows]
        return _success({"list": scrap_list, "total": len(scrap_list)})
    except Exception as e:
        return _error(f"查询报废列表失败：{e}")


@api_bp.route("/flow/progress", methods=["GET"])
@login_required
def flow_progress():
    """查询审批进度"""
    flow_biz_id = request.args.get("flow_biz_id", "")
    if not flow_biz_id:
        return _error("审批流ID不能为空")
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT f.dept_audit_result, f.dept_audit_user_biz_id, f.dept_audit_time,
                   f.school_audit_result, f.school_audit_user_biz_id, f.school_audit_time, f.final_result,
                   du.real_name AS dept_audit_user_name,
                   su.real_name AS school_audit_user_name
            FROM fams_audit_flow f
            LEFT JOIN sys_user du ON f.dept_audit_user_biz_id = du.biz_id
            LEFT JOIN sys_user su ON f.school_audit_user_biz_id = su.biz_id
            WHERE f.biz_id = ?""", (flow_biz_id,)).fetchone()
        conn.close()
        if not row:
            return _error("审批单不存在", 404)
        steps = []
        if row["dept_audit_result"]:
            steps.append({
                "step_name": "学院初审",
                "auditor_user_biz_id": row["dept_audit_user_biz_id"] or "",
                "auditor_user_name": row["dept_audit_user_name"] or "",
                "result": row["dept_audit_result"],
                "audit_time": row["dept_audit_time"] or ""
            })
        if row["school_audit_result"]:
            steps.append({
                "step_name": "校级复审",
                "auditor_user_biz_id": row["school_audit_user_biz_id"] or "",
                "auditor_user_name": row["school_audit_user_name"] or "",
                "result": row["school_audit_result"],
                "audit_time": row["school_audit_time"] or ""
            })
        return _success({"steps": steps, "final_result": row["final_result"] or ""})
    except Exception as e:
        return _error(f"查询审批进度失败：{e}")


# ==================== 6. 多人协同盘点模块 ====================
@api_bp.route("/check/task/create", methods=["POST"])
@login_required
def create_check_task():
    """创建盘点任务"""
    data = request.json
    required = ["task_name", "target_dept_biz_id", "start_time", "end_time"]
    if not all(k in data for k in required):
        return _error("缺少必填参数")
    try:
        stub = _get_stub("asset", asset_pb2_grpc.AssetServiceStub)
        resp = stub.CreateCheckTask(asset_pb2.CreateTaskRequest(
            **data,
            create_user_biz_id=_user_biz_id()
        ))
        oper_log(_user_biz_id(), "盘点管理", "创建任务",
                 f"创建盘点任务 {data['task_name']}")
        return _success({"task_biz_id": resp.task_biz_id}, "盘点任务创建成功")
    except Exception as e:
        return _error(f"创建任务失败：{e}")


@api_bp.route("/check/task/list", methods=["GET"])
@login_required
def check_task_list():
    """盘点任务列表"""
    dept_biz_id = request.args.get("dept_biz_id", "")
    if not dept_biz_id:
        return _error("部门ID不能为空")
    try:
        stub = _get_stub("asset", asset_pb2_grpc.AssetServiceStub)
        resp = stub.ListCheckTask(asset_pb2.ListTaskRequest(dept_biz_id=dept_biz_id))
        task_list = [{
            "biz_id": t.biz_id,
            "task_name": t.task_name,
            "target_dept_biz_id": t.target_dept_biz_id,
            "start_time": t.start_time,
            "end_time": t.end_time,
            "task_status": t.task_status,
            "create_user_biz_id": t.create_user_biz_id
        } for t in resp.list]
        return _success({"list": task_list, "total": resp.total})
    except Exception as e:
        return _error(f"查询任务列表失败：{e}")


@api_bp.route("/check/detail/submit", methods=["POST"])
@login_required
def submit_check_detail():
    """提交盘点明细"""
    data = request.json
    required = ["task_biz_id", "asset_biz_id", "actual_exist"]
    if not all(k in data for k in required):
        return _error("缺少必填参数")
    try:
        stub = _get_stub("asset", asset_pb2_grpc.AssetServiceStub)
        resp = stub.SubmitCheckDetail(asset_pb2.SubmitDetailRequest(
            **data,
            check_user_biz_id=_user_biz_id()
        ))
        if resp.success:
            oper_log(_user_biz_id(), "盘点管理", "提交盘点",
                     f"进度 {data['task_biz_id']}/{data['asset_biz_id']}")
            return _success(msg=resp.msg)
        return _error(resp.msg)
    except Exception as e:
        return _error(f"提交盘点失败：{e}")


@api_bp.route("/check/detail/list", methods=["GET"])
@login_required
def check_detail_list():
    """盘点明细列表"""
    task_biz_id = request.args.get("task_biz_id", "")
    if not task_biz_id:
        return _error("任务ID不能为空")
    try:
        stub = _get_stub("asset", asset_pb2_grpc.AssetServiceStub)
        resp = stub.GetCheckDetailList(asset_pb2.GetCheckDetailRequest(task_biz_id=task_biz_id))
        detail_list = [{
            "asset_biz_id": d.asset_biz_id,
            "check_user_biz_id": d.check_user_biz_id,
            "actual_exist": d.actual_exist,
            "real_location": d.real_location,
            "check_remark": d.check_remark,
            "check_time": d.check_time
        } for d in resp.list]
        return _success({"list": detail_list, "total": resp.total})
    except Exception as e:
        return _error(f"查询明细失败：{e}")


# ==================== 7. 文件附件模块 ====================
@api_bp.route("/storage/upload", methods=["POST"])
@login_required
def upload_attach():
    """上传资产附件"""
    asset_biz_id = request.form.get("asset_biz_id", "")
    attach_type = int(request.form.get("attach_type", 2))
    if not asset_biz_id:
        return _error("资产ID不能为空")
    if "file" not in request.files:
        return _error("请选择上传文件")
    file = request.files["file"]
    file_data = file.read()
    attach_name = file.filename
    try:
        stub = _get_stub("storage", storage_pb2_grpc.StorageServiceStub)
        resp = stub.UploadAttach(storage_pb2.UploadRequest(
            asset_biz_id=asset_biz_id,
            attach_name=attach_name,
            file_data=file_data,
            attach_type=attach_type,
            upload_user_biz_id=_user_biz_id()
        ))
        oper_log(_user_biz_id(), "文件管理", "上传", f"上传附件 {attach_name}")
        return _success({
            "attach_biz_id": resp.attach_biz_id,
            "file_path": resp.file_path
        }, "上传成功")
    except Exception as e:
        return _error(f"上传失败：{e}")


@api_bp.route("/storage/list", methods=["GET"])
@login_required
def attach_list():
    """资产附件列表"""
    asset_biz_id = request.args.get("asset_biz_id", "")
    if not asset_biz_id:
        return _error("资产ID不能为空")
    try:
        stub = _get_stub("storage", storage_pb2_grpc.StorageServiceStub)
        resp = stub.GetAttachList(storage_pb2.GetListRequest(asset_biz_id=asset_biz_id))
        attach_list = [{
            "biz_id": a.biz_id,
            "asset_biz_id": a.asset_biz_id,
            "attach_name": a.attach_name,
            "attach_path": a.attach_path,
            "attach_type": a.attach_type,
            "file_size": a.file_size,
            "create_time": a.create_time
        } for a in resp.list]
        return _success({"list": attach_list, "total": resp.total})
    except Exception as e:
        return _error(f"查询附件失败：{e}")


@api_bp.route("/storage/delete", methods=["DELETE"])
@login_required
def delete_attach():
    """删除附件"""
    attach_biz_id = request.args.get("attach_biz_id", "")
    if not attach_biz_id:
        return _error("附件ID不能为空")
    try:
        stub = _get_stub("storage", storage_pb2_grpc.StorageServiceStub)
        resp = stub.DeleteAttach(storage_pb2.DeleteRequest(attach_biz_id=attach_biz_id))
        if resp.success:
            oper_log(_user_biz_id(), "文件管理", "删除", f"删除附件 {attach_biz_id}")
            return _success(msg=resp.msg)
        return _error(resp.msg)
    except Exception as e:
        return _error(f"删除失败：{e}")


@api_bp.route("/storage/download", methods=["GET"])
@login_required
def download_attach():
    """下载附件"""
    attach_biz_id = request.args.get("attach_biz_id", "")
    if not attach_biz_id:
        return _error("附件ID不能为空")
    try:
        stub = _get_stub("storage", storage_pb2_grpc.StorageServiceStub)
        resp = stub.GetDownloadUrl(storage_pb2.GetUrlRequest(attach_biz_id=attach_biz_id))
        file_path = resp.download_url
        with open(file_path, "rb") as f:
            file_data = f.read()
        oper_log(_user_biz_id(), "文件管理", "下载", f"下载附件 {attach_biz_id}")
        return send_file(
            io.BytesIO(file_data),
            download_name=attach_biz_id,
            as_attachment=True
        )
    except Exception as e:
        return _error(f"下载失败：{e}")
