from flask import Flask
from services.svc_gateway.routes import api_bp
from common.log import init_log, get_logger
from common.config import LogSettings, EtcdSettings
import etcd3

logger = get_logger("gateway_server")

class GatewayServerBuilder:
    def __init__(self):
        self._listen_port = 8080
        self._log_settings: LogSettings = None
        self._etcd_settings: EtcdSettings = None

    def with_listen_port(self, port: int):
        self._listen_port = port
        return self

    def with_log_settings(self, settings: LogSettings):
        self._log_settings = settings
        return self

    def with_etcd_settings(self, settings: EtcdSettings):
        self._etcd_settings = settings
        return self

    def build(self) -> Flask:
        init_log(
            level=self._log_settings.level,
            async_log=self._log_settings.async_log,
            path=self._log_settings.path,
            fmt=self._log_settings.format
        )
        logger.info("初始化日志完成")

        app = Flask(__name__)
        from flask_cors import CORS
        CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
        app.register_blueprint(api_bp, url_prefix="/api")

        # 注册到etcd
        etcd_host, etcd_port = self._etcd_settings.registry_center_addr.replace("http://", "").split(":")
        etcd_client = etcd3.client(host=etcd_host, port=int(etcd_port))
        etcd_client.put(f"/services/{self._etcd_settings.service_name}", self._etcd_settings.service_addr)
        logger.info(f"网关注册etcd成功")

        return app