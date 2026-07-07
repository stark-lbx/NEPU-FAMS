import os
# 兼容 etcd3 旧版 pb 文件，强制使用纯 Python 解析器
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from services.svc_user.config import parse_args
from services.svc_user.server_builder import UserServerBuilder
from common.log import get_logger

logger = get_logger("user_main")

def main():
    # 解析命令行参数，获取全量配置
    config = parse_args()

    # 建造者构建服务，对齐 C++ 链式调用风格
    builder = UserServerBuilder()
    server = (builder
              .with_listen_port(config["listen_port"])
              .with_log_settings(config["log"])
              .with_db_settings(config["db"])
              .with_redis_settings(config["redis"])
              .with_etcd_settings(config["etcd"])
              .with_mq_settings(config["mq"])
              .build())

    # 启动服务
    server.start()
    logger.info(f"用户服务启动成功，监听端口: {config['listen_port']}")
    server.wait_for_termination()

if __name__ == "__main__":
    main()