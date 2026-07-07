from dataclasses import dataclass

@dataclass
class LogSettings:
    """日志配置，对应 bitelog::log_settings"""
    level: int = 2          # 1-debug;2-info;3-warn;4-error; 6-off
    async_log: bool = False
    format: str = "[%(asctime)s][%(levelname)-7s]: %(message)s"
    path: str = "stdout"

@dataclass
class DbSettings:
    """数据库配置，对应 biteodb::mysql_settings（SQLite版）"""
    db_path: str = "fams.db"

@dataclass
class RedisSettings:
    """Redis配置，对应 biteredis::redis_settings"""
    host: str = "127.0.0.1"
    port: int = 6379
    user: str = "default"
    password: str = "123456"
    connection_pool_size: int = 5

@dataclass
class EtcdSettings:
    """注册中心配置，对应 svc_file::registry_settings"""
    registry_center_addr: str = "http://127.0.0.1:2379"
    service_name: str = ""
    service_addr: str = ""

@dataclass
class MqSettings:
    """消息队列基础配置"""
    mq_url: str = "amqp://admin:123456@127.0.0.1:5672/"

@dataclass
class QueueSettings:
    """单个队列配置，对齐C++队列JSON结构"""
    exchange: str = ""
    type: str = "direct"       # direct/delayed/fanout
    queue: str = ""
    binding_key: str = ""
    delayed_ttl: int = 0       # 延迟队列秒数，type=delayed时生效

@dataclass
class FdfsSettings:
    """FastDFS配置，对应 bitefdfs::fdfs_settings"""
    fdfs_host: str = "127.0.0.1:22122"