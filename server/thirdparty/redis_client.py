"""
Redis 客户端封装
"""
import redis
from typing import Any, Dict, Optional
from thirdparty.log import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Redis 客户端封装"""

    def __init__(self, config: Dict):
        self.config = config
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis(
                host=self.config.get("host", "127.0.0.1"),
                port=self.config.get("port", 6379),
                password=self.config.get("password", ""),
                db=self.config.get("db", 0),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            try:
                self._client.ping()
                logger.info("Redis 连接成功")
            except Exception as e:
                logger.warning(f"Redis 连接失败: {e}")
        return self._client

    def set(self, key: str, value: str, expire: int = 0) -> bool:
        """设置字符串值"""
        try:
            if expire > 0:
                self.client.setex(key, expire, value)
            else:
                self.client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET 失败: {e}")
            return False

    def get(self, key: str) -> Optional[str]:
        """获取字符串值"""
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET 失败: {e}")
            return None

    def delete(self, *keys: str) -> int:
        """删除键"""
        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE 失败: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS 失败: {e}")
            return False

    def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        try:
            return self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE 失败: {e}")
            return False

    def hset(self, name: str, key: str, value: str) -> int:
        try:
            return self.client.hset(name, key, value)
        except Exception as e:
            logger.error(f"Redis HSET 失败: {e}")
            return 0

    def hget(self, name: str, key: str) -> Optional[str]:
        try:
            return self.client.hget(name, key)
        except Exception as e:
            logger.error(f"Redis HGET 失败: {e}")
            return None

    def hgetall(self, name: str) -> Dict:
        try:
            return self.client.hgetall(name)
        except Exception as e:
            logger.error(f"Redis HGETALL 失败: {e}")
            return {}

    def publish(self, channel: str, message: str) -> int:
        """发布消息"""
        try:
            return self.client.publish(channel, message)
        except Exception as e:
            logger.error(f"Redis PUBLISH 失败: {e}")
            return 0

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
