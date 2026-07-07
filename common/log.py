import logging
import sys
from logging.handlers import RotatingFileHandler

_LOG_LEVEL_MAP = {
    1: logging.DEBUG,
    2: logging.INFO,
    3: logging.WARNING,
    4: logging.ERROR,
    6: logging.CRITICAL
}


def init_log(level: int = 2, async_log: bool = False, path: str = "stdout",
             fmt: str = "[%(asctime)s][%(levelname)-7s]: %(message)s"):
    """
    初始化全局日志
    :param level: 日志等级 1-debug 2-info 3-warn 4-error 6-off
    :param async_log: 是否异步（简化版暂同步，后续可扩展）
    :param path: 输出路径 stdout=控制台，其他为文件路径
    :param fmt: 日志格式
    """
    log_level = _LOG_LEVEL_MAP.get(level, logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    formatter = logging.Formatter(fmt, datefmt="%H:%M:%S")

    if path == "stdout":
        handler = logging.StreamHandler(sys.stdout)
    else:
        handler = RotatingFileHandler(path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8')

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def get_logger(name: str = "fams"):
    return logging.getLogger(name)