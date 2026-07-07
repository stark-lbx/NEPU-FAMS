import argparse
from common.config import LogSettings, EtcdSettings

def parse_args():
    parser = argparse.ArgumentParser(description="API网关服务")

    parser.add_argument("--listen_port", type=int, default=8080, help="网关监听端口")
    parser.add_argument("--log_level", type=int, default=2)
    parser.add_argument("--log_async", type=bool, default=False)
    parser.add_argument("--log_path", type=str, default="stdout")
    parser.add_argument("--registry_center_addr", type=str, default="http://127.0.0.1:2379")
    parser.add_argument("--service_name", type=str, default="gateway")
    parser.add_argument("--service_addr", type=str, default="127.0.0.1:8080")

    args = parser.parse_args()

    return {
        "listen_port": args.listen_port,
        "log": LogSettings(level=args.log_level, async_log=args.log_async, path=args.log_path),
        "etcd": EtcdSettings(
            registry_center_addr=args.registry_center_addr,
            service_name=args.service_name,
            service_addr=args.service_addr
        )
    }