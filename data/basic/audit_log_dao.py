from .base_dao import BaseDao

class AuditLogDao(BaseDao):
    table_name = "sys_oper_log"

    def add_log(self, oper_user_biz_id: str, oper_module: str, oper_type: str,
                oper_content: str = "", business_type: int = None, business_biz_id: str = "",
                request_url: str = "", ip_address: str = ""):
        data = {
            "biz_id": __import__('common.utils', fromlist=['generate_biz_id']).generate_biz_id(),
            "oper_user_biz_id": oper_user_biz_id,
            "oper_module": oper_module,
            "oper_type": oper_type,
            "oper_content": oper_content,
            "business_type": business_type,
            "business_biz_id": business_biz_id,
            "request_url": request_url,
            "ip_address": ip_address
        }
        return self.insert(data)