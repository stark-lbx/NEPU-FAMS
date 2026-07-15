import request from './request'

export const loginApi = (data: { username: string; password: string }) =>
  request.post('/auth/login', data)
export const getUserInfoApi = () => request.get('/user/profile')
export const changePasswordApi = (data: { old_password: string; new_password: string }) =>
  request.put('/user/password', data)

export const listUsersApi = (params: any) => request.get('/user/list', { params })
export const createUserApi = (data: any) => request.post('/user', data)
export const updateUserApi = (data: any) => request.put('/user', data)
export const deleteUserApi = (id: number) => request.delete(`/user/${id}`)

export const listRolesApi = (params: any) => request.get('/role/list', { params })
export const getDeptTreeApi = () => request.get('/dept/tree')
export const listRepairersApi = () => request.get('/user/repairers')

/**
 * 当前用户的权限码列表（后端只返回 perms，不再返回菜单树）
 * GET /api/user/perms →  [ "system:user:list", "system:asset:create", ... ]
 */
export const getUserPermsApi = () => request.get('/user/perms')
