/** 通用类型定义 */

// 后端统一响应
export interface ApiResp<T = any> {
  code: number
  message: string
  data: T
}

export interface PageData<T = any> {
  list: T[]
  total: number
  page_num: number
  page_size: number
}

export interface DeptNode {
  dept_id: number
  dept_name: string
  parent_id?: number
  children?: DeptNode[]
}

export interface Role {
  role_id: number
  role_key: string
  role_name: string
}

export interface UserInfo {
  user_id: number
  username: string
  nickname: string
  dept_id: number
  dept_name?: string
  phone?: string
  email?: string
  status: number
  role_keys: string[]
  roles?: Role[]
  create_time?: string
}

export interface AssetStatus {
  status_id: number
  status_name: string
  status_code?: string
}

export interface CategoryNode {
  category_id: number
  category_name: string
  parent_id?: number
  children?: CategoryNode[]
}

export interface Asset {
  asset_id: number
  asset_code: string
  asset_name: string
  spec?: string
  category_id: number
  category_name?: string
  book_value: number
  dept_id: number
  dept_name?: string
  location?: string
  status: number
  status_name?: string
  status_code?: string
  user_id?: number
  user_name?: string
  purchase_date?: string
  version?: number
}

// 申请 (asset_apply)
export const ApplyType = { BORROW: 'BORROW', RETURN: 'RETURN', SCRAP: 'SCRAP' } as const
export type ApplyType = (typeof ApplyType)[keyof typeof ApplyType]

export const ApplyStatus = {
  PENDING_COLLEGE: 'PENDING_COLLEGE',
  PENDING_SCHOOL: 'PENDING_SCHOOL',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
  CANCELLED: 'CANCELLED',
} as const
export type ApplyStatus = (typeof ApplyStatus)[keyof typeof ApplyStatus]

export const APPLY_TYPE_NAME: Record<string, string> = {
  BORROW: '领用',
  RETURN: '归还',
  SCRAP: '报废',
}

export const APPLY_STATUS_NAME: Record<string, string> = {
  PENDING_COLLEGE: '院级待审',
  PENDING_SCHOOL: '校级待审',
  APPROVED: '已通过',
  REJECTED: '已驳回',
  CANCELLED: '已撤回',
}

export const APPLY_STATUS_TYPE: Record<string, 'primary' | 'success' | 'danger' | 'info' | 'warning'> = {
  PENDING_COLLEGE: 'warning',
  PENDING_SCHOOL: 'warning',
  APPROVED: 'success',
  REJECTED: 'danger',
  CANCELLED: 'info',
}

// 报修 (repair_order)
export const RepairStatus = {
  PENDING_COLLEGE_APPROVE: 'PENDING_COLLEGE_APPROVE',
  PENDING_SCHOOL_APPROVE: 'PENDING_SCHOOL_APPROVE',
  PENDING_DISPATCH: 'PENDING_DISPATCH',
  PENDING_REPAIR: 'PENDING_REPAIR',
  REPAIR_ACCEPTED: 'REPAIR_ACCEPTED',
  PENDING_ACCEPTANCE: 'PENDING_ACCEPTANCE',
  ACCEPTANCE_PASSED: 'ACCEPTANCE_PASSED',
  ACCEPTANCE_REJECTED: 'ACCEPTANCE_REJECTED',
} as const
export type RepairStatus = (typeof RepairStatus)[keyof typeof RepairStatus]

export const REPAIR_STATUS_NAME: Record<string, string> = {
  PENDING_COLLEGE_APPROVE: '院级待审',
  PENDING_SCHOOL_APPROVE: '校级待审',
  PENDING_DISPATCH: '待派单',
  PENDING_REPAIR: '维修中',
  REPAIR_ACCEPTED: '维修完成',
  PENDING_ACCEPTANCE: '待验收',
  ACCEPTANCE_PASSED: '已通过',
  ACCEPTANCE_REJECTED: '已驳回',
}

export const REPAIR_STATUS_TYPE: Record<string, 'primary' | 'success' | 'danger' | 'info' | 'warning'> = {
  PENDING_COLLEGE_APPROVE: 'warning',
  PENDING_SCHOOL_APPROVE: 'warning',
  PENDING_DISPATCH: 'primary',
  PENDING_REPAIR: 'primary',
  REPAIR_ACCEPTED: 'primary',
  PENDING_ACCEPTANCE: 'warning',
  ACCEPTANCE_PASSED: 'success',
  ACCEPTANCE_REJECTED: 'danger',
}

// 资产状态 (数字)
export const ASSET_STATUS_NAME: Record<number, string> = {
  0: '未知',
  1: '闲置',
  2: '在用',
  3: '维修中',
  4: '报废',
  5: '流转中',
}
export const ASSET_STATUS_TYPE: Record<number, 'primary' | 'success' | 'danger' | 'info' | 'warning'> = {
  1: 'success',
  2: 'primary',
  3: 'warning',
  4: 'danger',
  5: 'info',
  0: 'info',
}
