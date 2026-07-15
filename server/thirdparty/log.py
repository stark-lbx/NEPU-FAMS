"""
日志封装 (基于 loguru)
"""
import sys
import os
from loguru import logger
from typing import Optional


def setup_logger(log_level: str = "INFO", log_dir: str = "logs",
                 rotation: str = "10 MB", retention: str = "7 days") -> None:
    """
    配置日志系统
    Args:
        log_level: 日志级别
        log_dir: 日志目录
        rotation: 日志轮转大小
        retention: 日志保留天数
    """
    logger.remove()  # 移除默认 handler

    # 控制台输出
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True,
    )

    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)

    # 文件输出 - 按日期
    logger.add(
        os.path.join(log_dir, "app_{time:YYYY-MM-DD}.log"),
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
               "{name}:{function}:{line} - {message}",
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
    )

    # 错误日志单独文件
    logger.add(
        os.path.join(log_dir, "error_{time:YYYY-MM-DD}.log"),
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
               "{name}:{function}:{line} - {message}\n{exception}",
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
    )


def get_logger(name: Optional[str] = None):
    """获取 logger 实例"""
    if name:
        return logger.bind(name=name)
    return logger
