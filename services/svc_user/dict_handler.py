import grpc
import redis
import json
from proto.generated import user_pb2, user_pb2_grpc
from data.logic.dict_logic import DictLogic
from common.mq import MqProducer
from common.utils import safe_error_msg

class DictServiceHandler(user_pb2_grpc.DictServiceServicer):
    def __init__(self, dict_logic: DictLogic, redis_client: redis.Redis, mq_producer: MqProducer = None):
        self.dict_logic = dict_logic
        self.redis = redis_client
        self.mq_producer = mq_producer

    def ListDictByType(self, request, context):
        cache_key = f"dict:{request.dict_type}"
        cache = self.redis.get(cache_key)
        if cache:
            dict_list = json.loads(cache)
        else:
            dict_list = self.dict_logic.list_by_type(request.dict_type)
            self.redis.setex(cache_key, 3600, json.dumps(dict_list))

        info_list = [user_pb2.DictInfo(**{k: d[k] for k in user_pb2.DictInfo.DESCRIPTOR.fields_by_name if k in d}) for d in dict_list]
        return user_pb2.DictListResponse(list=info_list, total=len(info_list))

    def ListDictTypes(self, request, context):
        cache_key = "dict:types"
        cache = self.redis.get(cache_key)
        if cache:
            types = json.loads(cache)
        else:
            types = self.dict_logic.list_types()
            self.redis.setex(cache_key, 3600, json.dumps(types))
        return user_pb2.DictTypesResponse(dict_types=types)

    def CreateDict(self, request, context):
        try:
            dict_data = {
                "dict_type": request.dict_type,
                "dict_code": request.dict_code,
                "dict_name": request.dict_name,
                "sort": request.sort
            }
            biz_id = self.dict_logic.create_dict(dict_data)
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": "dict:*"})
            return user_pb2.CreateDictResponse(biz_id=biz_id)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return user_pb2.CreateDictResponse()

    def UpdateDict(self, request, context):
        try:
            update_data = {
                "dict_name": request.dict_name,
                "sort": request.sort
            }
            success = self.dict_logic.update_dict(request.biz_id, update_data)
            if self.mq_producer and success:
                self.mq_producer.publish_delayed({"cache_pattern": "dict:*"})
            return user_pb2.CommonResponse(success=success, msg="更新成功" if success else "更新失败")
        except Exception as e:
            return user_pb2.CommonResponse(success=False, msg=safe_error_msg(e))

    def DeleteDict(self, request, context):
        try:
            success = self.dict_logic.delete_dict(request.biz_id)
            if self.mq_producer and success:
                self.mq_producer.publish_delayed({"cache_pattern": "dict:*"})
            return user_pb2.CommonResponse(success=success, msg="删除成功" if success else "删除失败")
        except Exception as e:
            return user_pb2.CommonResponse(success=False, msg=safe_error_msg(e))