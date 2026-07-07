# FAMS 项目后端 Bug 修复及功能新增 — 修改文档

> 生成日期: 2026-07-07
> 项目路径: `D:\__lybix__\_Codes\FAMS`

---

## 问题一：用户列表查询失败

### 根因
`UserLogic` 类缺少 `list_by_dept` 方法，但 `services\svc_user\user_handler.py` 中通过 gRPC handler 调用了 `self.user_logic.list_by_dept(dept_biz_id)`，触发 `AttributeError: 'UserLogic' object has no attribute 'list_by_dept'`。

### 修复方案
在 `UserLogic` 中新增 `list_by_dept` 和 `get_user` 两个方法，分别调用 DAO 层的对应方法。

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `D:\__lybix__\_Codes\FAMS\data\logic\user_logic.py` | 新增 `list_by_dept(dept_biz_id)` 方法（调用 `self.user_dao.list_by_dept(dept_biz_id)` 并返回用户列表）；新增 `get_user(biz_id)` 方法（调用 `self.user_dao.select_by_biz_id(biz_id)`） |

---

## 问题二：部门树查询失败（SQL 语法错误）

### 根因
`data\basic\base_dao.py` 中 `list_by_condition` 和 `count_by_condition` 方法使用字符串拼接方式生成 WHERE 子句：
```python
where_clause += " AND is_delete = 0"
```
当 `condition` 为空字典时，`where_clause` 为空字符串，导致最终 SQL 变成 `"SELECT * FROM table WHERE  AND is_delete = 0"`，触发 `near "AND": syntax error`。

### 修复方案
将字符串拼接改为列表方式：使用 `conditions = []` 逐个收集条件片段，最后用 `" WHERE " + " AND ".join(conditions)` 拼接。空 condition 时生成 `"WHERE is_delete = 0"`，非空时生成 `"WHERE field1 = ? AND is_delete = 0"`。

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `D:\__lybix__\_Codes\FAMS\data\basic\base_dao.py` | 重写 `list_by_condition()` 和 `count_by_condition()` 的 WHERE 子句拼接逻辑，由字符串拼接改为列表收集条件后 join |

---

## 问题三：报废/报修/领用列表查询失败（is_delete 列缺失）

### 根因
三张业务表 `fams_asset_borrow`、`fams_repair_workorder`、`fams_asset_scrap` 的建表 SQL 中没有 `is_delete` 列，但 DAO 基类 `BaseDao` 的查询方法硬编码了 `is_delete = 0` 过滤条件，导致 `sqlite3.OperationalError: no such column: is_delete`。

### 修复方案（采用方案 A）
给三张业务表添加 `is_delete INTEGER DEFAULT 0` 列，保持代码一致性。

#### 执行的 SQL
```sql
ALTER TABLE fams_asset_borrow ADD COLUMN is_delete INTEGER NOT NULL DEFAULT 0;
ALTER TABLE fams_repair_workorder ADD COLUMN is_delete INTEGER NOT NULL DEFAULT 0;
ALTER TABLE fams_asset_scrap ADD COLUMN is_delete INTEGER NOT NULL DEFAULT 0;
```

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `D:\__lybix__\_Codes\FAMS\data\fams.db` | 执行三条 ALTER TABLE 添加 `is_delete` 列 |
| `D:\__lybix__\_Codes\FAMS\data\fams_sqlite.sql` | 在 `fams_asset_borrow`、`fams_repair_workorder`、`fams_asset_scrap` 三张表的 `CREATE TABLE` 语句中添加 `is_delete INTEGER NOT NULL DEFAULT 0` |

---

## 问题四：注册功能缺失

### 根因
系统仅有登录功能，没有用户注册入口。

### 修复方案

#### 后端（Flask 网关）
- 新增 `POST /user/register` 接口（无需 `@login_required`），接收用户名、密码、确认密码、真实姓名、部门 ID、手机号、邮箱，校验必填项和密码一致性后调用 gRPC `UserService.CreateUser` 创建用户。
- 新增 `GET /dept/public-list` 接口（无需认证），获取部门树后扁平化为列表返回，供注册页下拉选择部门使用。

