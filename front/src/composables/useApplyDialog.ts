/**
 * 统一申请/报修弹窗 composable
 * 资产详情页、流程中心、我的申请页均可复用
 */
import { reactive, ref } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import {
  submitBorrowApi, submitReturnApi, submitScrapApi, submitRepairApi,
} from '@/api/workflow'
import { listAssetsApi } from '@/api/asset'
import { useUserStore } from '@/store/user'
import { APPLY_TYPE_NAME, ASSET_STATUS_NAME, ASSET_STATUS_TYPE } from '@/types'

export type ApplyType = 'BORROW' | 'RETURN' | 'SCRAP'

export function useApplyDialog() {
  const userStore = useUserStore()

  // ===== 申请弹窗 =====
  const applyFormRef = ref<FormInstance>()
  const applyDialog = reactive({
    visible: false,
    type: 'BORROW' as ApplyType,
    loading: false,
    form: {
      asset_id: 0,
      asset_code: '',
      asset_name: '',
      asset_status: 0,
      asset_status_name: '',
      asset_user_id: 0,
      asset_dept_id: 0,
      // 预计归还时间（领用 BORROW 时使用，可选；SCRAP 不需要）
      expect_return_time: '',
      remark: '',
    },
  })
  const applyDialogRules = {
    asset_code: [{ required: true, message: '请输入资产编号', trigger: 'blur' }],
    remark: [{ max: 500, message: '备注不超过 500 字', trigger: 'blur' }],
  }

  // ===== 报修弹窗 =====
  const repairFormRef = ref<FormInstance>()
  const repairDialog = reactive({
    visible: false,
    loading: false,
    form: {
      asset_id: 0,
      asset_code: '',
      asset_name: '',
      asset_status: 0,
      asset_status_name: '',
      asset_dept_id: 0,
      fault_desc: '',
    },
  })
  const repairDialogRules = {
    asset_code: [{ required: true, message: '请输入资产编号', trigger: 'blur' }],
    fault_desc: [{ required: true, message: '请填写故障描述', trigger: 'blur' }],
  }

  /** 打开申请弹窗，presetAssetCode 可选：从资产详情预填 */
  function openApplyDialog(type: ApplyType, presetAssetCode?: string) {
    if (type === 'SCRAP' && !userStore.hasRole(['admin', 'college_admin'])) {
      ElMessage.warning('报废申请仅管理员/院管可发起')
      return
    }
    applyDialog.type = type
    applyDialog.form = {
      asset_id: 0,
      asset_code: presetAssetCode || '',
      asset_name: '',
      asset_status: 0,
      asset_status_name: '',
      asset_user_id: 0,
      asset_dept_id: 0,
      expect_return_time: '',
      remark: '',
    }
    applyDialog.visible = true
    if (presetAssetCode) {
      // 异步查询资产
      void onAssetCodeBlur()
    }
  }

  function openRepairDialog(presetAssetCode?: string) {
    repairDialog.form = {
      asset_id: 0,
      asset_code: presetAssetCode || '',
      asset_name: '',
      asset_status: 0,
      asset_status_name: '',
      asset_dept_id: 0,
      fault_desc: '',
    }
    repairDialog.visible = true
    if (presetAssetCode) {
      void onRepairAssetBlur()
    }
  }

  async function findAssetByCode(code: string): Promise<any | null> {
    if (!code?.trim()) return null
    try {
      const res: any = await listAssetsApi({ keyword: code.trim(), page_num: 1, page_size: 5 })
      const list = res?.data?.list || []
      return list.find((a: any) => a.asset_code === code.trim()) || list[0] || null
    } catch {
      return null
    }
  }

  async function onAssetCodeBlur() {
    const a = await findAssetByCode(applyDialog.form.asset_code)
    if (!a) {
      applyDialog.form.asset_id = 0
      applyDialog.form.asset_name = ''
      applyDialog.form.asset_status = 0
      applyDialog.form.asset_status_name = ''
      applyDialog.form.asset_user_id = 0
      applyDialog.form.asset_dept_id = 0
      return
    }
    // 兼容两种字段名：
    //   - get_asset_by_id 返回 a.status（详情接口）
    //   - list_assets 返回 a.status_id（列表接口，别名）
    const statusId = (a.status_id ?? a.status ?? 0) as number
    applyDialog.form.asset_id = a.asset_id
    applyDialog.form.asset_name = a.asset_name
    applyDialog.form.asset_status = statusId
    applyDialog.form.asset_status_name =
      ASSET_STATUS_NAME[statusId] || a.status_name || `状态${statusId}`
    // 归属信息（用于前端二次校验：仅本人可归还、仅本部门可申请）
    applyDialog.form.asset_user_id = a.user_id ?? 0
    applyDialog.form.asset_dept_id = a.dept_id ?? 0
  }

  async function onRepairAssetBlur() {
    const a = await findAssetByCode(repairDialog.form.asset_code)
    if (a) {
      repairDialog.form.asset_id = a.asset_id
      repairDialog.form.asset_name = a.asset_name
      const statusId = (a.status_id ?? a.status ?? 0) as number
      repairDialog.form.asset_status = statusId
      repairDialog.form.asset_status_name = a.status_name || `状态${statusId}`
      repairDialog.form.asset_dept_id = a.dept_id ?? 0
    } else {
      repairDialog.form.asset_id = 0
      repairDialog.form.asset_name = ''
      repairDialog.form.asset_status = 0
      repairDialog.form.asset_status_name = ''
      repairDialog.form.asset_dept_id = 0
    }
  }

  async function onSubmitApply() {
    const valid = await applyFormRef.value?.validate().catch(() => false)
    if (!valid) return
    if (!applyDialog.form.asset_id) {
      ElMessage.warning('未找到该资产，请输入有效的资产编号')
      return
    }
    if (applyDialog.type === 'BORROW' && applyDialog.form.asset_status !== 1) {
      ElMessage.warning('仅【闲置】状态的资产可发起领用')
      return
    }
    if (applyDialog.type === 'RETURN' && applyDialog.form.asset_status !== 2) {
      ElMessage.warning('仅【在用】状态的资产可发起归还')
      return
    }
    if (applyDialog.type === 'SCRAP' && applyDialog.form.asset_status !== 1) {
      ElMessage.warning('仅【闲置】状态的资产可发起报废')
      return
    }
    // === 角色 / 归属前端二次校验（防御性，最终以服务端校验为准） ===
    const isStaff = userStore.hasRole(['admin', 'college_admin'])
    if (applyDialog.type === 'SCRAP' && !isStaff) {
      ElMessage.warning('报废申请仅校管/院管可发起')
      return
    }
    const myUserId = userStore.userInfo?.user_id
    const myDept = userStore.userInfo?.dept_id
    // 关键：归还必须是当前使用人本人，校管/院管也不能代发起
    if (applyDialog.type === 'RETURN'
        && applyDialog.form.asset_user_id
        && applyDialog.form.asset_user_id !== myUserId) {
      ElMessage.warning('仅资产当前使用人本人可发起归还，无法代他人发起')
      return
    }
    if ((applyDialog.type === 'BORROW' || applyDialog.type === 'SCRAP') && !isStaff
        && myDept && applyDialog.form.asset_dept_id && applyDialog.form.asset_dept_id !== myDept) {
      ElMessage.warning('仅可对本部门资产发起申请')
      return
    }
    applyDialog.loading = true
    try {
      // 后端 SQL 字段是 reason，不是 remark
      // 预计归还时间仅 BORROW 使用，可选
      const payload: any = {
        asset_id: applyDialog.form.asset_id,
        reason: applyDialog.form.remark,
      }
      if (applyDialog.type === 'BORROW' && applyDialog.form.expect_return_time) {
        payload.expect_return_time = applyDialog.form.expect_return_time
      }
      if (applyDialog.type === 'BORROW') await submitBorrowApi(payload)
      else if (applyDialog.type === 'RETURN') await submitReturnApi(payload)
      else await submitScrapApi(payload)
      ElMessage.success(`${APPLY_TYPE_NAME[applyDialog.type]}申请已提交，等待审批`)
      applyDialog.visible = false
    } finally {
      applyDialog.loading = false
    }
  }

  async function onSubmitRepair() {
    const valid = await repairFormRef.value?.validate().catch(() => false)
    if (!valid) return
    if (!repairDialog.form.asset_id) {
      ElMessage.warning('未找到该资产，请输入有效的资产编号')
      return
    }
    // 部门归属校验
    const isStaff = userStore.hasRole(['admin', 'college_admin'])
    const myDept = userStore.userInfo?.dept_id
    if (!isStaff && myDept && repairDialog.form.asset_dept_id && repairDialog.form.asset_dept_id !== myDept) {
      ElMessage.warning('仅可对本部门资产发起报修')
      return
    }
    // 状态校验（按业务规则：仅 IDLE 闲置可报修）
    if (repairDialog.form.asset_status && repairDialog.form.asset_status !== 1) {
      ElMessage.warning('仅【闲置】状态的资产可发起报修')
      return
    }
    repairDialog.loading = true
    try {
      await submitRepairApi({
        asset_id: repairDialog.form.asset_id,
        fault_desc: repairDialog.form.fault_desc,
      })
      ElMessage.success('报修工单已提交')
      repairDialog.visible = false
    } finally {
      repairDialog.loading = false
    }
  }

  return {
    applyFormRef, applyDialog, applyDialogRules,
    repairFormRef, repairDialog, repairDialogRules,
    openApplyDialog, openRepairDialog,
    onAssetCodeBlur, onRepairAssetBlur,
    onSubmitApply, onSubmitRepair,
  }
}
