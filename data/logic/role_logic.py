from data.basic.role_dao import RoleDao, UserRoleDao

class RoleLogic:
    def __init__(self, db_path: str = "fams.db"):
        self.role_dao = RoleDao(db_path)
        self.user_role_dao = UserRoleDao(db_path)

    def get_user_roles(self, user_biz_id: str):
        return self.user_role_dao.list_by_user(user_biz_id)

    def get_all_roles(self):
        return self.role_dao.list_all()