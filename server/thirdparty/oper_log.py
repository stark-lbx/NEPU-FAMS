"""
统一操作日志工具类
提供 sys_oper_log / repair_operation_log / asset_operation_log 三张表的统一写入接口
所有写日志函数内部用 try-except 包裹，写入失败不抛出异常、不影响主业务
"""
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.basic.user_dao import OperLogDAO
from data.basic.repair_dao import RepairOperLogDAO
from data.basic.asset_dao import AssetOperLogDAO
from thirdparty.log import get_logger

_log = get_logger("oper_log")


# ==================== 通用操作日志 (sys_oper_log) ====================

def log_operation(db_config: dict,
                  user_id: int,
                  username: str,
                  oper_type: str,
                  oper_desc: str,
                  oper_ip: str = "127.0.0.1",
                  **kwargs) -> None:
    """
    写入通用操作日志到 sys_oper_log 表
    失败时静默忽略，不影响主业务
    """
    try:
        dao = OperLogDAO(db_config)
        dao.insert_log({
            "user_id": user_id,
            "username": username,
            "oper_type": oper_type,
            "oper_desc": oper_desc,
            "oper_ip": oper_ip,
        })
    except Exception as e:
        _log.warning(f"oper_log 写入失败 (user={username}, type={oper_type}): {e}")


# ==================== 维修操作日志 (repair_operation_log) ====================

def log_repair_operation(db_config: dict,
                         order_id: int,
                         operator_id: int,
                         oper_type: str,
                         oper_desc: str,
                         oper_ip: str = "127.0.0.1") -> None:
    """
    写入维修工单操作日志到 repair_operation_log 表
    失败时静默忽略，不影响主业务
    """
    try:
        dao = RepairOperLogDAO(db_config)
        dao.insert_log({
            "order_id": order_id,
            "operator_id": operator_id,
            "oper_type": oper_type,
            "oper_desc": oper_desc,
            "oper_ip": oper_ip,
        })
    except Exception as e:
        _log.warning(f"repair_oper_log 写入失败 (order={order_id}, type={oper_type}): {e}")


# ==================== 资产变更日志 (asset_operation_log) ====================

def log_asset_operation(db_config: dict,
                        asset_id: int,
                        operator_id: int,
                        oper_type: str,
                        field_name: str = "",
                        old_value: str = "",
                        new_value: str = "",
                        oper_ip: str = "127.0.0.1") -> None:
    """
    写入资产变更日志到 asset_operation_log 表
    失败时静默忽略，不影响主业务
    """
    try:
        dao = AssetOperLogDAO(db_config)
        dao.insert_log({
            "asset_id": asset_id,
            "operator_id": operator_id,
            "oper_type": oper_type,
            "field_name": field_name,
            "old_value": str(old_value) if old_value else "",
            "new_value": str(new_value) if new_value else "",
            "oper_ip": oper_ip,
        })
    except Exception as e:
        _log.warning(f"asset_oper_log 写入失败 (asset={asset_id}, type={oper_type}): {e}")
