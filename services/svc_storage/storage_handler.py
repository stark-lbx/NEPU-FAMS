import grpc
from proto.generated import storage_pb2, storage_pb2_grpc
from data.logic.storage_logic import StorageLogic
from common.utils import safe_error_msg
from common.mq import MqProducer

class StorageServiceHandler(storage_pb2_grpc.StorageServiceServicer):
    def __init__(self, storage_logic: StorageLogic, delete_file_producer: MqProducer = None):
        self.storage_logic = storage_logic
        self.delete_file_producer = delete_file_producer

    def UploadAttach(self, request, context):
        try:
            biz_id, file_path = self.storage_logic.upload_attach(
                request.asset_biz_id, request.attach_name,
                request.file_data, request.attach_type,
                request.upload_user_biz_id
            )
            return storage_pb2.UploadResponse(attach_biz_id=biz_id, file_path=file_path)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return storage_pb2.UploadResponse()

    def GetAttachList(self, request, context):
        data = self.storage_logic.list_attach(request.asset_biz_id)
        attach_list = [storage_pb2.AttachInfo(**d) for d in data]
        return storage_pb2.AttachListResponse(list=attach_list, total=len(data))

    def DeleteAttach(self, request, context):
        """删除附件：发送异步消息，由消费者执行物理删除"""
        try:
            if self.delete_file_producer:
                self.delete_file_producer.publish({"attach_biz_id": request.attach_biz_id})
            return storage_pb2.CommonResponse(success=True, msg="删除指令已提交，后台处理中")
        except Exception as e:
            return storage_pb2.CommonResponse(success=False, msg=safe_error_msg(e))

    def GetDownloadUrl(self, request, context):
        try:
            path = self.storage_logic.get_file_path(request.attach_biz_id)
            return storage_pb2.UrlResponse(download_url=path)
        except Exception as e:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(safe_error_msg(e))
            return storage_pb2.UrlResponse()