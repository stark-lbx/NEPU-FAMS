import argparse
from common.config import LogSettings, DbSettings, EtcdSettings, FdfsSettings, MqSettings

def parse_args():
    parser = argparse.ArgumentParser(description="文件存储子服务")

    parser.add_argument("--listen_port", type=int, default=9994)
    parser.add_argument("--log_level", type=int, default=2)
    parser.add_argument("--log_async", type=bool, default=False)
    parser.add_argument("--log_path", type=str, default="stdout")
    parser.add_argument("--db_path", type=str, default="fams.db")
    parser.add_argument("--registry_center_addr", type=str, default="http://127.0.0.1:2379")
    parser.add_argument("--service_name", type=str, default="storage")
    parser.add_argument("--service_addr", type=str, default="127.0.0.1:9994")
    parser.add_argument("--fdfs_host", type=str, default="127.0.0.1:22122", help="FastDFS Tracker地址")
    parser.add_argument("--mq_url", type=str, default="amqp://admin:123456@127.0.0.1:5672/", help="消息队列地址")

    args = parser.parse_args()

    return {
        "listen_port": args.listen_port,
        "log": LogSettings(level=args.log_level, async_log=args.log_async, path=args.log_path),
        "db": DbSettings(db_path=args.db_path),
        "etcd": EtcdSettings(
            registry_center_addr=args.registry_center_addr,
            service_name=args.service_name,
            service_addr=args.service_addr
        ),
        "fdfs": FdfsSettings(fdfs_host=args.fdfs_host),
        "mq": MqSettings(mq_url=args.mq_url)
    }