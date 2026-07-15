"""
用户认证、权限校验、部门管理 业务逻辑
不得出现任何SQL语句
"""
from typing import Any, Dict, List, Optional
import jwt
from datetime import datetime, timedelta
import bcrypt

from data.basic.user_dao import UserDAO, RoleDAO, DeptDAO, MenuDAO, OperLogDAO


class UserLogic:
    """用户业务逻辑"""

    def __init__(self, db_config: Dict, jwt_config: Dict):
        self.user_dao = UserDAO(db_config)
        self.role_dao = RoleDAO(db_config)
        self.dept_dao = DeptDAO(db_config)
        self.menu_dao = MenuDAO(db_config)
        self.oper_log_dao = OperLogDAO(db_config)
        self.jwt_config = jwt_config

    def login(self, username: str, password: str) -> Optional[Dict]:
        """用户登录，返回token和用户信息"""
        user = self.user_dao.get_user_by_username(username)
        if not user:
            return None
        if user["status"] != 1:
            return None

        # 验证密码
        stored = user["password"]
        if stored.startswith("$2b$") or stored.startswith("$2a$"):
            if not bcrypt.checkpw(password.encode(), stored.encode()):
                return None
        else:
            if stored != password:
                return None

        # 生成JWT
        token = self._generate_token(user["user_id"], user["username"])
        user_info = self._build_user_info(user)
        return {"token": token, "user_info": user_info}

    def _generate_token(self, user_id: int, username: str) -> str:
        user = self.user_dao.get_user_by_id(user_id)
        roles = self.user_dao.get_user_roles(user_id)
        payload = {
            "user_id": user_id,
            "username": username,
            "dept_id": user.get("dept_id", 0) if user else 0,
            "role_keys": [r["role_key"] for r in roles],
            "exp": datetime.utcnow() + timedelta(minutes=self.jwt_config.get("expire_minutes", 1440)),
            "iat": datetime.utcnow(),
        }
        return jwt.encode(
            payload,
            self.jwt_config["secret_key"],
            algorithm=self.jwt_config.get("algorithm", "HS256")
        )

    def verify_token(self, token: str) -> Optional[Dict]:
        """验证JWT，返回payload"""
        try:
            payload = jwt.decode(
                token,
                self.jwt_config["secret_key"],
                algorithms=[self.jwt_config.get("algorithm", "HS256")]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_user_info(self, user_id: int) -> Optional[Dict]:
        user = self.user_dao.get_user_by_id(user_id)
        if not user:
            return None
        return self._build_user_info(user)

    def list_users(self, keyword: str = "", dept_id: int = 0, status: int = -1,
                   page_num: int = 1, page_size: int = 10) -> tuple:
        users, total = self.user_dao.list_users(keyword, dept_id, status, page_num, page_size)
        for user in users:
            roles = self.user_dao.get_user_roles(user["user_id"])
            user["roles"] = [{"role_id": r["role_id"], "role_name": r["role_name"], "role_key": r["role_key"]} for r in roles]
        return users, total

    def create_user(self, data: Dict) -> int:
        data.setdefault("status", 1)
        data.setdefault("repair_specialty", "")
        if "password" in data and data["password"]:
            data["password"] = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
        user_id = self.user_dao.insert_user(data)
        if "role_ids" in data and data["role_ids"]:
            for role_id in data["role_ids"]:
                self.user_dao.insert_user_role(user_id, role_id)
        return user_id

    def update_user(self, data: Dict) -> bool:
        user = self.user_dao.get_user_by_id(data["user_id"])
        if not user:
            return False
        data.setdefault("status", user.get("status", 1))
        data.setdefault("repair_specialty", user.get("repair_specialty", ""))
        self.user_dao.update_user(data)
        if "role_ids" in data:
            self.user_dao.delete_user_roles(data["user_id"])
            for role_id in data["role_ids"]:
                self.user_dao.insert_user_role(data["user_id"], role_id)
        return True

    def change_password(self, user_id: int, old_pwd: str, new_pwd: str) -> bool:
        user = self.user_dao.get_user_by_id(user_id)
        if not user:
            return False
        stored = user["password"]
        if stored.startswith("$2b$") or stored.startswith("$2a$"):
            if not bcrypt.checkpw(old_pwd.encode(), stored.encode()):
                return False
        else:
            if stored != old_pwd:
                return False
        hashed = bcrypt.hashpw(new_pwd.encode(), bcrypt.gensalt()).decode()
        self.user_dao.update_password(user_id, hashed)
        return True

    def delete_user(self, user_id: int) -> bool:
        self.user_dao.delete_user_roles(user_id)
        self.user_dao.delete_user(user_id)
        return True

    def get_user_detail(self, user_id: int) -> Optional[Dict]:
        return self.get_user_info(user_id)

    def list_repairers(self) -> List[Dict]:
        return self.user_dao.list_repairers()

    def list_roles(self, keyword: str = "", page_num: int = 1, page_size: int = 10) -> tuple:
        return self.role_dao.list_roles(keyword, page_num, page_size)

    def get_dept_tree(self) -> List[Dict]:
        """构建部门树"""
        depts = self.dept_dao.list_all_depts()
        return self._build_dept_tree(depts, 0)

    def _build_dept_tree(self, depts: List[Dict], parent_id: int) -> List[Dict]:
        tree = []
        for d in depts:
            if d.get("parent_id", 0) == parent_id:
                node = {**d, "children": self._build_dept_tree(depts, d["dept_id"])}
                tree.append(node)
        return tree

    def get_menu_tree(self) -> List[Dict]:
        menus = self.menu_dao.list_all_menus()
        return self._build_menu_tree(menus, 0)

    def get_user_menus(self, user_id: int) -> List[Dict]:
        menus = self.menu_dao.get_menus_by_user_id(user_id)
        return self._build_menu_tree(menus, 0)

    def get_user_perms(self, user_id: int) -> List[str]:
        """返回当前用户拥有的所有权限码（扁平 perms 列表）

        前后端协同设计：前端只关心"我能做什么"（perms），
        不再依赖后端构建的菜单树（path/component 由前端路由决定）。
        """
        menus = self.menu_dao.get_menus_by_user_id(user_id)
        perms: List[str] = []
        for m in menus:
            p = m.get("perms")
            if p and p not in perms:
                perms.append(p)
        return perms

    def _build_menu_tree(self, menus: List[Dict], parent_id: int) -> List[Dict]:
        tree = []
        for m in menus:
            if m.get("parent_id", 0) == parent_id:
                node = {**m, "children": self._build_menu_tree(menus, m["menu_id"])}
                tree.append(node)
        return tree

    def check_permission(self, user_id: int, permission: str) -> bool:
        menus = self.menu_dao.get_menus_by_user_id(user_id)
        for m in menus:
            if m.get("perms") == permission:
                return True
        return False

    def add_oper_log(self, user_id: int, username: str, oper_type: str,
                     oper_desc: str, oper_ip: str = "127.0.0.1") -> None:
        self.oper_log_dao.insert_log({
            "user_id": user_id, "username": username,
            "oper_type": oper_type, "oper_desc": oper_desc, "oper_ip": oper_ip
        })

    def _build_user_info(self, user: Dict) -> Dict:
        roles = self.user_dao.get_user_roles(user["user_id"])
        dept = self.dept_dao.get_dept_by_id(user.get("dept_id", 0)) if user.get("dept_id") else None
        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "nickname": user.get("nickname", ""),
            "dept_id": user.get("dept_id", 0),
            "dept_name": dept["dept_name"] if dept else "",
            "phone": user.get("phone", ""),
            "email": user.get("email", ""),
            "repair_specialty": user.get("repair_specialty", ""),
            "status": user.get("status", 1),
            "role_ids": [r["role_id"] for r in roles],
            "role_keys": [r["role_key"] for r in roles],
            "role_names": [r["role_name"] for r in roles],
            "create_time": user.get("create_time"),
        }
