import pika
import json
import threading
from typing import Callable
from common.config import QueueSettings
from common.constants import DLX_EXCHANGE, DLX_EXCHANGE_TYPE, MAX_RETRY_COUNT, RETRY_DELAY_SECONDS
from common.log import get_logger

logger = get_logger("mq")


class MqConnectionManager:
    """RabbitMQ连接管理器，单例"""
    _instance = None

    def __new__(cls, mq_url: str):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.mq_url = mq_url
            cls._instance.connection = None
        return cls._instance

    def get_connection(self) -> pika.BlockingConnection:
        if not self.connection or self.connection.is_closed:
            parameters = pika.URLParameters(self.mq_url)
            self.connection = pika.BlockingConnection(parameters)
        return self.connection

    def close(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()


class MqProducer:
    """消息生产者，支持普通消息、延迟消息、死信绑定"""

    def __init__(self, mq_url: str, queue_settings: QueueSettings):
        self.conn_mgr = MqConnectionManager(mq_url)
        self.settings = queue_settings
        self._init_exchange_queue()

    def _init_exchange_queue(self):
        """初始化交换机、队列、绑定关系，自动绑定死信交换机"""
        conn = self.conn_mgr.get_connection()
        channel = conn.channel()

        # 声明死信交换机（全局共用）
        channel.exchange_declare(
            exchange=DLX_EXCHANGE,
            exchange_type=DLX_EXCHANGE_TYPE,
            durable=True
        )

        # 声明业务交换机
        if self.settings.type == "delayed":
            args = {"x-delayed-type": "direct"}
            channel.exchange_declare(
                exchange=self.settings.exchange,
                exchange_type="x-delayed-message",
                durable=True,
                arguments=args
            )
        else:
            channel.exchange_declare(
                exchange=self.settings.exchange,
                exchange_type=self.settings.type,
                durable=True
            )

        # 队列参数：绑定死信交换机和死信路由键
        queue_args = {
            "x-dead-letter-exchange": DLX_EXCHANGE,
            "x-dead-letter-routing-key": f"dlx.{self.settings.queue}"
        }

        # 声明业务队列
        channel.queue_declare(
            queue=self.settings.queue,
            durable=True,
            arguments=queue_args
        )

        # 绑定业务队列到业务交换机
        channel.queue_bind(
            queue=self.settings.queue,
            exchange=self.settings.exchange,
            routing_key=self.settings.binding_key
        )

        # 声明死信队列
        dlx_queue_name = f"dlx.{self.settings.queue}"
        channel.queue_declare(queue=dlx_queue_name, durable=True)
        channel.queue_bind(
            queue=dlx_queue_name,
            exchange=DLX_EXCHANGE,
            routing_key=f"dlx.{self.settings.queue}"
        )

        channel.close()

    def publish(self, data: dict, headers: dict = None):
        """发送普通消息"""
        try:
            conn = self.conn_mgr.get_connection()
            channel = conn.channel()
            props = pika.BasicProperties(
                delivery_mode=2,
                headers=headers or {}
            )
            channel.basic_publish(
                exchange=self.settings.exchange,
                routing_key=self.settings.binding_key,
                body=json.dumps(data, ensure_ascii=False),
                properties=props
            )
            logger.debug(f"发送消息到队列 {self.settings.queue}: {data}")
            channel.close()
        except Exception as e:
            logger.warning(f"MQ消息发送失败（不影响业务）: {e}")

    def publish_delayed(self, data: dict, delay_seconds: int = None, headers: dict = None):
        """发送延迟消息"""
        if self.settings.type != "delayed":
            raise Exception("非延迟队列不可发送延迟消息")

        try:
            delay = delay_seconds or self.settings.delayed_ttl
            conn = self.conn_mgr.get_connection()
            channel = conn.channel()

            msg_headers = headers or {}
            msg_headers["x-delay"] = delay * 1000  # 毫秒
            props = pika.BasicProperties(
                delivery_mode=2,
                headers=msg_headers
            )
            channel.basic_publish(
                exchange=self.settings.exchange,
                routing_key=self.settings.binding_key,
                body=json.dumps(data, ensure_ascii=False),
                properties=props
            )
            logger.debug(f"发送延迟消息 {delay}s 到队列 {self.settings.queue}: {data}")
            channel.close()
        except Exception as e:
            logger.warning(f"MQ延迟消息发送失败（不影响业务）: {e}")


class MqConsumer:
    """消息消费者，支持自动重试、死信兜底、异步线程消费"""

    def __init__(self, mq_url: str, queue_settings: QueueSettings, callback: Callable):
        self.conn_mgr = MqConnectionManager(mq_url)
        self.settings = queue_settings
        self.callback = callback
        self._thread = None
        self._running = False
        # 绑定同一个队列的生产者，用于重试补发
        self._retry_producer = MqProducer(mq_url, queue_settings)

    def _consume(self):
        """消费主循环"""
        conn = self.conn_mgr.get_connection()
        channel = conn.channel()
        channel.basic_qos(prefetch_count=1)

        def on_message(ch, method, properties, body):
            try:
                data = json.loads(body.decode('utf-8'))
                # 执行业务回调
                self.callback(data)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"消息消费失败: {e}, 队列: {self.settings.queue}")
                # 获取当前重试次数
                retry_count = 0
                if properties.headers and "retry_count" in properties.headers:
                    retry_count = properties.headers["retry_count"]

                if retry_count < MAX_RETRY_COUNT:
                    # 未达最大重试次数，延迟重试
                    new_headers = {"retry_count": retry_count + 1}
                    try:
                        self._retry_producer.publish_delayed(
                            json.loads(body.decode('utf-8')),
                            delay_seconds=RETRY_DELAY_SECONDS,
                            headers=new_headers
                        )
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        logger.info(f"消息第 {retry_count + 1} 次重试，队列: {self.settings.queue}")
                    except Exception as retry_e:
                        logger.error(f"重试消息发送失败: {retry_e}")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                else:
                    # 超过最大重试次数，进入死信队列
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    logger.error(f"消息达到最大重试次数，进入死信队列: {self.settings.queue}")

        channel.basic_consume(queue=self.settings.queue, on_message_callback=on_message)
        logger.info(f"开始监听队列: {self.settings.queue}")
        channel.start_consuming()

    def start(self):
        """启动消费线程"""
        self._running = True
        self._thread = threading.Thread(target=self._consume, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self.conn_mgr.close()