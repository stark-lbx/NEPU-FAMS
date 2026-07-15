"""
gRPC 客户端封装（etcd 服务发现 + 负载均衡）
"""
import random
import grpc
from typing import Any, Dict, List, Optional, Callable
from thirdparty.log import get_logger

logger = get_logger(__name__)


class RPCClientFactory:
    """
    gRPC 客户端工厂
    从 etcd 发现服务节点并创建 gRPC 连接，支持简单轮询负载均衡
    """

    def __init__(self, etcd_client):
        self.etcd = etcd_client
        self._connections: Dict[str, List[grpc.Channel]] = {}
        self._round_robin_index: Dict[str, int] = {}

    def get_channel(self, service_name: str) -> Optional[grpc.Channel]:
        """获取 gRPC channel（轮询负载均衡）"""
        services = self.etcd.discover_services(service_name)
        if not services:
            logger.error(f"未发现可用服务: {service_name}")
            return None

        # 清理失效连接
        self._connections.setdefault(service_name, [])

        # 随机选取一个节点
        svc = random.choice(services)
        host, port = svc["host"], svc["port"]
        target = f"{host}:{port}"

        channel = grpc.insecure_channel(
            target,
            options=[
                ("grpc.keepalive_time_ms", 30000),
                ("grpc.keepalive_timeout_ms", 10000),
                ("grpc.http2.max_pings_without_data", 0),
            ],
        )
        logger.info(f"gRPC 连接: {service_name} -> {target}")
        return channel

    def call_with_stub(self, service_name: str, stub_class, method: str,
                       request: Any, timeout: int = 10) -> Any:
        """
        通用 gRPC 调用
        Args:
            service_name: 服务名
            stub_class: gRPC Stub 类
            method: 方法名
            request: 请求对象 (Protobuf)
            timeout: 超时时间
        """
        channel = self.get_channel(service_name)
        if not channel:
            raise RuntimeError(f"无法连接到服务: {service_name}")

        try:
            stub = stub_class(channel)
            grpc_method = getattr(stub, method)
            response = grpc_method(request, timeout=timeout)
            channel.close()
            return response
        except grpc.RpcError as e:
            logger.error(f"gRPC 调用失败 [{service_name}.{method}]: {e.code()} - {e.details()}")
            channel.close()
            raise
        except Exception as e:
            logger.error(f"gRPC 调用异常 [{service_name}.{method}]: {e}")
            channel.close()
            raise
