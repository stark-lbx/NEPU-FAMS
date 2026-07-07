"""操作日志模块 - 记录用户登录、查询、修改、提交等操作"""
import sqlite3
import logging
from common.utils import generate_biz_id, now_str

# 文件日志
_file_logger = None

def _get_file_logger():
    global _file_logger
    if _file_logger is None:
        _file_logger = logging.getLogger("fams_oper")
        _file_logger.setLevel(logging.INFO)
        handler = logging.FileHandler("fams_oper.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        _file_logger.addHandler(handler)
    return _file_logger


class OperLogDao:
    """操作日志数据库访问"""
    table_name = "sys_oper_log"

    def __init__(self, db_path: str = "fams.db"):
        self.db_path = db_path

    def insert(self, oper_user_biz_id: str, oper_module: str, oper_type: str,
               oper_content: str = "", request_url: str = "", ip_address: str = "") -> str:
        biz_id = generate_biz_id()
        sql = """INSERT INTO sys_oper_log (biz_id, oper_user_biz_id, oper_module, oper_type,
                  oper_content, request_url, ip_address, oper_time)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(sql, (biz_id, oper_user_biz_id, oper_module, oper_type,
                           oper_content, request_url, ip_address, now_str()))
        conn.commit()
        conn.close()
        return biz_id


def oper_log(oper_user_biz_id: str, oper_module: str, oper_type: str,
             oper_content: str = "", request_url: str = "", ip_address: str = "",
             db_path: str = "fams.db"):
    """统一操作日志入口：写入数据库 + 文件日志"""
    try:
        OperLogDao(db_path).insert(oper_user_biz_id, oper_module, oper_type,
                                    oper_content, request_url, ip_address)
    except Exception:
        pass  # 日志记录失败不应影响主流程

    logger = _get_file_logger()
    logger.info(f"[{oper_module}] [{oper_type}] user={oper_user_biz_id} | url={request_url} | {oper_content}")
