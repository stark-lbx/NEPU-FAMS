"""
etcd 注册中心客户端封装
"""
import json
import threading
import time
from typing import Any, Dict, List, Optional
import etcd3
from thirdparty.log import get_logger

logger = get_logger(__name__)


class EtcdClient:
    """etcd 注册中心客户端"""

    def __init__(self, config: Dict):
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 2379)
        self._client: Optional[etcd3.Etcd3Client] = None
        self._lease = None
        self._keepalive_thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def client(self) -> etcd3.Etcd3Client:
        if self._client is None:
            self._client = etcd3.client(host=self.host, port=self.port)
            logger.info(f"etcd 连接成功: {self.host}:{self.port}")
        return self._client

    def register_service(self, service_name: str, host: str, port: int,
                         metadata: Optional[Dict] = None, ttl: int = 30) -> bool:
        """注册服务到 etcd"""
        try:
            key = f"/services/{service_name}/{host}:{port}"
            value = {
                "host": host,
                "port": port,
                "service_name": service_name,
                "metadata": metadata or {},
            }
            self.client.put(key, json.dumps(value))
            logger.info(f"服务注册成功: {service_name} -> {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"服务注册失败: {e}")
            return False

    def register_with_lease(self, service_name: str, host: str, port: int,
                            metadata: Optional[Dict] = None, ttl: int = 30) -> bool:
        """使用租约注册服务（支持心跳保活）"""
        try:
            self._lease = self.client.lease(ttl)
            key = f"/services/{service_name}/{host}:{port}"
            value = {
                "host": host,
                "port": port,
                "service_name": service_name,
                "metadata": metadata or {},
            }
            self.client.put(key, json.dumps(value), lease=self._lease)
            self._start_keepalive(ttl)
            logger.info(f"服务注册成功(租约): {service_name} -> {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"服务注册失败: {e}")
            return False

    def _start_keepalive(self, ttl: int):
        """启动心跳保活线程"""
        def keepalive():
            while self._running:
                try:
                    if self._lease:
                        self._lease.refresh()
                except Exception as e:
                    logger.warning(f"etcd 心跳刷新失败: {e}")
                    try:
                        self._lease = self.client.lease(ttl)
                    except Exception:
                        pass
                time.sleep(ttl / 3)

        self._running = True
        self._keepalive_thread = threading.Thread(target=keepalive, daemon=True)
        self._keepalive_thread.start()

    def discover_services(self, service_name: str) -> List[Dict]:
        """发现服务节点"""
        try:
            services = []
            results = self.client.get_prefix(f"/services/{service_name}/")
            for value, metadata in results:
                if value:
                    services.append(json.loads(value.decode()))
            return services
        except Exception as e:
            logger.error(f"服务发现失败: {e}")
            return []

    def deregister(self, service_name: str, host: str, port: int) -> bool:
        """注销服务"""
        try:
            key = f"/services/{service_name}/{host}:{port}"
            self.client.delete(key)
            logger.info(f"服务注销: {service_name} -> {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"服务注销失败: {e}")
            return False

    def close(self):
        """关闭连接"""
        self._running = False
        if self._client:
            self._client.close()
            self._client = None