#### 前端
- 在 `index.html` 登录表单底部添加"立即注册"链接，跳转到 `register.html`。
- 新建 `register.html` 注册页面，包含：用户名、密码、确认密码、真实姓名、手机号、邮箱、所属部门（从后端异步加载下拉选项），注册成功后跳转登录页。

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `D:\__lybix__\_Codes\FAMS\services\svc_gateway\routes.py` | 新增 `POST /user/register` 路由（校验字段 + 调用 gRPC CreateUser）；新增 `GET /dept/public-list` 路由（无需认证，扁平化部门树） |
| `D:\__lybix__\_Codes\FAMS\web_front\index.html` | 登录表单底部添加 `<a href="register.html">立即注册</a>` 链接 |
| `D:\__lybix__\_Codes\FAMS\web_front\register.html` | **新建** — 完整的注册页面，含表单验证、部门下拉动态加载、注册 API 调用 |

---

## 问题五：数据字典分类硬编码

### 根因
前端 `js\pages\dict.js` 中数据字典的分类选项（`asset_type`、`asset_status`、`dept_type`）是硬编码的，后端也没有提供获取所有字典分类的接口。新增分类后前端无法感知。

### 修复方案

#### Proto 层
在 `proto\user.proto` 的 `DictService` 中新增 `ListDictTypes` RPC 方法，并新增 `GetDictTypesRequest`、`DictTypesResponse` 消息类型。

#### 数据层
- `data\basic\dict_dao.py` 新增 `list_types()` 方法，通过 `SELECT DISTINCT dict_type` 查询所有分类。
- `data\logic\dict_logic.py` 新增 `list_types()` 方法，调用 `dict_dao.list_types()`。

#### gRPC 服务层
- `services\svc_user\dict_handler.py` 新增 `ListDictTypes` handler，含 Redis 缓存。
- `proto\generated\user_pb2.py` 由 protoc 重新生成，包含新消息类。
- `proto\generated\user_pb2_grpc.py` 手动添加 `ListDictTypes` 对应的 Stub、Servicer、Server Registration 和实验性 API 方法。

#### REST 网关
- `routes.py` 新增 `GET /dict/types` 路由（需登录），调用 `DictServiceStub.ListDictTypes`。

#### 前端
- `web_front\js\pages\dict.js`：页面初始化时调用 `GET /dict/types` 获取分类列表并动态填充下拉选项；"全部类型"模式改为遍历所有分类分别拉取数据后合并展示。

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `D:\__lybix__\_Codes\FAMS\proto\user.proto` | DictService 新增 `rpc ListDictTypes`；新增 `GetDictTypesRequest` 和 `DictTypesResponse` 消息 |
| `D:\__lybix__\_Codes\FAMS\proto\generated\user_pb2.py` | protoc 重新生成，含 `GetDictTypesRequest` 和 `DictTypesResponse` 类 |
| `D:\__lybix__\_Codes\FAMS\proto\generated\user_pb2_grpc.py` | DictServiceStub / Servicer / add_to_server / DictService 四处均添加 `ListDictTypes` 方法 |
| `D:\__lybix__\_Codes\FAMS\data\basic\dict_dao.py` | 新增 `list_types()` 方法 |
| `D:\__lybix__\_Codes\FAMS\data\logic\dict_logic.py` | 新增 `list_types()` 方法 |
| `D:\__lybix__\_Codes\FAMS\services\svc_user\dict_handler.py` | 新增 `ListDictTypes` gRPC handler |
| `D:\__lybix__\_Codes\FAMS\services\svc_gateway\routes.py` | 新增 `GET /dict/types` 路由 |
| `D:\__lybix__\_Codes\FAMS\web_front\js\pages\dict.js` | 移除硬编码分类；新增 `loadTypes()` 从后端动态获取分类；`load()` 支持"全部类型"合并展示 |

---

## 修改总结

| 问题 | 根因 | 涉及文件数 | 修复方式 |
|------|------|:---:|----------|
| 一：用户列表查询 | UserLogic 缺少 list_by_dept | 1 | 新增方法 |
| 二：部门树 SQL 错误 | WHERE 字符串拼接导致空条件语法错误 | 1 | 改为列表拼接 |
| 三：is_delete 列缺失 | 三张业务表无软删除列 | 2 | ALTER TABLE + 建表脚本同步 |
| 四：注册功能缺失 | 未实现 | 3 | 新增后端接口 + 前端页面 |
| 五：字典分类硬编码 | 前端硬编码 + 后端无接口 | 8 | 全链路：Proto → DAO → Logic → Handler → grpc-stub → Route → 前端 |

