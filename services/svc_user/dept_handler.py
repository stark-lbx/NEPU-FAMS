import grpc
from proto.generated import user_pb2, user_pb2_grpc
from data.logic.dept_logic import DeptLogic
from common.mq import MqProducer
from common.utils import safe_error_msg
from common.oper_log import oper_log


class DeptServiceHandler(user_pb2_grpc.DeptServiceServicer):
    def __init__(self, dept_logic: DeptLogic, mq_producer: MqProducer = None):
        self.dept_logic = dept_logic
        self.mq_producer = mq_producer

    def GetDeptTree(self, request, context):
        try:
            tree_data = self.dept_logic.get_dept_tree()
            dept_list = [self._build_dept_info(d) for d in tree_data]
            return user_pb2.DeptTreeResponse(list=dept_list)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return user_pb2.DeptTreeResponse()

    def _build_dept_info(self, dept: dict):
        children = [self._build_dept_info(c) for c in dept.get("children", [])]
        return user_pb2.DeptInfo(
            biz_id=dept["biz_id"],
            dept_name=dept["dept_name"],
            parent_biz_id=dept["parent_biz_id"],
            dept_sort=dept["dept_sort"],
            children=children
        )

    def CreateDept(self, request, context):
        try:
            dept_data = {
                "dept_name": request.dept_name,
                "parent_biz_id": request.parent_biz_id,
                "dept_sort": request.dept_sort
            }
            biz_id = self.dept_logic.create_dept(dept_data)
            oper_log(request.create_user_biz_id if hasattr(request, 'create_user_biz_id') else "",
                     "部门管理", "新增", f"创建部门 {request.dept_name}")
            if self.mq_producer:
                self.mq_producer.publish_delayed({"cache_pattern": "dept:*"})
            return user_pb2.CreateDeptResponse(biz_id=biz_id)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(safe_error_msg(e))
            return user_pb2.CreateDeptResponse()

    def UpdateDept(self, request, context):
        try:
            update_data = {
                "dept_name": request.dept_name,
                "dept_sort": request.dept_sort
            }
            success = self.dept_logic.update_dept(request.biz_id, update_data)
            if self.mq_producer and success:
                self.mq_producer.publish_delayed({"cache_pattern": "dept:*"})
            return user_pb2.CommonResponse(success=success,
                                           msg="更新成功" if success else "更新失败")
        except Exception as e:
            return user_pb2.CommonResponse(success=False, msg=safe_error_msg(e))

    def DeleteDept(self, request, context):
        try:
            success = self.dept_logic.delete_dept(request.biz_id)
            if self.mq_producer and success:
                self.mq_producer.publish_delayed({"cache_pattern": "dept:*"})
            return user_pb2.CommonResponse(success=success,
                                           msg="删除成功" if success else "删除失败")
        except Exception as e:
            return user_pb2.CommonResponse(success=False, msg=safe_error_msg(e))
