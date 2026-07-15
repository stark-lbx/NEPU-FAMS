<template>
  <div class="page-container">
    <el-page-header :icon="ArrowLeft" content="返回流程管理" @back="$router.push('/workflows')">
      <template #content>
        <span class="page-title-inline">
          <el-icon><Document /></el-icon> 申请详情 #{{ id }}
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
                <el-tag :type="APPLY_STATUS_TYPE[detail.status] || 'info'">
                  {{ APPLY_STATUS_NAME[detail.status] || detail.status }}
                </el-tag>
              </div>
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="申请类型">
                <el-tag size="small">{{ APPLY_TYPE_NAME[detail.apply_type] || detail.apply_type }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="资产编号">{{ detail.asset_code }}</el-descriptions-item>
              <el-descriptions-item label="资产名称" :span="2">{{ detail.asset_name }}</el-descriptions-item>
              <el-descriptions-item label="申请人">{{ detail.applicant_name }}</el-descriptions-item>
              <el-descriptions-item label="所属部门">{{ detail.dept_name }}</el-descriptions-item>
              <el-descriptions-item label="预计归还时间" v-if="detail.apply_type === 'BORROW'">
                {{ formatDate(detail.expect_return_time) }}
              </el-descriptions-item>
              <el-descriptions-item label="提交时间">{{ formatDate(detail.create_time) }}</el-descriptions-item>
              <el-descriptions-item label="完成时间" :span="2">{{ formatDate(detail.finish_time) }}</el-descriptions-item>
              <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card shadow="never" class="mt-12">
            <template #header><span>审批流程</span></template>
            <el-timeline>
              <el-timeline-item
                v-for="(s, i) in (detail.approve_records || [])"
                :key="i"
                :timestamp="formatDate(s.create_time)"
                :type="stepType(s.action)"
              >
                <div class="step-title">
                  <strong>{{ s.node_name || `第${i + 1}节点` }}</strong>
                  <el-tag size="small" :type="stepTagType(s.action)">
                    {{ stepLabel(s.action) }}
                  </el-tag>
                </div>
                <div class="step-meta">
                  {{ s.approver_name || '系统' }} · {{ s.dept_name || '' }}
                </div>
                <div v-if="s.opinion" class="step-op">
                  {{ s.action === 'SUBMIT' ? '申请理由' : '审批意见' }}：{{ s.opinion }}
                </div>
              </el-timeline-item>
              <el-timeline-item
                v-if="!detail.approve_records || detail.approve_records.length === 0"
                timestamp="-"
                type="info"
              >
                暂无审批记录
              </el-timeline-item>
            </el-timeline>
          </el-card>
        </el-col>

        <el-col :span="10">
          <!-- 审批操作 -->
          <el-card v-if="canApprove" shadow="never" class="mb-12">
            <template #header><span>审批操作</span></template>
            <el-form :model="opinionForm" size="default">
              <el-form-item label="审批意见">
                <el-input v-model="opinionForm.opinion" type="textarea" :rows="4" placeholder="请输入审批意见" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="approving" @click="onApprove">通过</el-button>
                <el-button type="danger" :loading="approving" @click="onReject">驳回</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <!-- 申请人撤回 -->
          <el-card
            v-else-if="canCancel"
            shadow="never"
            class="mb-12"
          >
            <template #header><span>撤回申请</span></template>
            <p class="text-muted">当前申请未完成，您可以主动撤回。</p>
            <el-button type="warning" @click="onCancel">撤回</el-button>
          </el-card>

          <el-card v-else shadow="never" class="mb-12">
            <template #header><span>说明</span></template>
            <p class="text-muted">该申请您无操作权限。</p>
          </el-card>
        </el-col>
      </el-row>
    </template>
    <el-empty v-else description="未找到该申请" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, ArrowLeft } from '@element-plus/icons-vue'
import { getApplyDetailApi, approveApplyApi, cancelApplyApi } from '@/api/workflow'
import { useUserStore } from '@/store/user'
import { formatDate } from '@/utils/format'
import { APPLY_STATUS_NAME, APPLY_STATUS_TYPE, APPLY_TYPE_NAME } from '@/types'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const id = Number(route.params.id)

const loading = ref(false)
const detail = ref<any>(null)
const approving = ref(false)
const opinionForm = reactive({ opinion: '' })

const canApprove = computed(() => {
  if (!detail.value) return false
  if (!userStore.userInfo?.user_id) return false
  if (!['PENDING_COLLEGE', 'PENDING_SCHOOL'].includes(detail.value.status)) return false
  if (userStore.hasRole('admin')) return true
  if (userStore.hasRole('college_admin')) {
    if (detail.value.status !== 'PENDING_COLLEGE') return false
    return detail.value.dept_id === userStore.userInfo?.dept_id
  }
  return false
})

const canCancel = computed(() => {
  if (!detail.value) return false
  return (
    detail.value.applicant_id === userStore.userInfo?.user_id &&
    ['PENDING_COLLEGE', 'PENDING_SCHOOL'].includes(detail.value.status)
  )
})

/** 流程节点 type 颜色 */
function stepType(action: string): 'success' | 'danger' | 'primary' | 'info' {
  if (action === 'APPROVE') return 'success'
  if (action === 'REJECT') return 'danger'
  if (action === 'SUBMIT') return 'primary'
  return 'info'
}
function stepTagType(action: string): 'success' | 'danger' | 'primary' | 'info' {
  return stepType(action)
}
function stepLabel(action: string): string {
  if (action === 'APPROVE') return '通过'
  if (action === 'REJECT') return '驳回'
  if (action === 'SUBMIT') return '已提交'
  return action
}

async function fetchDetail() {
  loading.value = true
  try {
    const res: any = await getApplyDetailApi(id)
    detail.value = res?.data || null
  } finally {
    loading.value = false
  }
}

async function onApprove() {
  approving.value = true
  try {
    await approveApplyApi({ apply_id: id, action: 'APPROVE', opinion: opinionForm.opinion })
    ElMessage.success('已通过')
    router.push('/workflows')
  } finally { approving.value = false }
}

async function onReject() {
  if (!opinionForm.opinion.trim()) {
    ElMessage.warning('请填写驳回意见')
    return
  }
  approving.value = true
  try {
    await approveApplyApi({ apply_id: id, action: 'REJECT', opinion: opinionForm.opinion })
    ElMessage.success('已驳回')
    router.push('/workflows')
  } finally { approving.value = false }
}

async function onCancel() {
  await ElMessageBox.confirm('确定撤回该申请？', '提示', { type: 'warning' })
  await cancelApplyApi(id, opinionForm.opinion)
  ElMessage.success('已撤回')
  router.push('/workflows')
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
.step-title { display: flex; align-items: center; gap: 8px; }
.step-meta { color: #909399; font-size: 12px; margin-top: 2px; }
.step-op { color: #606266; font-size: 13px; margin-top: 4px; }
</style>
