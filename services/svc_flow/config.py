import argparse
from common.config import LogSettings, DbSettings, RedisSettings, EtcdSettings, MqSettings

def parse_args():
    parser = argparse.ArgumentParser(description="流程审批子服务")

    parser.add_argument("--listen_port", type=int, default=9993)
    parser.add_argument("--log_level", type=int, default=2)
    parser.add_argument("--log_async", type=bool, default=False)
    parser.add_argument("--log_path", type=str, default="stdout")
    parser.add_argument("--db_path", type=str, default="fams.db")
    parser.add_argument("--redis_host", type=str, default="127.0.0.1")
    parser.add_argument("--redis_port", type=int, default=6379)
    parser.add_argument("--redis_user", type=str, default="default")
    parser.add_argument("--redis_passwd", type=str, default="123456")
    parser.add_argument("--redis_connection_pool_size", type=int, default=5)
    parser.add_argument("--registry_center_addr", type=str, default="http://127.0.0.1:2379")
    parser.add_argument("--service_name", type=str, default="flow")
    parser.add_argument("--service_addr", type=str, default="127.0.0.1:9993")
    parser.add_argument("--mq_url", type=str, default="amqp://admin:123456@127.0.0.1:5672/")

    args = parser.parse_args()

    return {
        "listen_port": args.listen_port,
        "log": LogSettings(level=args.log_level, async_log=args.log_async, path=args.log_path),
        "db": DbSettings(db_path=args.db_path),
        "redis": RedisSettings(
            host=args.redis_host, port=args.redis_port,
            user=args.redis_user, password=args.redis_passwd,
            connection_pool_size=args.redis_connection_pool_size
        ),
        "etcd": EtcdSettings(
            registry_center_addr=args.registry_center_addr,
            service_name=args.service_name,
            service_addr=args.service_addr
        ),
        "mq": MqSettings(mq_url=args.mq_url)
    }