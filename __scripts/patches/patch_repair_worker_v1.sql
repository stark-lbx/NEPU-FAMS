-- ==========================================
-- 补丁：新增修理工角色 + 扩展报修流程状态
-- ==========================================

-- 1. 新增修理工角色
INSERT OR IGNORE INTO sys_role (biz_id, role_name, role_code, role_desc)
VALUES ('ROLE005', '修理工', 'repair_worker', '接收报修派单、维修资产并提交维修结果');

-- 2. 新增修理工权限
INSERT OR IGNORE INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id)
VALUES ('PERM030204', '我的工单', 'GET:/api/flow/repair/my-tasks', 2, 'PERM0302');

INSERT OR IGNORE INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id)
VALUES ('PERM030205', '接单', 'POST:/api/flow/repair/accept', 2, 'PERM0302');

INSERT OR IGNORE INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id)
VALUES ('PERM030206', '完工', 'POST:/api/flow/repair/complete', 2, 'PERM0302');

-- 3. 修理工角色权限关联
INSERT OR IGNORE INTO sys_role_permission (role_biz_id, perm_biz_id)
VALUES ('ROLE005', 'PERM030204');

INSERT OR IGNORE INTO sys_role_permission (role_biz_id, perm_biz_id)
VALUES ('ROLE005', 'PERM030205');

INSERT OR IGNORE INTO sys_role_permission (role_biz_id, perm_biz_id)
VALUES ('ROLE005', 'PERM030206');
