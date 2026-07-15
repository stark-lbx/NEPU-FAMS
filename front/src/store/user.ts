import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getToken, setToken, removeToken } from '@/utils/auth'
import { parseJwtPayload } from '@/utils/format'
import { loginApi, getUserInfoApi, getUserPermsApi } from '@/api/user'
import router from '@/router'
import type { UserInfo } from '@/types'

/**
 * 前后端协同管理 - 用户 Store
 * 职责：
 *   1. 维护 token / 用户信息
 *   2. 维护当前用户的角色列表 roles（用于路由 meta.roles 校验）
 *   3. 维护当前用户的权限码 permissions（用于路由 meta.perms 校验）
 *
 * 注意：菜单由前端根据 routes + roles + permissions 动态生成，
 *       后端 sys_menu 只存"权限码"，不存 path/component。
 */
export const useUserStore = defineStore('user', () => {
  const token = ref<string>(getToken() || '')
  const userInfo = ref<UserInfo | null>(null)
  const roles = ref<string[]>([])
  const permissions = ref<string[]>([])

  function initRolesFromToken() {
    if (!token.value) return
    const p = parseJwtPayload(token.value)
    roles.value = p?.role_keys || []
  }
  if (token.value) initRolesFromToken()

  async function login(username: string, password: string) {
    const res: any = await loginApi({ username, password })
    if (res?.data?.token) {
      setToken(res.data.token)
      token.value = res.data.token
      initRolesFromToken()
      await fetchUserInfo()
      await fetchPerms()
    }
    return res
  }

  async function fetchUserInfo() {
    const res: any = await getUserInfoApi()
    userInfo.value = res?.data || null
    if (userInfo.value) roles.value = userInfo.value.role_keys || []
  }

  /**
   * 加载当前用户的权限码集合
   * 后端只返回扁平 perms 列表，不返回 path/component
   */
  async function fetchPerms() {
    try {
      const res: any = await getUserPermsApi()
      // 兼容两种返回：data=[perm1, perm2] 或 data={ perms: [...] }
      const data = res?.data
      const perms: string[] = Array.isArray(data)
        ? data
        : Array.isArray(data?.perms) ? data.perms : []
      permissions.value = perms.filter(Boolean)
    } catch {
      permissions.value = []
    }
  }

  function logout() {
    removeToken()
    token.value = ''
    userInfo.value = null
    roles.value = []
    permissions.value = []
    router.push('/login')
  }

  function hasRole(rolesNeeded: string | string[]): boolean {
    if (!rolesNeeded) return true
    const list = Array.isArray(rolesNeeded) ? rolesNeeded : [rolesNeeded]
    if (list.length === 0) return true
    return list.some((r) => roles.value.includes(r))
  }

  function hasPerm(perm: string): boolean {
    if (!perm) return true
    return permissions.value.includes(perm)
  }

  /** 是否拥有任一权限码 */
  function hasAnyPerm(perms: string[]): boolean {
    if (!perms || perms.length === 0) return true
    return perms.some((p) => permissions.value.includes(p))
  }

  const isAdmin = () => roles.value.includes('admin')
  const isCollegeAdmin = () => roles.value.includes('college_admin')
  const isRepairer = () => roles.value.includes('repairer')
  const isStaff = () => isAdmin() || isCollegeAdmin()   // 教职工（管理员）
  const isStudent = () => !isStaff() && !isRepairer()   // 师生

  return {
    token,
    userInfo,
    roles,
    permissions,
    login,
    logout,
    fetchUserInfo,
    fetchPerms,
    hasRole,
    hasPerm,
    hasAnyPerm,
    isAdmin,
    isCollegeAdmin,
    isRepairer,
    isStaff,
    isStudent,
  }
})
