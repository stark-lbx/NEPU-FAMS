import grpc
from concurrent import futures
import etcd3
from data.logic.storage_logic import StorageLogic
from services.svc_storage.storage_handler import StorageServiceHandler
from services.svc_storage.consumer import StorageMqConsumer
from proto.generated import storage_pb2_grpc
from common.log import init_log, get_logger
from common.config import LogSettings, DbSettings, EtcdSettings, FdfsSettings, MqSettings, QueueSettings
from common.constants import QUEUE_DELETE_FILE
from common.mq import MqProducer

logger = get_logger("storage_server")

class StorageServerBuilder:
    def __init__(self):
        self._listen_port = 9994
        self._log_settings: LogSettings = None
        self._db_settings: DbSettings = None
        self._etcd_settings: EtcdSettings = None
        self._fdfs_settings: FdfsSettings = None
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

    def with_etcd_settings(self, settings: EtcdSettings):
        self._etcd_settings = settings
        return self

    def with_fdfs_settings(self, settings: FdfsSettings):
        self._fdfs_settings = settings
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
        logger.info("初始化日志完成")

        storage_logic = StorageLogic(db_path=self._db_settings.db_path)
        logger.info("初始化存储逻辑完成")

        # 初始化删除文件MQ生产者
        delete_file_queue = QueueSettings(**QUEUE_DELETE_FILE)
        delete_file_producer = MqProducer(self._mq_settings.mq_url, delete_file_queue)
        logger.info("初始化MQ生产者完成")

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
        handler = StorageServiceHandler(storage_logic, delete_file_producer)
        storage_pb2_grpc.add_StorageServiceServicer_to_server(handler, server)
        server.add_insecure_port(f"[::]:{self._listen_port}")

        etcd_host, etcd_port = self._etcd_settings.registry_center_addr.replace("http://", "").split(":")
        etcd_client = etcd3.client(host=etcd_host, port=int(etcd_port))
        etcd_client.put(f"/services/{self._etcd_settings.service_name}", self._etcd_settings.service_addr)
        logger.info(f"服务注册成功: {self._etcd_settings.service_name}")

        # 启动MQ消费者
        consumer = StorageMqConsumer(self._mq_settings.mq_url, delete_file_queue, storage_logic)
        consumer.start()
        logger.info("初始化MQ消费者完成")

        return server