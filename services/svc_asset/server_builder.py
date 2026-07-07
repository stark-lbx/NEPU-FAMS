import grpc
from concurrent import futures
import redis
import etcd3
from data.logic.asset_logic import AssetLogic
from data.logic.check_logic import CheckLogic
from services.svc_asset.asset_handler import AssetServiceHandler
from services.svc_asset.consumer import AssetMqConsumer
from proto.generated import asset_pb2_grpc
from common.log import init_log, get_logger
from common.config import LogSettings, DbSettings, RedisSettings, EtcdSettings, MqSettings, QueueSettings
from common.constants import QUEUE_DELETE_CACHE_ASSET
from common.mq import MqProducer

logger = get_logger("asset_server")

class AssetServerBuilder:
    def __init__(self):
        self._listen_port = 9992
        self._log_settings: LogSettings = None
        self._db_settings: DbSettings = None
        self._redis_settings: RedisSettings = None
        self._etcd_settings: EtcdSettings = None
        self._mq_settings: MqSettings = None

    def with_listen_port(self, port: int):
        self._listen_port = port
        return self

    def with_log_settings(self, settings: LogSettings):
        self._log_settings = settings
        return self

    def with_db_settings(self, settings: DbSettings):
        self._db_settings = settings
        return self

    def with_redis_settings(self, settings: RedisSettings):
        self._redis_settings = settings
        return self

    def with_etcd_settings(self, settings: EtcdSettings):
        self._etcd_settings = settings
        return self

    def with_mq_settings(self, settings: MqSettings):
        self._mq_settings = settings
        return self

    def build(self):
        init_log(
            level=self._log_settings.level,
            async_log=self._log_settings.async_log,
            path=self._log_settings.path,
            fmt=self._log_settings.format
        )
        logger.info("初始化日志模块完成")

        redis_pool = redis.ConnectionPool(
            host=self._redis_settings.host, port=self._redis_settings.port,
            password=self._redis_settings.password,
            max_connections=self._redis_settings.connection_pool_size
        )
        redis_client = redis.Redis(connection_pool=redis_pool)
        logger.info("初始化Redis完成")

        # 初始化MQ生产者
        cache_queue = QueueSettings(**QUEUE_DELETE_CACHE_ASSET)
        mq_producer = MqProducer(self._mq_settings.mq_url, cache_queue)
        logger.info("初始化MQ生产者完成")

        asset_logic = AssetLogic(db_path=self._db_settings.db_path)
        check_logic = CheckLogic(db_path=self._db_settings.db_path)
        logger.info("初始化业务逻辑层完成")

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
        handler = AssetServiceHandler(asset_logic, check_logic, redis_client, mq_producer)
        asset_pb2_grpc.add_AssetServiceServicer_to_server(handler, server)
        server.add_insecure_port(f"[::]:{self._listen_port}")
        logger.info(f"初始化gRPC服务完成，端口: {self._listen_port}")

        etcd_host, etcd_port = self._etcd_settings.registry_center_addr.replace("http://", "").split(":")
        etcd_client = etcd3.client(host=etcd_host, port=int(etcd_port))
        etcd_client.put(f"/services/{self._etcd_settings.service_name}", self._etcd_settings.service_addr)
        logger.info(f"服务注册etcd成功: {self._etcd_settings.service_name}")

        # 启动MQ消费者
        consumer = AssetMqConsumer(self._mq_settings.mq_url, cache_queue, redis_client)
        consumer.start()
        logger.info("初始化MQ消费者完成")

        return server