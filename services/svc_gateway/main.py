import os
# 兼容 etcd3 旧版 pb 文件，强制使用纯 Python 解析器
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from services.svc_gateway.config import parse_args
from services.svc_gateway.server_builder import GatewayServerBuilder
from common.log import get_logger

logger = get_logger("gateway_main")

def main():
    config = parse_args()

    builder = GatewayServerBuilder()
    app = (builder
           .with_listen_port(config["listen_port"])
           .with_log_settings(config["log"])
           .with_etcd_settings(config["etcd"])
           .build())

    logger.info(f"网关服务启动成功，端口: {config['listen_port']}")
    app.run(host="0.0.0.0", port=config["listen_port"], debug=False)

if __name__ == "__main__":
    main()