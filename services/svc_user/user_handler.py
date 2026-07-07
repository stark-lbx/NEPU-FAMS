import grpc
import redis
import json
import jwt
import datetime
from proto.generated import user_pb2, user_pb2_grpc
from data.logic.user_logic import UserLogic
from data.logic.role_logic import RoleLogic
from common.utils import verify_password, safe_error_msg, get_role_level, ROLE_HIERARCHY
from common.mq import MqProducer
from common.config import QueueSettings
from common.constants import QUEUE_DELETE_CACHE_USER
from common.oper_log import oper_log

SECRET_KEY = "fams_secret_key_2024"


class UserServiceHandler(user_pb2_grpc.UserServiceServicer):
    def __init__(self, user_logic: UserLogic, role_logic: RoleLogic,
                 redis_client: redis.Redis, mq_producer: MqProducer = None):
        self.user_logic = user_logic
        self.role_logic = role_logic
        self.redis = redis_client
        self.mq_producer = mq_producer

    def Login(self, request, context):
        try:
            user = self.user_logic.login_verify(request.username, request.password)
            if not user:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("账号或密码错误")
                return user_pb2.LoginResponse()

            # 获取用户角色（取最高权限角色）
            roles = self.role_logic.get_user_roles(user["biz_id"])
            role_code = roles[0]["role_code"] if roles else "student"

            # 生成JWT Token（含角色信息）
            payload = {
                "user_biz_id": user["biz_id"],
                "username": user["username"],
                "role_code": role_code,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

            oper_log(user["biz_id"], "用户认证", "登录", f"用户 {user['username']} 登录成功")

            user_info = user_pb2.UserInfo(
                biz_id=user["biz_id"],
                username=user["username"],
                real_name=user["real_name"],
                dept_biz_id=user["dept_biz_id"],
                phone=user["phone"],
                email=user["email"],
                user_status=user["user_status"]
            )
            return user_pb2.LoginResponse(token=token, user=user_info)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return user_pb2.LoginResponse()

    def GetUserByBizId(self, request, context):
        try:
            cache_key = f"user:{request.biz_id}"
            cache = self.redis.get(cache_key)
            if cache:
                user = json.loads(cache)
            else:
                user = self.user_logic.get_user(request.biz_id)
                if user:
                    self.redis.setex(cache_key, 3600, json.dumps(user))

            if not user:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("用户不存在")
                return user_pb2.UserResponse()

            return user_pb2.UserResponse(user=user_pb2.UserInfo(
                **{k: user[k] for k in user_pb2.UserInfo.DESCRIPTOR.fields_by_name.keys() if k in user}))
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return user_pb2.UserResponse()

    def CreateUser(self, request, context):
        try:
            user_data = {
                "username": request.username,
                "password": request.password,
                "real_name": request.real_name,
                "dept_biz_id": request.dept_biz_id,
                "phone": request.phone,
                "email": request.email
            }
            role_code = request.role_code if request.role_code else "teacher"
            biz_id = self.user_logic.create_user(user_data, role_code)
            oper_log(biz_id, "用户管理", "注册", f"新用户 {request.username} 注册成功，角色 {role_code}")
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": "user:*"})
            return user_pb2.CreateUserResponse(biz_id=biz_id)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return user_pb2.CreateUserResponse()

    def ListUserByDept(self, request, context):
        try:
            users = self.user_logic.list_by_dept(request.dept_biz_id)
            user_list = [user_pb2.UserInfo(
                **{k: u[k] for k in user_pb2.UserInfo.DESCRIPTOR.fields_by_name.keys() if k in u}
            ) for u in users]
            return user_pb2.UserListResponse(list=user_list, total=len(users))
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return user_pb2.UserListResponse()

    def GetUserRoles(self, request, context):
        try:
            roles = self.role_logic.get_user_roles(request.user_biz_id)
            role_list = [user_pb2.RoleInfo(
                biz_id=r["biz_id"], role_name=r["role_name"], role_code=r["role_code"]
            ) for r in roles]
            return user_pb2.RoleListResponse(list=role_list)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return user_pb2.RoleListResponse()

    def ListUsersByRole(self, request, context):
        """按权限层级查询可见用户列表"""
        try:
            viewer_code = request.viewer_role_code
            if not viewer_code:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("缺少角色信息")
                return user_pb2.UserListResponse()

            viewer_level = get_role_level(viewer_code)
            if viewer_level <= 0:
                return user_pb2.UserListResponse(list=[], total=0)

            # 获取所有可见的角色code
            visible_codes = [code for code, level in ROLE_HIERARCHY.items() if level <= viewer_level]
            users = self.user_logic.list_users_by_permission(visible_codes)
            user_list = [user_pb2.UserInfo(
                **{k: u[k] for k in user_pb2.UserInfo.DESCRIPTOR.fields_by_name.keys() if k in u}
            ) for u in users]
            return user_pb2.UserListResponse(list=user_list, total=len(user_list))
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return user_pb2.UserListResponse()

    def PromoteUserRole(self, request, context):
        """提升/修改用户角色"""
        try:
            self.user_logic.promote_user_role(
                request.target_biz_id, request.new_role_code, request.operator_biz_id
            )
            oper_log(request.operator_biz_id, "用户管理", "角色变更",
                     f"将用户 {request.target_biz_id} 角色变更为 {request.new_role_code}")
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": "user:*"})
            return user_pb2.CommonResponse(success=True, msg="角色变更成功")
        except Exception as e:
            return user_pb2.CommonResponse(success=False, msg=safe_error_msg(e))

    def UpdateUser(self, request, context):
        """编辑用户信息（权限受控）"""
        try:
            update_data = {k: v for k, v in {
                "real_name": request.real_name,
                "phone": request.phone,
                "email": request.email,
                "dept_biz_id": request.dept_biz_id,
                "user_status": request.user_status
            }.items() if v}
            self.user_logic.update_user(request.biz_id, update_data, request.editor_role_code)
            oper_log(request.editor_biz_id, "用户管理", "编辑用户",
                     f"编辑用户 {request.biz_id}")
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": "user:*"})
            return user_pb2.CommonResponse(success=True, msg="更新成功")
        except Exception as e:
            return user_pb2.CommonResponse(success=False, msg=safe_error_msg(e))
