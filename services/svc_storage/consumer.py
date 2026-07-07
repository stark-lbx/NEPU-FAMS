from data.logic.storage_logic import StorageLogic
from common.mq import MqConsumer
from common.config import QueueSettings
from common.log import get_logger

logger = get_logger("storage_consumer")


class StorageMqConsumer:
    def __init__(self, mq_url: str, delete_file_queue: QueueSettings, storage_logic: StorageLogic):
        self.storage_logic = storage_logic
        self.consumer = MqConsumer(mq_url, delete_file_queue, self._handle_delete_file)

    def _handle_delete_file(self, data: dict):
        """处理删除文件消息"""
        attach_biz_id = data.get("attach_biz_id", "")
        if not attach_biz_id:
            return

        try:
            self.storage_logic.delete_attach(attach_biz_id)
            logger.info(f"异步删除附件成功: {attach_biz_id}")
        except Exception as e:
            logger.error(f"异步删除附件失败: {attach_biz_id}, {e}")

    def start(self):
        self.consumer.start()
        logger.info("存储服务MQ消费者启动成功")