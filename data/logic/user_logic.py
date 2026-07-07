from data.basic.user_dao import UserDao
from data.basic.role_dao import RoleDao, UserRoleDao
from common.utils import generate_biz_id
import sqlite3


class UserLogic:
    def __init__(self, db_path: str = "fams.db"):
        self.user_dao = UserDao(db_path)
        self.role_dao = RoleDao(db_path)
        self.user_role_dao = UserRoleDao(db_path)

    def create_user(self, user_data: dict, role_code: str = "teacher") -> str:
        """创建用户 + 分配角色，事务保证原子性"""
        biz_id = generate_biz_id()
        conn = sqlite3.connect(self.user_dao.db_path)
        try:
            # 1. 创建用户
            user_data["biz_id"] = biz_id
            fields = ",".join(user_data.keys())
            placeholders = ",".join(["?"] * len(user_data))
            sql = f"INSERT INTO sys_user ({fields}) VALUES ({placeholders})"
            conn.execute(sql, list(user_data.values()))

            # 2. 绑定角色 — 通过 role_code 查 role_biz_id
            row = conn.execute(
                "SELECT biz_id FROM sys_role WHERE role_code = ? AND is_delete = 0",
                (role_code,)
            ).fetchone()
            if not row:
                raise Exception(f"角色「{role_code}」不存在")
            role_biz_id = row[0]

            conn.execute(
                "INSERT INTO sys_user_role (user_biz_id, role_biz_id) VALUES (?, ?)",
                (biz_id, role_biz_id)
            )

            conn.commit()
            return biz_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def login_verify(self, username: str, password: str) -> dict:
        """登录校验"""
        user = self.user_dao.select_by_username(username)
        if not user or user["password"] != password:
            return None
        return user

    def list_by_dept(self, dept_biz_id: str):
        """按部门查询用户列表"""
        return self.user_dao.list_by_dept(dept_biz_id)

    def get_user(self, biz_id: str):
        """根据业务ID查询用户"""
        return self.user_dao.select_by_biz_id(biz_id)

    def list_users_by_permission(self, role_codes: list) -> list:
        """根据角色层级查询可见用户列表（用于权限控制）"""
        conn = sqlite3.connect(self.user_dao.db_path)
        conn.row_factory = sqlite3.Row
        if not role_codes:
            conn.close()
            return []
        placeholders = ",".join(["?"] * len(role_codes))
        sql = f"""SELECT DISTINCT u.* FROM sys_user u
                  INNER JOIN sys_user_role ur ON u.biz_id = ur.user_biz_id
                  INNER JOIN sys_role r ON ur.role_biz_id = r.biz_id
                  WHERE r.role_code IN ({placeholders}) AND u.is_delete = 0
                  ORDER BY u.create_time DESC"""
        rows = conn.execute(sql, role_codes).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_user_with_roles(self, user_biz_id: str) -> dict:
        """获取用户信息及其角色列表"""
        user = self.user_dao.select_by_biz_id(user_biz_id)
        if not user:
            return None
        roles = self.user_role_dao.list_by_user(user_biz_id)
        user["roles"] = [{"role_code": r["role_code"], "role_name": r["role_name"]} for r in roles]
        return user

    def promote_user_role(self, target_biz_id: str, new_role_code: str, operator_biz_id: str) -> bool:
        """提升/修改用户角色，需校验操作者权限（业务层检查）"""
        conn = sqlite3.connect(self.user_dao.db_path)
        try:
            # 获取目标用户当前角色
            target_row = conn.execute("""
                SELECT r.role_code FROM sys_user_role ur
                INNER JOIN sys_role r ON ur.role_biz_id = r.biz_id
                WHERE ur.user_biz_id = ?
            """, (target_biz_id,)).fetchone()
            if not target_row:
                raise Exception("目标用户未分配角色")

            # 获取操作者角色
            op_row = conn.execute("""
                SELECT r.role_code FROM sys_user_role ur
                INNER JOIN sys_role r ON ur.role_biz_id = r.biz_id
                WHERE ur.user_biz_id = ?
            """, (operator_biz_id,)).fetchone()
            if not op_row:
                raise Exception("操作者未分配角色")

            from common.utils import can_edit, get_role_level
            if not can_edit(target_row[0], op_row[0]):
                raise Exception("无权修改该用户的角色")

            if get_role_level(new_role_code) >= get_role_level(op_row[0]):
                raise Exception("不能将用户提升到您的权限级别或更高")

            # 查找新角色的 biz_id
            role_row = conn.execute(
                "SELECT biz_id FROM sys_role WHERE role_code = ? AND is_delete = 0",
                (new_role_code,)
            ).fetchone()
            if not role_row:
                raise Exception(f"角色「{new_role_code}」不存在")

            # 删除旧角色绑定，插入新绑定
            conn.execute("DELETE FROM sys_user_role WHERE user_biz_id = ?", (target_biz_id,))
            conn.execute(
                "INSERT INTO sys_user_role (user_biz_id, role_biz_id) VALUES (?, ?)",
                (target_biz_id, role_row[0])
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def update_user(self, biz_id: str, data: dict, editor_role_code: str) -> bool:
        """更新用户信息，校验编辑权限"""
        user = self.user_dao.select_by_biz_id(biz_id)
        if not user:
            raise Exception("用户不存在")

        # 获取目标用户角色
        conn = sqlite3.connect(self.user_dao.db_path)
        target_role = conn.execute("""
            SELECT r.role_code FROM sys_user_role ur
            INNER JOIN sys_role r ON ur.role_biz_id = r.biz_id
            WHERE ur.user_biz_id = ?
        """, (biz_id,)).fetchone()
        conn.close()

        if target_role:
            from common.utils import can_edit
            if not can_edit(target_role[0], editor_role_code):
                raise Exception("无权编辑该用户")

        return self.user_dao.update_by_biz_id(biz_id, data)
