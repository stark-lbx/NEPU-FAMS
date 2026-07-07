import uuid
import hashlib
import logging
import traceback
from datetime import datetime


# ==================== 角色层级定义 ====================
ROLE_HIERARCHY = {
    "school_admin": 4,
    "dept_admin": 3,
    "teacher": 2,
    "student": 1
}

ROLE_LABELS = {
    "school_admin": "校级管理员",
    "dept_admin": "院系管理员",
    "teacher": "教师",
    "student": "学生"
}


def get_role_level(role_code: str) -> int:
    """获取角色层级数值，未知角色返回 0"""
    return ROLE_HIERARCHY.get(role_code, 0)


def can_view(target_role_code: str, viewer_role_code: str) -> bool:
    """viewer 能否查看 target 的用户信息"""
    return get_role_level(target_role_code) <= get_role_level(viewer_role_code)


def can_edit(target_role_code: str, editor_role_code: str) -> bool:
    """editor 能否编辑 target（只能编辑严格低于自己的角色）"""
    return get_role_level(target_role_code) < get_role_level(editor_role_code)


# ==================== 通用工具函数 ====================

def generate_biz_id() -> str:
    """生成32位分布式业务ID（简化版雪花ID，实训场景够用）"""
    return uuid.uuid4().hex.replace('-', '')


def hash_password(password: str) -> str:
    """密码哈希（MD5简化，生产建议bcrypt）"""
    return hashlib.md5(password.encode('utf-8')).hexdigest()


def verify_password(raw_password: str, hashed_password: str) -> bool:
    return hash_password(raw_password) == hashed_password


def now_str() -> str:
    """返回当前时间字符串，适配SQLite datetime格式"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def today_str() -> str:
    return datetime.now().strftime('%Y-%m-%d')


# ==================== 安全错误信息封装 ====================

# 常见错误关键词 → 用户友好提示
_SAFE_ERROR_MAP = [
    ("UNIQUE constraint", "数据已存在，请勿重复添加"),
    ("NOT NULL constraint", "必填项缺失"),
    ("FOREIGN KEY constraint", "关联数据不存在"),
    ("no such table", "系统配置异常，请联系管理员"),
    ("no such column", "系统配置异常，请联系管理员"),
    ("timeout", "操作超时，请稍后重试"),
    ("already exists", "数据已存在"),
    ("not found", "请求的数据不存在"),
    ("database is locked", "系统正忙，请稍后重试"),
]

_USER_FRIENDLY_FALLBACK = "服务异常，请稍后重试"


def safe_error_msg(err: Exception, fallback: str = None) -> str:
    """将异常转换为用户友好的错误信息，不暴露系统内部细节"""
    err_str = str(err)
    for keyword, friendly in _SAFE_ERROR_MAP:
        if keyword.lower() in err_str.lower():
            return friendly
    # 记录原始错误到日志
    logger = logging.getLogger("fams_error")
    logger.error("Raw exception: %s\n%s", err_str, traceback.format_exc())
    return fallback or _USER_FRIENDLY_FALLBACK