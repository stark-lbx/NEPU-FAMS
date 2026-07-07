import redis
from common.mq import MqConsumer
from common.config import QueueSettings
from common.log import get_logger

logger = get_logger("asset_consumer")


class AssetMqConsumer:
    def __init__(self, mq_url: str, cache_queue_settings: QueueSettings, redis_client: redis.Redis):
        self.redis = redis_client
        self.consumer = MqConsumer(mq_url, cache_queue_settings, self._handle_message)

    def _handle_message(self, data: dict):
        """处理资产模块缓存删除消息"""
        cache_key = data.get("cache_key", "")
        cache_pattern = data.get("cache_pattern", "")

        if cache_key:
            self.redis.delete(cache_key)
            logger.info(f"资产服务删除缓存: {cache_key}")

        if cache_pattern:
            keys = self.redis.keys(cache_pattern)
            if keys:
                self.redis.delete(*keys)
                logger.info(f"资产服务批量删除缓存: {cache_pattern}, 数量: {len(keys)}")

    def start(self):
        self.consumer.start()
        logger.info("资产服务MQ消费者启动成功")