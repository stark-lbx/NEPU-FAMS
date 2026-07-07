from data.basic.dept_dao import DeptDao
from common.utils import generate_biz_id
from common.log import get_logger

logger = get_logger("dept_logic")

class DeptLogic:
    def __init__(self, db_path: str = "fams.db"):
        self.dept_dao = DeptDao(db_path)

    def get_dept_tree(self):
        """获取完整部门树"""
        all_dept = self.dept_dao.list_all_tree()
        return self._build_tree(all_dept, parent_id="")

    def _build_tree(self, dept_list, parent_id):
        tree = []
        for dept in dept_list:
            if dept["parent_biz_id"] == parent_id:
                children = self._build_tree(dept_list, dept["biz_id"])
                dept["children"] = children
                tree.append(dept)
        return tree

    def create_dept(self, dept_data: dict) -> str:
        """新增部门"""
        dept_data["biz_id"] = generate_biz_id()
        self.dept_dao.insert(dept_data)
        logger.info(f"新增部门: {dept_data['dept_name']}")
        return dept_data["biz_id"]

    def update_dept(self, biz_id: str, dept_data: dict) -> bool:
        """更新部门"""
        return self.dept_dao.update_by_biz_id(biz_id, dept_data)

    def delete_dept(self, biz_id: str) -> bool:
        """软删除部门"""
        # 检查是否有子部门
        children = self.dept_dao.list_by_parent(biz_id)
        if children:
            raise Exception("存在子部门，不可删除")
        return self.dept_dao.delete_by_biz_id(biz_id)