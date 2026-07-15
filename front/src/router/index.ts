import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getToken, removeToken } from '@/utils/auth'
import { useUserStore } from '@/store/user'

const Layout = () => import('@/layout/Index.vue')

/**
 * 路由与菜单设计
 * 侧边栏菜单按 "功能" 组织，不显示详情页/编辑页等子页。
 *
 * 路由 meta 字段：
 *   - title       菜单/页面标题
 *   - icon        Element Plus 图标名
 *   - showInMenu  是否在侧边栏显示（默认 true；详情页/编辑页等子页必须显式设为 false）
 *   - parent      归属的父菜单 path（用于嵌套子菜单；不设 = 顶级菜单）
 *   - perms       路由守卫校验：要求用户拥有任一权限码
 *   - roles       路由守卫校验：要求用户拥有任一角色
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/Index.vue'),
    meta: { title: '登录', showInMenu: false },
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      // ============ 1. 资产台（首页） ============
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Index.vue'),
        meta: { title: '资产台', icon: 'Monitor' },
      },

      // ============ 2. 业务办理 ============
      {
        path: 'assets',
        name: 'AssetManage',
        component: () => import('@/views/asset/Index.vue'),
        meta: { title: '资产管理', icon: 'Box' },
      },
      {
        path: 'assets/detail/:id',
        name: 'AssetDetail',
        component: () => import('@/views/asset/Detail.vue'),
        meta: { title: '资产详情', showInMenu: false },
      },
      {
        path: 'my-borrows',
        name: 'MyBorrows',
        component: () => import('@/views/borrow/Index.vue'),
        meta: { title: '我的申请', icon: 'Goods' },
      },

      // 流程中心（父菜单 + 3 个子项）
      {
        path: 'workflows',
        name: 'WorkflowHub',
        component: () => import('@/views/workflow/Index.vue'),
        meta: { title: '流程中心', icon: 'Document' },
      },
      {
        path: 'workflows/pending',
        name: 'WorkflowPending',
        component: () => import('@/views/workflow/Pending.vue'),
        meta: { title: '待办清单', parent: '/workflows', showInMenu: false },
      },
      {
        path: 'workflows/done',
        name: 'WorkflowDone',
        component: () => import('@/views/workflow/Done.vue'),
        meta: { title: '我的已处理', parent: '/workflows', showInMenu: false },
      },
      {
        path: 'workflows/apply/:id',
        name: 'ApplyDetail',
        component: () => import('@/views/workflow/ApplyDetail.vue'),
        meta: { title: '申请详情', showInMenu: false },
      },
      {
        path: 'workflows/repair/:id',
        name: 'RepairDetail',
        component: () => import('@/views/workflow/RepairDetail.vue'),
        meta: { title: '工单详情', showInMenu: false },
      },

      // ============ 3. 系统管理（仅 admin/college_admin） ============
      {
        path: 'users',
        name: 'UserManage',
        component: () => import('@/views/user/Index.vue'),
        meta: { title: '用户管理', icon: 'User', roles: ['admin', 'college_admin'] },
      },
      {
        path: 'checks',
        name: 'CheckManage',
        component: () => import('@/views/check/Index.vue'),
        meta: { title: '资产盘点', icon: 'Collection', roles: ['admin', 'college_admin'] },
      },
      {
        path: 'checks/:id',
        name: 'CheckSheet',
        component: () => import('@/views/check/Sheet.vue'),
        meta: { title: '协同盘点', showInMenu: false, roles: ['admin', 'college_admin'] },
      },
      {
        path: 'checks/:id/report',
        name: 'CheckReport',
        component: () => import('@/views/check/Report.vue'),
        meta: { title: '盘点报告', showInMenu: false, roles: ['admin', 'college_admin'] },
      },

      // ============ 4. 个人中心（走右上角下拉，不进侧边栏） ============
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/profile/Index.vue'),
        meta: { title: '个人信息', showInMenu: false },
      },
    ],
  },
  // 全屏大屏（顶级路由，不进 layout，铺满整个浏览器）
  {
    path: '/dashboard/fullscreen',
    name: 'DashboardFullscreen',
    component: () => import('@/views/dashboard/Fullscreen.vue'),
    meta: { title: '资产台·全屏大屏', showInMenu: false },
  },
  {
    path: '/403',
    name: '403',
    component: () => import('@/views/error/403.vue'),
    meta: { showInMenu: false },
  },
  {
    path: '/:pathMatch(.*)*',
    name: '404',
    component: () => import('@/views/error/404.vue'),
    meta: { showInMenu: false },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

/**
 * 路由守卫（极简版）
 *   1. 无 token → /login
 *   2. 有 token：先确保权限已加载，再判断 meta.perms / meta.roles
 *   3. 不通过 → /403 + toast
 */
router.beforeEach(async (to, _from, next) => {
  document.title = `${to.meta.title || ''} - FAMS-NEPU v2`
  const token = getToken()
  if (to.path === '/login') return next()
  if (!token) return next('/login')

  const userStore = useUserStore()
  if (!userStore.userInfo) {
    try { await userStore.fetchUserInfo() } catch { /* ignore */ }
  }
  if (!userStore.permissions.length) {
    try { await userStore.fetchPerms() } catch { /* ignore */ }
  }

  const meta = to.meta as any
  const requiredPerms: string[] | undefined = meta?.perms
  const requiredRoles: string[] | undefined = meta?.roles

  if (requiredRoles && requiredRoles.length > 0) {
    if (!requiredRoles.some((r: string) => userStore.hasRole(r))) {
      ElMessage.warning(`您当前的角色无权访问「${meta.title || to.path}」`)
      return next('/403')
    }
  }
  if (requiredPerms && requiredPerms.length > 0) {
    if (!requiredPerms.some((p: string) => userStore.hasPerm(p))) {
      ElMessage.warning(`您当前的角色无权访问「${meta.title || to.path}」`)
      return next('/403')
    }
  }
  next()
})

export default router
