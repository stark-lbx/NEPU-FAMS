-- 用户状态
INSERT INTO sys_dict (biz_id, dict_type, dict_code, dict_name, sort) VALUES
('DICT0001', 'sys_user_status', '1', '正常', 1),
('DICT0002', 'sys_user_status', '0', '停用', 2);

-- 部门类型
INSERT INTO sys_dict (biz_id, dict_type, dict_code, dict_name, sort) VALUES
('DICT0003', 'sys_dept_type', '1', '党政管理部门', 1),
('DICT0004', 'sys_dept_type', '2', '教学学院', 2),
('DICT0005', 'sys_dept_type', '3', '科研机构', 3),
('DICT0006', 'sys_dept_type', '4', '教辅直属单位', 4);

-- 性别
INSERT INTO sys_dict (biz_id, dict_type, dict_code, dict_name, sort) VALUES
('DICT0007', 'sys_gender', '1', '男', 1),
('DICT0008', 'sys_gender', '2', '女', 2),
('DICT0009', 'sys_gender', '0', '未知', 3);

-- 学历
INSERT INTO sys_dict (biz_id, dict_type, dict_code, dict_name, sort) VALUES
('DICT0010', 'sys_education', '1', '博士', 1),
('DICT0011', 'sys_education', '2', '硕士', 2),
('DICT0012', 'sys_education', '3', '本科', 3),
('DICT0013', 'sys_education', '4', '专科', 4);

-- 资产状态
INSERT INTO sys_dict (biz_id, dict_type, dict_code, dict_name, sort) VALUES
('DICT0014', 'asset_status', '1', '在用', 1),
('DICT0015', 'asset_status', '2', '闲置', 2),
('DICT0016', 'asset_status', '3', '借出', 3),
('DICT0017', 'asset_status', '4', '维修中', 4),
('DICT0018', 'asset_status', '5', '已报废', 5);

-- 资产分类
INSERT INTO sys_dict (biz_id, dict_type, dict_code, dict_name, sort) VALUES
('DICT0019', 'asset_category', '1', '计算机设备', 1),
('DICT0020', 'asset_category', '2', '办公设备', 2),
('DICT0021', 'asset_category', '3', '教学仪器', 3),
('DICT0022', 'asset_category', '4', '科研设备', 4),
('DICT0023', 'asset_category', '5', '家具用具', 5),
('DICT0024', 'asset_category', '6', '车辆设备', 6);

-- 审批流程状态
INSERT INTO sys_dict (biz_id, dict_type, dict_code, dict_name, sort) VALUES
('DICT0025', 'flow_status', 'WAIT', '待审批', 1),
('DICT0026', 'flow_status', 'APPROVED', '已通过', 2),
('DICT0027', 'flow_status', 'REJECTED', '已驳回', 3),
('DICT0028', 'flow_status', 'PROCESSING', '处理中', 4),
('DICT0029', 'flow_status', 'FINISHED', '已完成', 5);

-- 资产使用方向
INSERT INTO sys_dict (biz_id, dict_type, dict_code, dict_name, sort) VALUES
('DICT0030', 'asset_use_type', '1', '教学使用', 1),
('DICT0031', 'asset_use_type', '2', '科研使用', 2),
('DICT0032', 'asset_use_type', '3', '行政办公', 3),
('DICT0033', 'asset_use_type', '4', '公共服务', 4);

-- 盘点任务状态
INSERT INTO sys_dict (biz_id, dict_type, dict_code, dict_name, sort) VALUES
('DICT0034', 'check_task_status', 'WAIT', '待开始', 1),
('DICT0035', 'check_task_status', 'RUNNING', '进行中', 2),
('DICT0036', 'check_task_status', 'FINISHED', '已完成', 3);