**总计修改文件: 15 个**（含新建 1 个 register.html）

---

## 问题六：部门树查询失败 — parent_biz_id 字段缺失

> 修复日期: 2026-07-07

### 根因
`data/logic/dept_logic.py` 中 `_build_tree()` 方法使用 `dept["parent_biz_id"]` 作为父级关联字段，但 `sys_department` 表的建表 SQL 中没有该列（仅有 `id, biz_id, dept_name, dept_type, dept_sort, is_delete, create_time, update_time`）。`dept_dao.py` 的 `list_by_parent` 方法同样查询 `parent_biz_id` 列。运行时触发 `KeyError: 'parent_biz_id'`。

### 修复方案
给 `sys_department` 表添加 `parent_biz_id` 列，默认值为空字符串（与 `_build_tree` 中 `parent_id=""` 的初始调用语义一致：顶层部门的 parent 为空字符串）。

#### 执行的 SQL
```sql
ALTER TABLE sys_department ADD COLUMN parent_biz_id TEXT DEFAULT '';
```

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `D:\__lybix__\_Codes\FAMS\data\fams.db` (sys_department) | 执行 ALTER TABLE 添加 `parent_biz_id TEXT DEFAULT ''` 列 |

---

## 问题七：用户列表查询失败 — Proto UserInfo 无 id 字段

> 修复日期: 2026-07-07

### 根因
`services/svc_user/user_handler.py` 中 `ListUserByDept` 方法直接使用 `user_pb2.UserInfo(**u)` 将数据库查询结果字典展开传给 protobuf 构造函数。`user_dao.list_by_dept` 返回 `SELECT *` 结果，包含 `id`、`password`、`is_delete` 等 proto `UserInfo` 定义中不存在的字段。触发 `Protocol message UserInfo has no "id" field.`。

Proto `UserInfo` 实际字段为：`biz_id, username, real_name, dept_biz_id, phone, email, user_status`。

### 修复方案
参照同文件中 `GetUserByBizId` 方法的过滤写法，在构建 `UserInfo` 前通过 `DESCRIPTOR.fields_by_name.keys()` 过滤掉 proto 中不存在的字段。

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `D:\__lybix__\_Codes\FAMS\services\svc_user\user_handler.py` | `ListUserByDept` 中 `user_pb2.UserInfo(**u)` 改为 `user_pb2.UserInfo(**{k: u[k] for k in user_pb2.UserInfo.DESCRIPTOR.fields_by_name.keys() if k in u})` |

---

## 问题八：盘点任务列表查询失败 — is_delete 列缺失

> 修复日期: 2026-07-07

### 根因
`BaseDao` 基类所有查询方法硬编码了 `is_delete = 0` 过滤条件，但以下三张表建表时遗漏了 `is_delete` 列：
- `fams_check_task`（盘点任务表）
- `fams_asset_status_log`（资产状态变更日志表）
- `fams_check_detail`（盘点明细表）

与问题三同类问题，本次同步补齐。

### 修复方案
给三张表追加 `is_delete INTEGER DEFAULT 0` 列。

#### 执行的 SQL
```sql
ALTER TABLE fams_check_task ADD COLUMN is_delete INTEGER DEFAULT 0;
ALTER TABLE fams_asset_status_log ADD COLUMN is_delete INTEGER DEFAULT 0;
ALTER TABLE fams_check_detail ADD COLUMN is_delete INTEGER DEFAULT 0;
```

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `D:\__lybix__\_Codes\FAMS\data\fams.db` | 执行三条 ALTER TABLE 添加 `is_delete` 列 |

---

## 补充修改总结

| 问题 | 根因 | 涉及文件数 | 修复方式 |
|------|------|:---:|----------|
| 六：部门树查询失败 | sys_department 缺 parent_biz_id 列 | 1 | ALTER TABLE 添加列 |
| 七：用户列表查询失败 | UserInfo proto 无 id 字段 | 1 | 字段过滤 |
| 八：盘点任务列表 is_delete 缺失 | 三张表缺软删除列 | 1 | ALTER TABLE 添加列 |

**累计修改文件: 18 个**（含新建 1 个 register.html）
