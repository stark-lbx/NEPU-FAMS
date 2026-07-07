INSERT INTO sys_role (biz_id, role_name, role_code, role_desc) VALUES
('ROLE001', '校级管理员', 'school_admin', '全校系统最高权限，可管理所有部门、用户、资产、系统配置'),
('ROLE002', '院系管理员', 'dept_admin', '本院系范围内的用户、资产、审批流程管理权限'),
('ROLE003', '教师', 'teacher', '个人资产申报、借用、报修，查看本院系资产台账'),
('ROLE004', '学生', 'student', '资产借用申请、个人借用记录查询');