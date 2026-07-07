from .base_dao import BaseDao

class DeptDao(BaseDao):
    table_name = "sys_department"

    def list_by_parent(self, parent_biz_id: str):
        return self.list_by_condition({"parent_biz_id": parent_biz_id}, order_by="dept_sort ASC")

    def list_all_tree(self):
        return self.list_by_condition({}, order_by="dept_sort ASC")