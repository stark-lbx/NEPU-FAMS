# FAMS-NEPU v2 前端 (front)

> 高校固定资产协同管理系统 — 第二代前端，7 大模块扁平布局。

## 启动

```bash
# 安装依赖（首次）
cd platform/front
npm install

# 开发（端口 5174）
npm run dev

# 类型检查 + 打包
npm run build
```

> 启动前请确保后端 `enable_server.cmd` 已运行（端口 9900）。前端 dev server 已配置 `/api → http://127.0.0.1:9900` 代理。

## 7 大模块

| # | 路径                | 名称       | 角色     | 说明 |
|---|--------------------|-----------|---------|------|
| 1 | `/dashboard`       | 资产台     | 全员    | KPI + 折线/饼图/条形 + 待办 + 学院分布 + 快捷 |
| 2 | `/users`           | 用户管理   | admin / college_admin | 多条件过滤 + CRUD + 部门树 + 角色分配 + 列排序 |
| 3 | `/assets`          | 资产管理   | admin / college_admin | 多条件过滤 + CRUD + 详情 + 状态/分类/部门/地点/日期 + 列排序 |
| 4 | `/workflows`       | 流程管理   | 全员    | 进行中/已终止 × 全部/领用/归还/报修/报废 + 发起按钮 + 列排序 |
| 5 | `/my-borrows`      | 我的借用   | 全员    | 领用中资产 + 维修工单 + 我的申请 + 一键归还/报修 + 列排序 |
| 6 | `/profile`         | 个人信息   | 全员    | 资料查看 + 修改密码 + 退出登录 |
| 7 | `/checks`          | 资产盘点   | admin / college_admin | 任务列表 + 创建 + 协同录入（el-table 内联编辑）+ 差异报告 + 确认 |

## 权限与菜单展示

- 路由 `meta.roles` 声明可见角色；
- `layout/Index.vue` 的 `menuItems` 计算属性按 `userStore.roles` 自动过滤侧边栏；
- 详细按钮（编辑/删除/审批/验收/确认）按 `useUserStore().hasRole(...)` 在页面内显隐；
- 路由守卫跳 403 前给 toast 提示（"您当前的角色无权访问 XX"），403 页面给出按角色的友好说明。

## 表格列排序

- 6 个核心表格（用户/资产/流程/我的借用 3 个/盘点）全部支持列排序
- 实现：`composables/useTableSort.ts` —— 客户端排序，支持数字/字符串/日期/中文字段

## 与后端 API 约定

前端仅消费后端已暴露的 `services/svr_gateway/routes.py` 端点，**不写 SQL**。
按业务分类组织于 `src/api/`：

- `user.ts` —— 登录、用户/角色/部门、密码修改
- `asset.ts` —— 资产 CRUD、分类/状态字典
- `workflow.ts` —— 申请/报修 全流程接口
- `report.ts` —— Dashboard / 资产 / 维修 统计
- `check.ts` —— 盘点任务、明细、差异报告

## 与 v1 关系

- 端口与目录均独立：v1 = `platform/webview`（5173），v2 = `platform/front`（5174）
- 共用同一后端服务（端口 9900）
- v2 **不会**修改 v1 任何代码，可并存；上线时只切 nginx upstream
- v1 中的"分散入口"（报修/领用/归还/报废/盘点 各独立页面）已合并到 v2 的 7 大模块内

## v2.1 修复要点（2026-07-12）

- 后端 `report_dao.py`：修复 `%%Y-%%m` 双转义导致字面量入库（`month` 字段从 `"%Y-%m"` 变为 `"2026-07"`）
- 后端 `status_distribution` 增加 `LEFT JOIN asset_status` 返回 `{status_id, status_name, value}`，前端不再需要二次查字典
- 流程管理：新增【全部】tab、修复【已终止归档 × 报修】未传 status 拉错数据的 bug、顶部新增【发起申请/报修】4 个按钮 + 弹窗
- 普通用户进 403 不再只弹错，前端路由守卫先 toast 拦截 + 403 页面给出角色说明
- 盘点模块：v1 依赖 luckysheet 太重，v2 用 el-table 内联编辑完成协同录入，并配套差异报告 + 确认

## v2.0 概览（2026-07-12 初版）

- 6 大模块扁平布局（v2.1 升级为 7 大模块，新增盘点）
- 完整用户/资产/流程/我的借用/个人信息 CRUD
- Dashboard 大屏信息密集（4 KPI + 3 图表 + 学院分布 + 待办 + 6 快捷）
- 流程管理：双层 Tab 矩阵 + 详情页审批
- vue-tsc 零错误 + vite build 68 文件 / 2.9 MB
