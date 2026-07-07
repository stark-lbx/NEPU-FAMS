import os
# 兼容 etcd3 旧版 pb 文件，强制使用纯 Python 解析器
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from services.svc_storage.config import parse_args
from services.svc_storage.server_builder import StorageServerBuilder
from common.log import get_logger

logger = get_logger("storage_main")

def main():
    config = parse_args()

    builder = StorageServerBuilder()
    server = (builder
              .with_listen_port(config["listen_port"])
              .with_log_settings(config["log"])
              .with_db_settings(config["db"])
              .with_etcd_settings(config["etcd"])
              .with_fdfs_settings(config["fdfs"])
              .with_mq_settings(config["mq"])
              .build())

    server.start()
    logger.info(f"存储服务启动成功，端口: {config['listen_port']}")
    server.wait_for_termination()

if __name__ == "__main__":
    main()