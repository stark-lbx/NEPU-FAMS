<template>
  <div class="page-container">
    <el-page-header :icon="ArrowLeft" content="返回流程管理" @back="$router.push('/workflows')">
      <template #content>
        <span class="page-title-inline">
          <el-icon><Tools /></el-icon> 工单详情 #{{ id }}
        </span>
      </template>
    </el-page-header>

    <el-skeleton v-if="loading" :rows="6" animated class="mt-16" />
    <template v-else-if="detail">
      <el-row :gutter="12" class="mt-16">
        <el-col :span="14">
          <el-card shadow="never">
            <template #header>
              <div class="card-hd">
                <span>基本信息</span>
                <el-tag :type="REPAIR_STATUS_TYPE[detail.status] || 'info'">
                  {{ REPAIR_STATUS_NAME[detail.status] || detail.status }}
                </el-tag>
              </div>
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="资产编号">{{ detail.asset_code }}</el-descriptions-item>
              <el-descriptions-item label="资产名称" :span="2">{{ detail.asset_name }}</el-descriptions-item>
              <el-descriptions-item label="报修人">{{ detail.reporter_name }}</el-descriptions-item>
              <el-descriptions-item label="所属部门">{{ detail.dept_name }}</el-descriptions-item>
              <el-descriptions-item label="维修员">{{ detail.repairer_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="维修费用">¥{{ formatMoney(detail.repair_cost) }}</el-descriptions-item>
              <el-descriptions-item label="故障描述" :span="2">{{ detail.fault_desc }}</el-descriptions-item>
              <el-descriptions-item label="维修说明" :span="2">{{ detail.repair_detail || '-' }}</el-descriptions-item>
              <el-descriptions-item label="截止时间">{{ detail.deadline || '-' }}</el-descriptions-item>
              <el-descriptions-item label="提交时间">{{ formatDate(detail.create_time) }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card shadow="never" class="mt-12">
            <template #header><span>操作日志</span></template>
            <el-timeline>
              <el-timeline-item
                v-for="(l, i) in (detail.operation_logs || [])"
                :key="i"
                :timestamp="formatDate(l.create_time)"
              >
                <strong>{{ l.action }}</strong> - {{ l.operator_name || l.user_id }}
                <div v-if="l.remark" class="step-op">{{ l.remark }}</div>
              </el-timeline-item>
              <el-timeline-item
                v-if="!detail.operation_logs || detail.operation_logs.length === 0"
                timestamp="-"
                type="info"
              >
                暂无操作日志
              </el-timeline-item>
            </el-timeline>
          </el-card>
        </el-col>

        <el-col :span="10">
          <el-card v-if="actions.length" shadow="never" class="mb-12">
            <template #header><span>可执行操作</span></template>
            <el-form :model="opinionForm" size="default">
              <el-form-item label="审批/处理意见">
                <el-input v-model="opinionForm.opinion" type="textarea" :rows="3" placeholder="驳回/验收必填；其余可填备注" />
              </el-form-item>
              <el-form-item>
                <el-button
                  v-for="a in actions"
                  :key="a.key"
                  :type="a.btnType"
                  :loading="approving"
                  @click="onAction(a.key)"
                >{{ a.label }}</el-button>
              </el-form-item>
            </el-form>
          </el-card>
          <el-card v-else shadow="never" class="mb-12">
            <template #header><span>说明</span></template>
            <p class="text-muted">该工单当前状态下您无可执行操作。</p>
          </el-card>
        </el-col>
      </el-row>
    </template>
    <el-empty v-else description="未找到该工单" />

    <!-- 派单弹窗（仅校管） -->
    <el-dialog v-model="dispatchVisible" title="派单" width="480px" destroy-on-close>
      <el-form :model="dispatchForm" label-width="100px">
        <el-form-item label="维修工" required>
          <el-select v-model="dispatchForm.repairer_id" placeholder="请选择维修工" filterable style="width:100%">
            <el-option
              v-for="r in repairerList"
              :key="r.user_id"
              :label="r.nickname + (r.repair_specialty ? '（' + r.repair_specialty + '）' : '')"
              :value="r.user_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="截止时间">
          <el-date-picker
            v-model="dispatchForm.deadline"
            type="datetime"
            placeholder="请选择完成截止时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width:100%"
          />
        </el-form-item>
        <el-form-item label="派单备注">
          <el-input v-model="dispatchForm.remark" type="textarea" :rows="2" placeholder="可填派单备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dispatchVisible = false">取消</el-button>
        <el-button type="primary" :loading="approving" @click="confirmDispatch">确认派单</el-button>
      </template>
    </el-dialog>

    <!-- 编辑维修信息弹窗（仅维修工，REPAIR_ACCEPTED 状态） -->
    <el-dialog v-model="editVisible" title="编辑维修信息" width="480px" destroy-on-close>
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="维修说明">
          <el-input v-model="editForm.repair_detail" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="维修费用">
          <el-input-number v-model="editForm.repair_cost" :min="0" :precision="2" :step="50" style="width:100%" />
        </el-form-item>
        <el-form-item label="更换配件">
          <el-input v-model="editForm.parts_detail" type="textarea" :rows="2" placeholder="可填配件清单" />
        </el-form-item>
        <el-form-item label="发票附件">
          <el-input v-model="editForm.invoice_files" placeholder="多个用英文逗号分隔，可留空" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="approving" @click="confirmEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Tools, ArrowLeft } from '@element-plus/icons-vue'
import {
  getRepairDetailApi,
  collegeApproveApi, schoolApproveApi, acceptanceApi,
  dispatchOrderApi, acceptOrderApi, updateRepairInfoApi,
  finishRepairApi, resubmitRepairApi, listRepairersApi,
} from '@/api/workflow'
import { useUserStore } from '@/store/user'
import { formatDate, formatMoney } from '@/utils/format'
import { REPAIR_STATUS_NAME, REPAIR_STATUS_TYPE } from '@/types'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const id = Number(route.params.id)

const loading = ref(false)
const detail = ref<any>(null)
const approving = ref(false)
const opinionForm = reactive({ opinion: '' })

// 派单
const dispatchVisible = ref(false)
const dispatchForm = reactive({ repairer_id: 0 as number, deadline: '' as string, remark: '' })
const repairerList = ref<any[]>([])

// 编辑维修
const editVisible = ref(false)
const editForm = reactive({ repair_detail: '', repair_cost: 0, parts_detail: '', invoice_files: '' })

const isAdmin = computed(() => userStore.hasRole('admin'))
const isCollege = computed(() => userStore.hasRole('college_admin') && !isAdmin.value)
const isRepairer = computed(() => userStore.hasRole('repairer') && !isAdmin.value)
const me = computed(() => userStore.userInfo?.user_id)

/**
 * 根据状态 + 角色生成可执行操作按钮
 * 节点 / 角色边界（与后端路由 / 状态机严格一致）：
 *   PENDING_COLLEGE_APPROVE → 院管 college_pass/reject
 *   PENDING_SCHOOL_APPROVE  → 校管 school_pass/reject
 *   PENDING_DISPATCH        → 校管 dispatch（新增派单入口）
 *   PENDING_REPAIR          → 维修工 accept（必须派给自己）
 *   REPAIR_ACCEPTED         → 维修工 edit_repair/finish（必须派给自己）
 *   PENDING_ACCEPTANCE      → 校管 accept_pass/reject
 *   ACCEPTANCE_REJECTED     → 维修工 resubmit（必须派给自己）
 */
const actions = computed<{ key: string; label: string; btnType: 'primary' | 'success' | 'danger' | 'warning' | 'info' }[]>(() => {
  if (!detail.value) return []
  const s = detail.value.status
  const arr: any[] = []

  if (s === 'PENDING_COLLEGE_APPROVE' && isCollege.value
      && detail.value.dept_id === userStore.userInfo?.dept_id) {
    arr.push({ key: 'college_pass', label: '院级通过', btnType: 'primary' })
    arr.push({ key: 'college_reject', label: '院级驳回', btnType: 'danger' })
  }
  if (s === 'PENDING_SCHOOL_APPROVE' && isAdmin.value) {
    arr.push({ key: 'school_pass', label: '校级通过', btnType: 'primary' })
    arr.push({ key: 'school_reject', label: '校级驳回', btnType: 'danger' })
  }
  if (s === 'PENDING_DISPATCH' && isAdmin.value) {
    arr.push({ key: 'dispatch', label: '派单', btnType: 'primary' })
  }
  if (s === 'PENDING_REPAIR' && isRepairer.value
      && detail.value.repairer_id === me.value) {
    arr.push({ key: 'accept', label: '接单', btnType: 'primary' })
  }
  if (s === 'REPAIR_ACCEPTED' && isRepairer.value
      && detail.value.repairer_id === me.value) {
    arr.push({ key: 'edit_repair', label: '编辑维修信息', btnType: 'info' })
    arr.push({ key: 'finish', label: '提交完成', btnType: 'success' })
  }
  if (s === 'PENDING_ACCEPTANCE' && isAdmin.value) {
    arr.push({ key: 'accept_pass', label: '验收通过', btnType: 'success' })
    arr.push({ key: 'accept_reject', label: '验收驳回', btnType: 'danger' })
  }
  if (s === 'ACCEPTANCE_REJECTED' && isRepairer.value
      && detail.value.repairer_id === me.value) {
    arr.push({ key: 'resubmit', label: '返工后重新提交', btnType: 'primary' })
  }
  return arr
})

async function fetchDetail() {
  loading.value = true
  try {
    const res: any = await getRepairDetailApi(id)
    detail.value = res?.data || null
  } finally { loading.value = false }
}

async function fetchRepairers() {
  try {
    const res: any = await listRepairersApi()
    repairerList.value = res?.data || []
  } catch { repairerList.value = [] }
}

async function onAction(key: string) {
  // 派单：开弹窗
  if (key === 'dispatch') {
    if (repairerList.value.length === 0) await fetchRepairers()
    dispatchForm.repairer_id = 0
    dispatchForm.deadline = ''
    dispatchForm.remark = ''
    dispatchVisible.value = true
    return
  }
  // 编辑维修：开弹窗
  if (key === 'edit_repair') {
    editForm.repair_detail = detail.value?.repair_detail || ''
    editForm.repair_cost = detail.value?.repair_cost || 0
    editForm.parts_detail = detail.value?.parts_detail || ''
    editForm.invoice_files = detail.value?.invoice_files || ''
    editVisible.value = true
    return
  }
  // 重新提交：二次确认
  if (key === 'resubmit') {
    await ElMessageBox.confirm('确认返工已完成并重新提交验收？', '提示', { type: 'warning' })
    approving.value = true
    try {
      await resubmitRepairApi(id)
      ElMessage.success('已重新提交验收')
      router.push('/workflows/pending')
    } finally { approving.value = false }
    return
  }
  // 其它动作：审批/接单/完成/验收
  approving.value = true
  try {
    if (key === 'college_pass') {
      await collegeApproveApi({ order_id: id, is_pass: true, opinion: opinionForm.opinion })
    } else if (key === 'college_reject') {
      if (!opinionForm.opinion.trim()) { ElMessage.warning('请填写驳回意见'); return }
      await collegeApproveApi({ order_id: id, is_pass: false, opinion: opinionForm.opinion })
    } else if (key === 'school_pass') {
      await schoolApproveApi({ order_id: id, is_pass: true, opinion: opinionForm.opinion })
    } else if (key === 'school_reject') {
      if (!opinionForm.opinion.trim()) { ElMessage.warning('请填写驳回意见'); return }
      await schoolApproveApi({ order_id: id, is_pass: false, opinion: opinionForm.opinion })
    } else if (key === 'accept') {
      await acceptOrderApi({ order_id: id })
    } else if (key === 'finish') {
      if (!editForm.repair_detail.trim()) {
        ElMessage.warning('请先填写维修说明')
        return
      }
      // 完成前先保存最新维修信息
      await updateRepairInfoApi({
        order_id: id,
        repair_detail: editForm.repair_detail,
        repair_cost: editForm.repair_cost,
        parts_detail: editForm.parts_detail,
        invoice_files: editForm.invoice_files,
      })
      await finishRepairApi({ order_id: id })
    } else if (key === 'accept_pass') {
      await acceptanceApi({ order_id: id, is_pass: true, opinion: opinionForm.opinion })
    } else if (key === 'accept_reject') {
      if (!opinionForm.opinion.trim()) { ElMessage.warning('请填写驳回意见'); return }
      await acceptanceApi({ order_id: id, is_pass: false, opinion: opinionForm.opinion })
    }
    ElMessage.success('操作成功')
    router.push('/workflows/pending')
  } finally { approving.value = false }
}

async function confirmDispatch() {
  if (!dispatchForm.repairer_id) { ElMessage.warning('请选择维修工'); return }
  approving.value = true
  try {
    await dispatchOrderApi({
      order_id: id,
      repairer_id: dispatchForm.repairer_id,
      deadline: dispatchForm.deadline,
      remark: dispatchForm.remark,
    })
    ElMessage.success('派单成功')
    dispatchVisible.value = false
    router.push('/workflows/pending')
  } finally { approving.value = false }
}

async function confirmEdit() {
  approving.value = true
  try {
    await updateRepairInfoApi({
      order_id: id,
      repair_detail: editForm.repair_detail,
      repair_cost: editForm.repair_cost,
      parts_detail: editForm.parts_detail,
      invoice_files: editForm.invoice_files,
    })
    ElMessage.success('维修信息已保存')
    editVisible.value = false
    fetchDetail()
  } finally { approving.value = false }
}

onMounted(fetchDetail)
</script>

<style scoped>
.page-title-inline {
  font-size: 18px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.card-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
.step-op { color: #606266; font-size: 13px; margin-top: 4px; }
.text-muted { color: #909399; }
</style>