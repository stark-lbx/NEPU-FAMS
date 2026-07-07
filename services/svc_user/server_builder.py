import grpc
from concurrent import futures
import redis
import etcd3
from data.logic.user_logic import UserLogic
from data.logic.role_logic import RoleLogic
from data.logic.dept_logic import DeptLogic
from data.logic.dict_logic import DictLogic
from services.svc_user.user_handler import UserServiceHandler
from services.svc_user.dept_handler import DeptServiceHandler
from services.svc_user.dict_handler import DictServiceHandler
from services.svc_user.consumer import UserMqConsumer
from proto.generated import user_pb2_grpc
from common.log import init_log, get_logger
from common.config import LogSettings, DbSettings, RedisSettings, EtcdSettings, MqSettings, QueueSettings
from common.constants import QUEUE_DELETE_CACHE_USER
from common.mq import MqProducer

logger = get_logger("user_server")


class UserServerBuilder:
    def __init__(self):
        self._listen_port = 9991
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
        # 1. 初始化日志
        init_log(
            level=self._log_settings.level,
            async_log=self._log_settings.async_log,
            path=self._log_settings.path,
            fmt=self._log_settings.format
        )
        logger.info("初始化日志模块完成")

        # 2. 初始化Redis连接池
        redis_pool = redis.ConnectionPool(
            host=self._redis_settings.host,
            port=self._redis_settings.port,
            password=self._redis_settings.password,
            max_connections=self._redis_settings.connection_pool_size
        )
        redis_client = redis.Redis(connection_pool=redis_pool)
        logger.info("初始化Redis连接池完成")

        # 3. 初始化MQ生产者
        cache_queue = QueueSettings(**QUEUE_DELETE_CACHE_USER)
        mq_producer = MqProducer(self._mq_settings.mq_url, cache_queue)
        logger.info("初始化MQ生产者完成")

        # 4. 初始化业务逻辑层
        user_logic = UserLogic(db_path=self._db_settings.db_path)
        role_logic = RoleLogic(db_path=self._db_settings.db_path)
        dept_logic = DeptLogic(db_path=self._db_settings.db_path)
        dict_logic = DictLogic(db_path=self._db_settings.db_path)
        logger.info("初始化业务逻辑层完成")

        # 5. 初始化gRPC服务
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))

        # 注册用户服务
        user_handler = UserServiceHandler(user_logic, role_logic, redis_client, mq_producer)
        user_pb2_grpc.add_UserServiceServicer_to_server(user_handler, server)

        # 注册部门服务
        dept_handler = DeptServiceHandler(dept_logic, mq_producer)
        user_pb2_grpc.add_DeptServiceServicer_to_server(dept_handler, server)

        # 注册字典服务
        dict_handler = DictServiceHandler(dict_logic, redis_client, mq_producer)
        user_pb2_grpc.add_DictServiceServicer_to_server(dict_handler, server)

        server.add_insecure_port(f"[::]:{self._listen_port}")
        logger.info(f"初始化gRPC服务完成，监听端口: {self._listen_port}")

        # 6. 服务注册到etcd
        etcd_host, etcd_port = self._etcd_settings.registry_center_addr.replace("http://", "").split(":")
        etcd_client = etcd3.client(host=etcd_host, port=int(etcd_port))
        etcd_client.put(f"/services/{self._etcd_settings.service_name}", self._etcd_settings.service_addr)
        logger.info(f"服务注册到etcd成功: {self._etcd_settings.service_name} -> {self._etcd_settings.service_addr}")

        # 7. 启动MQ消费者
        consumer = UserMqConsumer(self._mq_settings.mq_url, cache_queue, redis_client)
        consumer.start()
        logger.info("初始化MQ消费者完成")

        return server