-- 开启外键约束（可选，按需开启）
PRAGMA foreign_keys = ON;

-- ========== 模块一：系统组织架构与权限模块 ==========
-- 1.1 部门�?sys_department
-- 1.1 部门�?sys_department（修改后�?
CREATE TABLE IF NOT EXISTS sys_department (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  biz_id TEXT NOT NULL UNIQUE,
  dept_name TEXT NOT NULL,
  dept_type TEXT NOT NULL,
  dept_sort INTEGER DEFAULT 0,
  is_delete INTEGER NOT NULL DEFAULT 0,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- 索引：按部门类型查询优化
CREATE INDEX IF NOT EXISTS idx_dept_type ON sys_department(dept_type);
CREATE INDEX IF NOT EXISTS idx_dept_is_delete ON sys_department(is_delete);

-- 1.2 角色�?sys_role
CREATE TABLE IF NOT EXISTS sys_role (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  biz_id TEXT NOT NULL UNIQUE,
  role_name TEXT NOT NULL,
  role_code TEXT NOT NULL UNIQUE,
  role_desc TEXT DEFAULT '',
  is_delete INTEGER NOT NULL DEFAULT 0,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 1.3 权限�?sys_permission
CREATE TABLE IF NOT EXISTS sys_permission (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  biz_id TEXT NOT NULL UNIQUE,
  perm_name TEXT NOT NULL,
  perm_url TEXT NOT NULL UNIQUE,
  perm_type INTEGER NOT NULL,
  parent_biz_id TEXT DEFAULT '',
  is_delete INTEGER NOT NULL DEFAULT 0,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 1.4 角色-权限关联�?sys_role_permission
CREATE TABLE IF NOT EXISTS sys_role_permission (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  role_biz_id TEXT NOT NULL,
  perm_biz_id TEXT NOT NULL,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(role_biz_id, perm_biz_id)
);
CREATE INDEX IF NOT EXISTS idx_rp_role ON sys_role_permission(role_biz_id);
CREATE INDEX IF NOT EXISTS idx_rp_perm ON sys_role_permission(perm_biz_id);

-- 1.5 用户�?sys_user
CREATE TABLE IF NOT EXISTS sys_user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  biz_id TEXT NOT NULL UNIQUE,
  username TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,
  real_name TEXT NOT NULL,
  phone TEXT DEFAULT '',
  email TEXT DEFAULT '',
  dept_biz_id TEXT NOT NULL,
  user_status INTEGER NOT NULL DEFAULT 1,
  is_delete INTEGER NOT NULL DEFAULT 0,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_user_dept ON sys_user(dept_biz_id, is_delete);

-- 1.6 用户-角色关联�?sys_user_role
CREATE TABLE IF NOT EXISTS sys_user_role (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_biz_id TEXT NOT NULL,
  role_biz_id TEXT NOT NULL,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_biz_id, role_biz_id)
);
CREATE INDEX IF NOT EXISTS idx_ur_user ON sys_user_role(user_biz_id);
CREATE INDEX IF NOT EXISTS idx_ur_role ON sys_user_role(role_biz_id);

-- ========== 模块二：通用数据字典模块 ==========
-- 2.1 通用字典�?sys_dict
CREATE TABLE IF NOT EXISTS sys_dict (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  biz_id TEXT NOT NULL UNIQUE,
  dict_type TEXT NOT NULL,
  dict_code TEXT NOT NULL,
  dict_name TEXT NOT NULL,
  sort INTEGER DEFAULT 0,
  is_delete INTEGER NOT NULL DEFAULT 0,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(dict_type, dict_code)
);

-- ========== 模块三：固定资产核心主表 ==========
-- 3.1 资产主表 fams_asset
CREATE TABLE IF NOT EXISTS fams_asset (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  biz_id TEXT NOT NULL UNIQUE,
  asset_name TEXT NOT NULL,
  asset_type_code TEXT NOT NULL,
  buy_time DATE NOT NULL,
  asset_price NUMERIC(12,2) NOT NULL,
  store_location TEXT NOT NULL,
  dept_biz_id TEXT NOT NULL,
  current_status_code TEXT NOT NULL,
  use_user_biz_id TEXT DEFAULT '',
  supplier TEXT DEFAULT '',
  spec TEXT DEFAULT '',
  remark TEXT DEFAULT '',
  is_delete INTEGER NOT NULL DEFAULT 0,
  create_user_biz_id TEXT NOT NULL,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_asset_dept_status ON fams_asset(dept_biz_id, current_status_code, is_delete);
CREATE INDEX IF NOT EXISTS idx_asset_use_user ON fams_asset(use_user_biz_id);

-- 3.2 资产状态变更流水表 fams_asset_status_log
CREATE TABLE IF NOT EXISTS fams_asset_status_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_biz_id TEXT NOT NULL,
  old_status_code TEXT NOT NULL,
  new_status_code TEXT NOT NULL,
  oper_user_biz_id TEXT NOT NULL,
  oper_desc TEXT DEFAULT '',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_status_asset ON fams_asset_status_log(asset_biz_id);
CREATE INDEX IF NOT EXISTS idx_status_oper ON fams_asset_status_log(oper_user_biz_id);

-- 3.3 资产附件�?fams_asset_attach
CREATE TABLE IF NOT EXISTS fams_asset_attach (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  biz_id TEXT NOT NULL UNIQUE,
  asset_biz_id TEXT NOT NULL,
  attach_name TEXT NOT NULL,
  attach_path TEXT NOT NULL,
  attach_type INTEGER NOT NULL,
  file_size INTEGER DEFAULT 0,
  upload_user_biz_id TEXT NOT NULL,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_attach_asset ON fams_asset_attach(asset_biz_id);

-- ========== 模块四：多级协同审批业务模块 ==========
-- 4.1 统一审批流程主表 fams_audit_flow
CREATE TABLE IF NOT EXISTS fams_audit_flow (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  biz_id TEXT NOT NULL UNIQUE,
  business_type INTEGER NOT NULL,
  business_biz_id TEXT NOT NULL,
  apply_user_biz_id TEXT NOT NULL,
  dept_audit_user_biz_id TEXT DEFAULT '',
  dept_audit_result TEXT DEFAULT 'WAIT',
  dept_audit_time DATETIME NULL,
  school_audit_user_biz_id TEXT DEFAULT '',
  school_audit_result TEXT DEFAULT 'WAIT',
  school_audit_time DATETIME NULL,
  final_result TEXT NOT NULL DEFAULT 'WAIT',
  apply_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finish_time DATETIME NULL,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_business ON fams_audit_flow(business_type, business_biz_id);
CREATE INDEX IF NOT EXISTS idx_audit_apply_user ON fams_audit_flow(apply_user_biz_id);

-- 4.2 资产领用归还申请�?fams_asset_borrow
CREATE TABLE IF NOT EXISTS fams_asset_borrow (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  biz_id TEXT NOT NULL UNIQUE,
  asset_biz_id TEXT NOT NULL,
  borrow_user_biz_id TEXT NOT NULL,
  borrow_start_time DATE NOT NULL,
  borrow_end_time DATE NULL,
  actual_return_time DATETIME NULL,
  borrow_desc TEXT DEFAULT '',
  flow_biz_id TEXT DEFAULT '',
  borrow_status TEXT NOT NULL DEFAULT 'APPLY',
  is_delete INTEGER NOT NULL DEFAULT 0,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_borrow_asset ON fams_asset_borrow(asset_biz_id);
CREATE INDEX IF NOT EXISTS idx_borrow_user ON fams_asset_borrow(borrow_user_biz_id);
CREATE INDEX IF NOT EXISTS idx_borrow_flow ON fams_asset_borrow(flow_biz_id);

-- 4.3 报修维修工单�?fams_repair_workorder
CREATE TABLE IF NOT EXISTS fams_repair_workorder (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  biz_id TEXT NOT NULL UNIQUE,
  asset_biz_id TEXT NOT NULL,
  report_user_biz_id TEXT NOT NULL,
  fault_desc TEXT NOT NULL,
  repair_user_biz_id TEXT DEFAULT '',
  repair_cost NUMERIC(12,2) DEFAULT 0,
  repair_result TEXT DEFAULT '',
  flow_biz_id TEXT DEFAULT '',
  order_status TEXT NOT NULL DEFAULT 'REPORT',
  is_delete INTEGER NOT NULL DEFAULT 0,
  report_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finish_time DATETIME NULL,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_repair_asset ON fams_repair_workorder(asset_biz_id);
CREATE INDEX IF NOT EXISTS idx_repair_report_user ON fams_repair_workorder(report_user_biz_id);
CREATE INDEX IF NOT EXISTS idx_repair_flow ON fams_repair_workorder(flow_biz_id);

-- 4.4 资产报废审核�?fams_asset_scrap
CREATE TABLE IF NOT EXISTS fams_asset_scrap (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  biz_id TEXT NOT NULL UNIQUE,
  asset_biz_id TEXT NOT NULL,
  apply_user_biz_id TEXT NOT NULL,
  scrap_reason TEXT NOT NULL,
  flow_biz_id TEXT DEFAULT '',
  scrap_status TEXT NOT NULL DEFAULT 'APPLY',
  is_delete INTEGER NOT NULL DEFAULT 0,
  apply_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  audit_time DATETIME NULL,
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_scrap_asset ON fams_asset_scrap(asset_biz_id);
CREATE INDEX IF NOT EXISTS idx_scrap_flow ON fams_asset_scrap(flow_biz_id);

-- ========== 模块五：多人协同盘点模块 ==========
-- 5.1 盘点任务主表 fams_check_task
CREATE TABLE IF NOT EXISTS fams_check_task (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  biz_id TEXT NOT NULL UNIQUE,
  task_name TEXT NOT NULL,
  target_dept_biz_id TEXT NOT NULL,
  start_time DATETIME NOT NULL,
  end_time DATETIME NOT NULL,
  create_user_biz_id TEXT NOT NULL,
  task_status TEXT NOT NULL DEFAULT 'WAIT',
  llm_diff_result TEXT DEFAULT '',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_check_dept ON fams_check_task(target_dept_biz_id);

-- 5.2 盘点明细记录�?fams_check_detail
CREATE TABLE IF NOT EXISTS fams_check_detail (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_biz_id TEXT NOT NULL,
  asset_biz_id TEXT NOT NULL,
  check_user_biz_id TEXT NOT NULL,
  actual_exist INTEGER NOT NULL,
  real_location TEXT DEFAULT '',
  check_remark TEXT DEFAULT '',
  check_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(task_biz_id, asset_biz_id)
);
CREATE INDEX IF NOT EXISTS idx_detail_task ON fams_check_detail(task_biz_id);
CREATE INDEX IF NOT EXISTS idx_detail_asset ON fams_check_detail(asset_biz_id);
CREATE INDEX IF NOT EXISTS idx_detail_user ON fams_check_detail(check_user_biz_id);

-- ========== 模块六：全局审计日志模块 ==========
-- 6.1 系统操作审计日志 sys_oper_log
CREATE TABLE IF NOT EXISTS sys_oper_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  biz_id TEXT NOT NULL UNIQUE,
  oper_user_biz_id TEXT NOT NULL,
  oper_module TEXT NOT NULL,
  oper_type TEXT NOT NULL,
  oper_content TEXT DEFAULT '',
  request_url TEXT DEFAULT '',
  ip_address TEXT DEFAULT '',
  oper_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_log_user ON sys_oper_log(oper_user_biz_id);
CREATE INDEX IF NOT EXISTS idx_log_time ON sys_oper_log(oper_time);