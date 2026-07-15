<template>
  <el-container class="layout-root">
    <el-aside :width="isCollapse ? '64px' : '232px'" class="layout-aside">
      <div class="logo-bar" :class="{ collapsed: isCollapse }">
        <el-icon class="logo-icon"><Box /></el-icon>
        <div v-show="!isCollapse" class="logo-text-wrap">
          <span class="logo-text">FAMS v2</span>
          <span class="logo-sub">固定资产协同管理</span>
        </div>
      </div>

      <el-menu
        :default-active="activePath"
        :collapse="isCollapse"
        :collapse-transition="false"
        background-color="transparent"
        text-color="#bfcbd9"
        active-text-color="#fff"
        router
        class="layout-menu"
        :unique-opened="true"
      >
        <template v-for="group in menuGroups" :key="group.key">
          <!-- 分组标题 -->
          <div v-if="!isCollapse && group.items.length" class="group-label">
            <el-icon><component :is="group.icon" /></el-icon>
            <span>{{ group.title }}</span>
          </div>

          <template v-for="m in group.items" :key="m.path">
            <!-- 有子项：el-sub-menu -->
            <el-sub-menu v-if="m.children.length" :index="m.path">
              <template #title>
                <el-icon><component :is="m.icon" /></el-icon>
                <span>{{ m.title }}</span>
              </template>
              <el-menu-item v-for="c in m.children" :key="c.path" :index="c.path">
                <el-icon><component :is="c.icon" /></el-icon>
                <template #title>{{ c.title }}</template>
              </el-menu-item>
            </el-sub-menu>

            <!-- 无子项：el-menu-item -->
            <el-menu-item v-else :index="m.path">
              <el-icon><component :is="m.icon" /></el-icon>
              <template #title>{{ m.title }}</template>
            </el-menu-item>
          </template>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div class="header-left">
          <el-icon class="toggle-btn" @click="isCollapse = !isCollapse">
            <component :is="isCollapse ? 'Expand' : 'Fold'" />
          </el-icon>
          <el-breadcrumb separator="/" class="bc">
            <el-breadcrumb-item v-for="b in breadcrumbs" :key="b.path" :to="b.path">
              {{ b.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tag v-if="userStore.userInfo" :type="roleTagType" effect="dark" round size="small" class="role-tag">
            <el-icon style="margin-right:4px"><Avatar /></el-icon>
            {{ userStore.userInfo.nickname }}
          </el-tag>
          <el-tag :type="roleTagType" effect="plain" round size="small">
            {{ roleLabel }}
          </el-tag>
          <el-dropdown trigger="click" @command="onCommand">
            <span class="user-trigger">
              <el-avatar :size="30" :style="{ background: avatarColor }">
                {{ avatarChar }}
              </el-avatar>
              <el-icon style="margin-left:4px"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><UserFilled /></el-icon> 个人信息
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="layout-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { routes } from '@/router'
import { useUserStore } from '@/store/user'
import {
  Box, Monitor, UserFilled, ArrowDown, Expand, Fold, SwitchButton, Avatar,
  Suitcase, Setting, User as UserIcon,
  Goods, Collection, Document,
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const isCollapse = ref(false)

onMounted(async () => {
  if (userStore.token && !userStore.userInfo) {
    try { await userStore.fetchUserInfo() } catch { /* ignore */ }
  }
  if (userStore.token && !userStore.permissions.length) {
    try { await userStore.fetchPerms() } catch { /* ignore */ }
  }
})

const activePath = computed(() => route.path)

/**
 * 把 routes 拍平 + 提取菜单项
 * 严格规则：只收集 showInMenu !== false 的项
 */
interface MenuNode {
  path: string
  title: string
  icon: string
  group: string
  roles?: string[]
  perms?: string[]
  parent: string | null
  children: MenuNode[]
}

const layoutChildren = (routes.find((r) => r.path === '/')?.children || []) as any[]

/** 所有可见的菜单项（顶级 + 子项） */
const allVisibleItems = computed<MenuNode[]>(() => {
  const list: MenuNode[] = []
  for (const c of layoutChildren) {
    if (!c.meta) continue
    const meta = c.meta as any
    // 严格：showInMenu 显式 false 跳过（默认 true）
    if (meta.showInMenu === false) continue
    // 权限过滤
    if (meta.roles?.length && !userStore.hasRole(meta.roles)) continue
    if (meta.perms?.length && !userStore.hasAnyPerm(meta.perms)) continue

    list.push({
      path: '/' + c.path,
      title: meta.title as string,
      icon: (meta.icon as string) || '',
      group: '',  // 顶级项的 group 由分组规则决定
      roles: meta.roles,
      perms: meta.perms,
      parent: null,
      children: [],
    })
  }
  return list
})

/**
 * 3 大侧边主区
 * 顶级菜单 = 归属某个主区（按 path 硬编码）
 * 子菜单 = parent 指向顶级菜单，自动挂到父项下
 */
const ICON_MAP: Record<string, any> = {
  Monitor, Suitcase, Setting, User: UserIcon, Box, UserFilled,
  Document, Goods, Collection,
}

/** 顶级菜单归类（按 path 前缀硬编码，清晰可控） */
function getGroup(path: string): string | null {
  if (path === '/dashboard') return 'dashboard'
  if (path === '/assets' || path.startsWith('/assets/')) return 'business'
  if (path === '/my-borrows' || path.startsWith('/my-borrows/')) return 'business'
  if (path.startsWith('/workflows')) return 'business'
  if (path === '/users' || path.startsWith('/users/')) return 'manage'
  if (path.startsWith('/checks')) return 'manage'
  return null
}

/** 顶级菜单（has parent === null OR parent 不在可见项中） */
const topLevelItems = computed<MenuNode[]>(() => {
  // 从 allVisibleItems 找出顶级 + 找子项挂上去
  const visiblePaths = new Set(allVisibleItems.value.map((i) => i.path))

  // 1. 顶级项
  const topList: MenuNode[] = []
  for (const it of allVisibleItems.value) {
    // 子项的 path 形如 /workflows/pending
    // 顶级项的 path 形如 /workflows、/assets
    const group = getGroup(it.path)
    if (!group) continue
    // 判断是否为顶级：path 不含 "/<x>" 后缀，或后缀是 detail/id 等
    // 简单方式：path 与其父级顶级项 path 不同
    const isTop = ['/dashboard', '/assets', '/my-borrows', '/workflows', '/users', '/checks'].includes(it.path)
    if (isTop) {
      topList.push({ ...it, group, children: [] })
    }
  }

  // 2. 把 parent 指向顶级项的子项挂上去
  for (const it of allVisibleItems.value) {
    // 它是子项的条件：不是顶级
    if (['/dashboard', '/assets', '/my-borrows', '/workflows', '/users', '/checks'].includes(it.path)) continue
    // 找父级
    let parentPath: string | null = null
    if (it.path.startsWith('/workflows/')) parentPath = '/workflows'
    if (parentPath) {
      const parent = topList.find((p) => p.path === parentPath)
      if (parent) {
        parent.children.push({ ...it, group: parent.group, parent: parentPath })
      }
    }
  }

  return topList
})

/** 3 大侧边主区定义（按角色过滤） */
const GROUP_DEFS: { key: string; title: string; icon: any }[] = [
  { key: 'dashboard', title: '首页',     icon: Monitor },
  { key: 'business',  title: '业务办理', icon: Suitcase },
  { key: 'manage',    title: '系统管理', icon: Setting },
]

const menuGroups = computed(() => {
  return GROUP_DEFS
    .map((g) => ({
      ...g,
      items: topLevelItems.value
        .filter((m) => m.group === g.key)
        .map((m) => ({
          ...m,
          icon: ICON_MAP[m.icon] || Box,
        })),
    }))
    .filter((g) => g.items.length > 0)
})

const breadcrumbs = computed(() => {
  const items: { path: string; title: string }[] = [{ path: '/dashboard', title: '首页' }]
  if (route.path !== '/dashboard') {
    const title = (route.meta?.title as string) || ''
    if (title) items.push({ path: route.path, title })
  }
  return items
})

const roleLabel = computed(() => {
  const r = userStore.roles
  if (r.includes('admin')) return '校级管理员'
  if (r.includes('college_admin')) return '院级管理员'
  if (r.includes('repairer')) return '维修工程师'
  return '普通师生'
})

const roleTagType = computed<'danger' | 'warning' | 'success' | 'info'>(() => {
  if (userStore.roles.includes('admin')) return 'danger'
  if (userStore.roles.includes('college_admin')) return 'warning'
  if (userStore.roles.includes('repairer')) return 'success'
  return 'info'
})

const avatarChar = computed(() => {
  const n = userStore.userInfo?.nickname || userStore.userInfo?.username || 'U'
  return n.charAt(0).toUpperCase()
})

const avatarColor = computed(() => {
  const t = roleTagType.value
  return t === 'danger' ? '#f56c6c'
    : t === 'warning' ? '#e6a23c'
    : t === 'success' ? '#67c23a'
    : '#909399'
})

function onCommand(cmd: string) {
  if (cmd === 'profile') router.push('/profile')
  else if (cmd === 'logout') userStore.logout()
}
</script>

<style scoped>
.layout-root { height: 100vh; }

.layout-aside {
  background: #1f2d3d;
  transition: width 0.2s;
  overflow-x: hidden;
  border-right: 1px solid #1a2533;
  display: flex;
  flex-direction: column;
}
.layout-aside :deep(.el-menu) {
  border-right: none;
  flex: 1;
  overflow-y: auto;
  background: transparent;
}
.layout-aside :deep(.el-menu-item),
.layout-aside :deep(.el-sub-menu__title) {
  background-color: transparent !important;
}
.layout-aside :deep(.el-menu-item:hover),
.layout-aside :deep(.el-sub-menu__title:hover) {
  background-color: #2a3a52 !important;
}
.layout-aside :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, #409eff 0%, #2a3a52 100%) !important;
  color: #fff !important;
  border-radius: 6px;
  margin: 2px 8px;
}
.layout-aside :deep(.el-sub-menu .el-menu) {
  background: #182736 !important;
}
.layout-aside :deep(.el-sub-menu .el-menu-item.is-active) {
  background: linear-gradient(90deg, #409eff 0%, #182736 100%) !important;
}

.logo-bar {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  background: linear-gradient(135deg, #14202e 0%, #1f2d3d 100%);
  font-weight: 600;
  padding: 0 16px;
  border-bottom: 1px solid #1a2533;
}
.logo-bar.collapsed { padding: 0; justify-content: center; }
.logo-bar .logo-icon { font-size: 26px; color: #409eff; flex-shrink: 0; }
.logo-text-wrap { display: flex; flex-direction: column; line-height: 1.1; }
.logo-text { font-size: 16px; letter-spacing: 1px; }
.logo-sub { font-size: 10px; color: #8b9bb0; margin-top: 2px; font-weight: normal; }

.group-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 14px 20px 6px;
  font-size: 11px;
  color: #6c7a8d;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.group-label .el-icon { font-size: 12px; }

.layout-header {
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 56px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.header-left { display: flex; align-items: center; gap: 16px; }
.toggle-btn { font-size: 20px; cursor: pointer; color: #606266; }
.bc { font-size: 13px; }
.header-right { display: flex; align-items: center; gap: 10px; }
.role-tag { font-weight: 500; }
.user-trigger { cursor: pointer; display: flex; align-items: center; }

.layout-main {
  background: #f5f7fa;
  padding: 16px;
  overflow: auto;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
