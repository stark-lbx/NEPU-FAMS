import grpc
import redis
import json
from proto.generated import asset_pb2, asset_pb2_grpc
from data.logic.asset_logic import AssetLogic
from data.logic.check_logic import CheckLogic
from common.mq import MqProducer
from common.utils import safe_error_msg
from common.oper_log import oper_log
from data.basic.asset_dao import AssetStatusLogDao


class AssetServiceHandler(asset_pb2_grpc.AssetServiceServicer):
    def __init__(self, asset_logic: AssetLogic, check_logic: CheckLogic,
                 redis_client: redis.Redis, mq_producer: MqProducer = None):
        self.asset_logic = asset_logic
        self.check_logic = check_logic
        self.redis = redis_client
        self.mq_producer = mq_producer

    def CreateAsset(self, request, context):
        try:
            asset_data = {
                "asset_code": request.asset_code,
                "asset_name": request.asset_name,
                "asset_type_code": request.asset_type_code,
                "buy_time": request.buy_time,
                "asset_price": request.asset_price,
                "store_location": request.store_location,
                "dept_biz_id": request.dept_biz_id,
                "current_status_code": request.current_status_code,
                "use_user_biz_id": request.use_user_biz_id,
                "supplier": request.supplier,
                "spec": request.spec,
                "remark": request.remark,
                "create_user_biz_id": request.create_user_biz_id
            }
            biz_id = self.asset_logic.create_asset(asset_data)
            # 延迟清理部门资产列表缓存
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": f"asset_list:{request.dept_biz_id}"})
            return asset_pb2.CreateAssetResponse(biz_id=biz_id)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return asset_pb2.CreateAssetResponse()

    def GetAssetByBizId(self, request, context):
        cache_key = f"asset:{request.biz_id}"
        cache = self.redis.get(cache_key)
        if cache:
            asset = json.loads(cache)
        else:
            asset = self.asset_logic.get_asset(request.biz_id)
            if asset:
                self.redis.setex(cache_key, 1800, json.dumps(asset))

        if not asset:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("资产不存在")
            return asset_pb2.AssetResponse()

        asset_fields = {f.name for f in asset_pb2.AssetInfo.DESCRIPTOR.fields}
        return asset_pb2.AssetResponse(asset=asset_pb2.AssetInfo(**{k: asset[k] for k in asset_fields if k in asset}))

    def ListAssetByDept(self, request, context):
        data, total = self.asset_logic.list_asset(
            request.dept_biz_id, request.status_code, request.page, request.page_size
        )
        asset_fields = {f.name for f in asset_pb2.AssetInfo.DESCRIPTOR.fields}
        asset_list = [asset_pb2.AssetInfo(**{k: a[k] for k in asset_fields if k in a}) for a in data]
        return asset_pb2.AssetListResponse(list=asset_list, total=total)

    def UpdateAssetStatus(self, request, context):
        try:
            self.asset_logic.update_status(
                request.asset_biz_id, request.new_status_code,
                request.oper_user_biz_id, request.oper_desc
            )
            # 延迟清理资产详情和列表缓存
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_key": f"asset:{request.asset_biz_id}"})
                self.mq_producer.publish_delayed({"cache_pattern": "asset_list:*"})
            return asset_pb2.CommonResponse(success=True, msg="状态更新成功")
        except Exception as e:
            return asset_pb2.CommonResponse(success=False, msg=safe_error_msg(e))

    def GetStatusLogList(self, request, context):
        """查询资产状态变更流水"""
        log_dao = AssetStatusLogDao(db_path=self.asset_logic.asset_dao.db_path)
        logs = log_dao.list_by_asset(request.asset_biz_id)
        log_list = [asset_pb2.StatusLogInfo(**log) for log in logs]
        return asset_pb2.StatusLogListResponse(list=log_list, total=len(logs))

    def CreateCheckTask(self, request, context):
        try:
            task_data = {
                "task_name": request.task_name,
                "target_dept_biz_id": request.target_dept_biz_id,
                "start_time": request.start_time,
                "end_time": request.end_time,
                "create_user_biz_id": request.create_user_biz_id
            }
            task_id = self.check_logic.create_task(task_data)
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": "check_task:*"})
            return asset_pb2.TaskResponse(task_biz_id=task_id)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return asset_pb2.TaskResponse()

    def SubmitCheckDetail(self, request, context):
        try:
            detail_data = {
                "task_biz_id": request.task_biz_id,
                "asset_biz_id": request.asset_biz_id,
                "check_user_biz_id": request.check_user_biz_id,
                "actual_exist": request.actual_exist,
                "real_location": request.real_location,
                "check_remark": request.check_remark
            }
            self.check_logic.submit_detail(detail_data)
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": f"check_detail:{request.task_biz_id}"})
            return asset_pb2.CommonResponse(success=True, msg="盘点提交成功")
        except Exception as e:
            return asset_pb2.CommonResponse(success=False, msg=safe_error_msg(e))

    def ListCheckTask(self, request, context):
        tasks = self.check_logic.list_task_by_dept(request.dept_biz_id)
        task_list = [asset_pb2.CheckTaskInfo(**t) for t in tasks]
        return asset_pb2.TaskListResponse(list=task_list, total=len(tasks))

    def GetCheckDetailList(self, request, context):
        """查询盘点任务明细列表"""
        details = self.check_logic.get_task_detail(request.task_biz_id)
        detail_list = [asset_pb2.CheckDetailInfo(**d) for d in details]
        return asset_pb2.CheckDetailListResponse(list=detail_list, total=len(details))