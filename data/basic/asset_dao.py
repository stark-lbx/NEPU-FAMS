from .base_dao import BaseDao

class AssetDao(BaseDao):
    table_name = "fams_asset"

    def list_by_dept_status(self, dept_biz_id: str, status_code: str = "",
                            limit: int = 20, offset: int = 0):
        condition = {}
        if dept_biz_id:
            condition["dept_biz_id"] = dept_biz_id
        if status_code:
            condition["current_status_code"] = status_code
        return self.list_by_condition(condition, limit=limit, offset=offset)

    def count_by_dept_status(self, dept_biz_id: str, status_code: str = ""):
        condition = {}
        if dept_biz_id:
            condition["dept_biz_id"] = dept_biz_id
        if status_code:
            condition["current_status_code"] = status_code
        return self.count_by_condition(condition)


class AssetStatusLogDao(BaseDao):
    table_name = "fams_asset_status_log"

    def list_by_asset(self, asset_biz_id: str):
        return self.list_by_condition({"asset_biz_id": asset_biz_id}, order_by="create_time DESC")


class AssetAttachDao(BaseDao):
    table_name = "fams_asset_attach"

    def list_by_asset(self, asset_biz_id: str):
        return self.list_by_condition({"asset_biz_id": asset_biz_id}, order_by="create_time DESC")