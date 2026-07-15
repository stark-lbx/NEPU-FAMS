"""
配置加载工具 - 从 config.yaml 读取所有配置
所有微服务共享此模块
"""
import os
from pathlib import Path
from typing import Any, Dict
import yaml


_config_cache: Dict[str, Any] = {}


def load_config(config_path: str = None) -> Dict[str, Any]:
    """加载全局配置文件（带缓存）"""
    global _config_cache
    if _config_cache:
        return _config_cache

    if config_path is None:
        # 从当前文件向上找到 config.yaml
        # services/config_loader.py -> server -> config.yaml
        config_path = Path(__file__).parent.parent / "config.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        _config_cache = yaml.safe_load(f)

    return _config_cache


def get_database_config(service_name: str) -> Dict:
    """获取指定服务的数据库配置"""
    config = load_config()
    return config.get("database", {}).get(service_name, {})


def get_service_config(service_name: str) -> Dict:
    """获取指定服务的端口配置"""
    config = load_config()
    return config.get("services", {}).get(service_name, {})


def get_redis_config() -> Dict:
    return load_config().get("redis", {})


def get_etcd_config() -> Dict:
    return load_config().get("etcd", {})


def get_jwt_config() -> Dict:
    return load_config().get("jwt", {})


def get_rabbitmq_config() -> Dict:
    return load_config().get("rabbitmq", {})


def get_file_storage_config() -> Dict:
    return load_config().get("file_storage", {})


def get_llm_config() -> Dict:
    return load_config().get("llm", {})
