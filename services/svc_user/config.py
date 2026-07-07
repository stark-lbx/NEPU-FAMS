import argparse
from common.config import LogSettings, DbSettings, RedisSettings, EtcdSettings, MqSettings


def parse_args():
    """解析命令行参数，返回全量配置对象，对齐 C++ google::ParseCommandLineFlags"""
    parser = argparse.ArgumentParser(description="用户权限子服务")

    # 服务基础配置
    parser.add_argument("--listen_port", type=int, default=9991, help="服务监听端口")

    # 日志配置
    parser.add_argument("--log_level", type=int, default=2, help="日志等级: 1-debug;2-info;3-warn;4-error; 6-off")
    parser.add_argument("--log_async", type=bool, default=False, help="日志是否异步")
    parser.add_argument("--log_path", type=str, default="stdout", help="日志输出目标")

    # 数据库配置
    parser.add_argument("--db_path", type=str, default="fams.db", help="SQLite数据库文件路径")

    # Redis配置
    parser.add_argument("--redis_host", type=str, default="127.0.0.1", help="Redis服务器地址")
    parser.add_argument("--redis_port", type=int, default=6379, help="Redis端口")
    parser.add_argument("--redis_user", type=str, default="default", help="Redis用户名")
    parser.add_argument("--redis_passwd", type=str, default="123456", help="Redis密码")
    parser.add_argument("--redis_connection_pool_size", type=int, default=5, help="Redis连接池大小")

    # 注册中心配置
    parser.add_argument("--registry_center_addr", type=str, default="http://127.0.0.1:2379", help="注册中心地址")
    parser.add_argument("--service_name", type=str, default="user", help="服务名称")
    parser.add_argument("--service_addr", type=str, default="127.0.0.1:9991", help="服务地址")

    # 消息队列配置
    parser.add_argument("--mq_url", type=str, default="amqp://admin:123456@127.0.0.1:5672/", help="消息队列地址")

    args = parser.parse_args()

    # 组装配置结构体
    log_settings = LogSettings(level=args.log_level, async_log=args.log_async, path=args.log_path)
    db_settings = DbSettings(db_path=args.db_path)
    redis_settings = RedisSettings(
        host=args.redis_host, port=args.redis_port,
        user=args.redis_user, password=args.redis_passwd,
        connection_pool_size=args.redis_connection_pool_size
    )
    etcd_settings = EtcdSettings(
        registry_center_addr=args.registry_center_addr,
        service_name=args.service_name,
        service_addr=args.service_addr
    )
    mq_settings = MqSettings(mq_url=args.mq_url)

    return {
        "listen_port": args.listen_port,
        "log": log_settings,
        "db": db_settings,
        "redis": redis_settings,
        "etcd": etcd_settings,
        "mq": mq_settings
    }