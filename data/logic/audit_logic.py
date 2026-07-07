from data.basic.audit_log_dao import AuditLogDao

class AuditLogic:
    def __init__(self, db_path: str = "fams.db"):
        self.log_dao = AuditLogDao(db_path)

    def record_oper(self, **kwargs):
        """记录操作日志"""
        self.log_dao.add_log(**kwargs)