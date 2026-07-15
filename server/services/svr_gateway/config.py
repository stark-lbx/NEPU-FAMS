"""
网关服务配置
"""
from services.config_loader import load_config, get_service_config, get_jwt_config


class GatewayConfig:
    def __init__(self):
        config = load_config()
        svc = get_service_config("gateway")
        jwt_cfg = get_jwt_config()

        self.HTTP_PORT = svc.get("http_port", 8000)
        self.GRPC_PORT = svc.get("grpc_port", 9000)
        self.JWT_SECRET = jwt_cfg.get("secret_key", "fams-nepu-secret-key")
        self.JWT_ALGORITHM = jwt_cfg.get("algorithm", "HS256")
        self.JWT_EXPIRE_MINUTES = jwt_cfg.get("expire_minutes", 1440)


gateway_config = GatewayConfig()
