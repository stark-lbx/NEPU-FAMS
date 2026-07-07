-- ========== 一级模块 ==========
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM0001', '系统管理', '/system', 1, ''),
('PERM0002', '资产管理', '/asset', 1, ''),
('PERM0003', '流程管理', '/flow', 1, ''),
('PERM0004', '文件服务', '/storage', 1, '');

-- ========== 系统管理-二级模块 ==========
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM0101', '用户管理', '/system/user', 1, 'PERM0001'),
('PERM0102', '部门管理', '/system/dept', 1, 'PERM0001'),
('PERM0103', '角色管理', '/system/role', 1, 'PERM0001'),
('PERM0104', '字典管理', '/system/dict', 1, 'PERM0001');

-- 用户管理-接口权限
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM010101', '用户列表查询', 'GET:/api/system/user/list', 2, 'PERM0101'),
('PERM010102', '用户新增', 'POST:/api/system/user', 2, 'PERM0101'),
('PERM010103', '用户修改', 'PUT:/api/system/user', 2, 'PERM0101'),
('PERM010104', '用户删除', 'DELETE:/api/system/user/{id}', 2, 'PERM0101'),
('PERM010105', '用户详情查询', 'GET:/api/system/user/{id}', 2, 'PERM0101');

-- 部门管理-接口权限
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM010201', '部门列表查询', 'GET:/api/system/dept/list', 2, 'PERM0102'),
('PERM010202', '部门新增', 'POST:/api/system/dept', 2, 'PERM0102'),
('PERM010203', '部门修改', 'PUT:/api/system/dept', 2, 'PERM0102'),
('PERM010204', '部门删除', 'DELETE:/api/system/dept/{id}', 2, 'PERM0102');

-- 角色管理-接口权限
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM010301', '角色列表查询', 'GET:/api/system/role/list', 2, 'PERM0103'),
('PERM010302', '角色新增', 'POST:/api/system/role', 2, 'PERM0103'),
('PERM010303', '角色修改', 'PUT:/api/system/role', 2, 'PERM0103'),
('PERM010304', '角色删除', 'DELETE:/api/system/role/{id}', 2, 'PERM0103'),
('PERM010305', '角色权限分配', 'PUT:/api/system/role/{id}/perm', 2, 'PERM0103');

-- 字典管理-接口权限
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM010401', '字典列表查询', 'GET:/api/system/dict/list', 2, 'PERM0104'),
('PERM010402', '字典新增', 'POST:/api/system/dict', 2, 'PERM0104'),
('PERM010403', '字典修改', 'PUT:/api/system/dict', 2, 'PERM0104'),
('PERM010404', '字典删除', 'DELETE:/api/system/dict/{id}', 2, 'PERM0104');

-- ========== 资产管理-二级模块 ==========
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM0201', '资产台账', '/asset/info', 1, 'PERM0002'),
('PERM0202', '资产分类', '/asset/category', 1, 'PERM0002');

-- 资产台账-接口权限
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM020101', '资产列表查询', 'GET:/api/asset/list', 2, 'PERM0201'),
('PERM020102', '资产新增', 'POST:/api/asset', 2, 'PERM0201'),
('PERM020103', '资产修改', 'PUT:/api/asset', 2, 'PERM0201'),
('PERM020104', '资产删除', 'DELETE:/api/asset/{id}', 2, 'PERM0201'),
('PERM020105', '资产详情查询', 'GET:/api/asset/{id}', 2, 'PERM0201'),
('PERM020106', '资产盘点', 'POST:/api/asset/check', 2, 'PERM0201');

-- 资产分类-接口权限
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM020201', '分类列表查询', 'GET:/api/asset/category/list', 2, 'PERM0202'),
('PERM020202', '分类新增', 'POST:/api/asset/category', 2, 'PERM0202'),
('PERM020203', '分类修改', 'PUT:/api/asset/category', 2, 'PERM0202'),
('PERM020204', '分类删除', 'DELETE:/api/asset/category/{id}', 2, 'PERM0202');

-- ========== 流程管理-二级模块 ==========
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM0301', '借用流程', '/flow/borrow', 1, 'PERM0003'),
('PERM0302', '报修流程', '/flow/repair', 1, 'PERM0003'),
('PERM0303', '报废流程', '/flow/scrap', 1, 'PERM0003');

-- 借用流程-接口权限
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM030101', '借用申请', 'POST:/api/flow/borrow/apply', 2, 'PERM0301'),
('PERM030102', '借用审批', 'POST:/api/flow/borrow/approve', 2, 'PERM0301'),
('PERM030103', '借用记录查询', 'GET:/api/flow/borrow/list', 2, 'PERM0301'),
('PERM030104', '归还确认', 'POST:/api/flow/borrow/return', 2, 'PERM0301');

-- 报修流程-接口权限
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM030201', '报修申请', 'POST:/api/flow/repair/apply', 2, 'PERM0302'),
('PERM030202', '报修处理', 'POST:/api/flow/repair/handle', 2, 'PERM0302'),
('PERM030203', '报修记录查询', 'GET:/api/flow/repair/list', 2, 'PERM0302');

-- 报废流程-接口权限
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM030301', '报废申请', 'POST:/api/flow/scrap/apply', 2, 'PERM0303'),
('PERM030302', '报废审批', 'POST:/api/flow/scrap/approve', 2, 'PERM0303'),
('PERM030303', '报废记录查询', 'GET:/api/flow/scrap/list', 2, 'PERM0303');

-- ========== 文件服务-二级模块 ==========
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM0401', '文件管理', '/storage/file', 1, 'PERM0004');

-- 文件管理-接口权限
INSERT INTO sys_permission (biz_id, perm_name, perm_url, perm_type, parent_biz_id) VALUES
('PERM040101', '文件上传', 'POST:/api/storage/upload', 2, 'PERM0401'),
('PERM040102', '文件下载', 'GET:/api/storage/download/{id}', 2, 'PERM0401'),
('PERM040103', '文件删除', 'DELETE:/api/storage/{id}', 2, 'PERM0401'),
('PERM040104', '文件列表查询', 'GET:/api/storage/list', 2, 'PERM0401');