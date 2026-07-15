"""
RabbitMQ 客户端封装
"""
import json
from typing import Any, Callable, Dict, Optional
import pika
from thirdparty.log import get_logger

logger = get_logger(__name__)


class RabbitMQClient:
    """RabbitMQ 客户端封装"""

    def __init__(self, config: Dict):
        self.config = config
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel = None

    @property
    def connection(self) -> pika.BlockingConnection:
        if self._connection is None or self._connection.is_closed:
            credentials = pika.PlainCredentials(
                self.config.get("user", "admin"),
                self.config.get("password", "123456")
            )
            params = pika.ConnectionParameters(
                host=self.config.get("host", "127.0.0.1"),
                port=self.config.get("port", 5672),
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )
            self._connection = pika.BlockingConnection(params)
            logger.info("RabbitMQ 连接成功")
        return self._connection

    @property
    def channel(self):
        if self._channel is None or self._channel.is_closed:
            self._channel = self.connection.channel()
        return self._channel

    def declare_queue(self, queue_name: str, durable: bool = True) -> None:
        """声明队列"""
        self.channel.queue_declare(queue=queue_name, durable=durable)

    def declare_exchange(self, exchange_name: str, exchange_type: str = "direct",
                         durable: bool = True) -> None:
        """声明交换机"""
        self.channel.exchange_declare(
            exchange=exchange_name, exchange_type=exchange_type, durable=durable
        )

    def bind_queue(self, queue_name: str, exchange_name: str,
                   routing_key: str = "") -> None:
        """绑定队列到交换机"""
        self.channel.queue_bind(
            queue=queue_name, exchange=exchange_name, routing_key=routing_key
        )

    def publish(self, exchange: str, routing_key: str, message: Any,
                properties: Optional[pika.BasicProperties] = None) -> None:
        """发布消息"""
        if isinstance(message, (dict, list)):
            message = json.dumps(message, ensure_ascii=False)
        self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=message.encode("utf-8"),
            properties=properties or pika.BasicProperties(
                delivery_mode=2,  # 消息持久化
                content_type="application/json",
            ),
        )
        logger.debug(f"消息已发布: {exchange} -> {routing_key}")

    def consume(self, queue_name: str, callback: Callable,
                auto_ack: bool = False) -> None:
        """消费消息"""
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=auto_ack,
        )
        logger.info(f"开始消费队列: {queue_name}")
        self.channel.start_consuming()

    def close(self):
        """关闭连接"""
        if self._channel and self._channel.is_open:
            self._channel.close()
        if self._connection and self._connection.is_open:
            self._connection.close()
        self._channel = None
        self._connection = None
