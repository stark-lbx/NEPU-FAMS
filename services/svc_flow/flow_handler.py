import grpc
from proto.generated import flow_pb2, flow_pb2_grpc
from data.logic.flow_logic import FlowLogic
from common.mq import MqProducer
from common.utils import safe_error_msg
from common.oper_log import oper_log

class FlowServiceHandler(flow_pb2_grpc.FlowServiceServicer):
    def __init__(self, flow_logic: FlowLogic, mq_producer: MqProducer = None):
        self.flow_logic = flow_logic
        self.mq_producer = mq_producer

    def CreateBorrow(self, request, context):
        try:
            borrow_data = {
                "asset_biz_id": request.asset_biz_id,
                "borrow_user_biz_id": request.borrow_user_biz_id,
                "borrow_start_time": request.borrow_start_time,
                "borrow_end_time": request.borrow_end_time,
                "borrow_desc": request.borrow_desc
            }
            flow_id, biz_id = self.flow_logic.create_borrow_apply(borrow_data)
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": "borrow_list:*"})
            return flow_pb2.FlowResponse(flow_biz_id=flow_id, business_biz_id=biz_id)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return flow_pb2.FlowResponse()

    def CreateRepair(self, request, context):
        try:
            repair_data = {
                "asset_biz_id": request.asset_biz_id,
                "report_user_biz_id": request.report_user_biz_id,
                "fault_desc": request.fault_desc
            }
            flow_id, biz_id = self.flow_logic.create_repair_apply(repair_data)
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": "repair_list:*"})
            return flow_pb2.FlowResponse(flow_biz_id=flow_id, business_biz_id=biz_id)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return flow_pb2.FlowResponse()

    def CreateScrap(self, request, context):
        try:
            scrap_data = {
                "asset_biz_id": request.asset_biz_id,
                "apply_user_biz_id": request.apply_user_biz_id,
                "scrap_reason": request.scrap_reason
            }
            flow_id, biz_id = self.flow_logic.create_scrap_apply(scrap_data)
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": "scrap_list:*"})
            return flow_pb2.FlowResponse(flow_biz_id=flow_id, business_biz_id=biz_id)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return flow_pb2.FlowResponse()

    def DeptAudit(self, request, context):
        try:
            self.flow_logic.dept_audit(request.flow_biz_id, request.audit_user_biz_id, request.result)
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": "*_list:*"})
            return flow_pb2.CommonResponse(success=True, msg="审核完成")
        except Exception as e:
            return flow_pb2.CommonResponse(success=False, msg=safe_error_msg(e))

    def SchoolAudit(self, request, context):
        try:
            self.flow_logic.school_audit(request.flow_biz_id, request.audit_user_biz_id, request.result)
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": "*_list:*"})
            return flow_pb2.CommonResponse(success=True, msg="审核完成")
        except Exception as e:
            return flow_pb2.CommonResponse(success=False, msg=safe_error_msg(e))

    def GetBorrowList(self, request, context):
        data = self.flow_logic.list_borrow(request.user_biz_id, request.dept_biz_id)
        borrow_list = [flow_pb2.BorrowInfo(**d) for d in data]
        return flow_pb2.BorrowListResponse(list=borrow_list, total=len(data))

    def GetRepairList(self, request, context):
        data = self.flow_logic.list_repair(request.user_biz_id, request.dept_biz_id)
        repair_list = [flow_pb2.RepairInfo(**d) for d in data]
        return flow_pb2.RepairListResponse(list=repair_list, total=len(data))

    def GetScrapList(self, request, context):
        data = self.flow_logic.list_scrap(request.user_biz_id, request.dept_biz_id)
        scrap_list = [flow_pb2.ScrapInfo(**d) for d in data]
        return flow_pb2.ScrapListResponse(list=scrap_list, total=len(data))

    def ReturnAsset(self, request, context):
        try:
            self.flow_logic.return_asset(request.borrow_biz_id, request.oper_user_biz_id)
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": "borrow_list:*"})
                self.mq_producer.publish_delayed({"cache_pattern": "asset:*"})
            return flow_pb2.CommonResponse(success=True, msg="归还成功")
        except Exception as e:
            return flow_pb2.CommonResponse(success=False, msg=safe_error_msg(e))