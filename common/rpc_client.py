import grpc
import etcd3
from typing import Dict

class RpcClientManager:
    """gRPC客户端管理器，从etcd发现服务地址"""
    _instance = None

    def __new__(cls, etcd_addr: str = "127.0.0.1:2379"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.etcd_host, cls._instance.etcd_port = etcd_addr.split(":")
            cls._instance.etcd_client = etcd3.client(host=cls._instance.etcd_host,
                                                     port=int(cls._instance.etcd_port))
            cls._instance._channel_cache: Dict[str, grpc.Channel] = {}
        return cls._instance

    def get_service_addr(self, service_name: str) -> str:
        """从etcd获取服务地址"""
        key = f"/services/{service_name}"
        value, _ = self.etcd_client.get(key)
        if not value:
            raise Exception(f"服务 {service_name} 未注册")
        return value.decode('utf-8')

    def get_channel(self, service_name: str) -> grpc.Channel:
        """获取gRPC通道，带缓存"""
        if service_name not in self._channel_cache:
            addr = self.get_service_addr(service_name)
            self._channel_cache[service_name] = grpc.insecure_channel(addr)
        return self._channel_cache[service_name]