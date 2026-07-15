<template>
  <div class="page-container">
    <el-page-header :icon="ArrowLeft" content="返回资产列表" @back="$router.push('/assets')">
      <template #content>
        <span class="page-title-inline">
          <el-icon><Box /></el-icon> 资产详情
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
                <el-tag :type="ASSET_STATUS_TYPE[detail.status] || 'info'">
                  {{ ASSET_STATUS_NAME[detail.status] || detail.status_name }}
                </el-tag>
              </div>
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="资产编号">{{ detail.asset_code }}</el-descriptions-item>
              <el-descriptions-item label="资产名称">{{ detail.asset_name }}</el-descriptions-item>
              <el-descriptions-item label="规格型号">{{ detail.spec || '-' }}</el-descriptions-item>
              <el-descriptions-item label="分类">{{ detail.category_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="账面价值">¥{{ formatMoney(detail.book_value) }}</el-descriptions-item>
              <el-descriptions-item label="购置日期">{{ detail.purchase_date || '-' }}</el-descriptions-item>
              <el-descriptions-item label="归属学院">{{ detail.dept_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="存放地点">{{ detail.location || '-' }}</el-descriptions-item>
              <el-descriptions-item label="使用人">{{ detail.user_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="供应商">{{ detail.supplier || '-' }}</el-descriptions-item>
              <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>

        <el-col :span="10">
          <el-card shadow="never" class="mb-12">
            <template #header><span>快捷操作</span></template>
            <div class="action-grid">
              <!-- 领用：仅 IDLE 闲置可发起；非校管/院管必须本部门 -->
              <el-tooltip v-if="!canBorrow" :content="borrowTip" placement="top">
                <el-button :icon="Document" disabled>发起领用</el-button>
              </el-tooltip>
              <el-button v-else :icon="Document" @click="openApplyDialog('BORROW', detail.asset_code)">发起领用</el-button>

              <!-- 归还：仅 USING 在用 + 资产 user_id = 当前用户本人（校管/院管除外） -->
              <el-tooltip v-if="!canReturn" :content="returnTip" placement="top">
                <el-button :icon="RefreshRight" disabled>发起归还</el-button>
              </el-tooltip>
              <el-button v-else :icon="RefreshRight" @click="openApplyDialog('RETURN', detail.asset_code)">发起归还</el-button>

              <!-- 报修：仅 IDLE/USING 可报；非校管/院管必须本部门 -->
              <el-tooltip v-if="!canRepair" :content="repairTip" placement="top">
                <el-button :icon="Tools" disabled>发起报修</el-button>
              </el-tooltip>
              <el-button v-else :icon="Tools" @click="openRepairDialog(detail.asset_code)">发起报修</el-button>

              <!-- 报废：仅校管/院管 + 闲置 -->
              <el-tooltip v-if="!canScrap" :content="scrapTip" placement="top">
                <el-button :icon="Delete" type="danger" plain disabled>发起报废</el-button>
              </el-tooltip>
              <el-button
                v-else
                :icon="Delete" type="danger" plain
                @click="openApplyDialog('SCRAP', detail.asset_code)"
              >发起报废</el-button>
            </div>
          </el-card>

          <el-card shadow="never">
            <template #header><span>操作日志</span></template>
            <el-timeline v-if="logs.length">
              <el-timeline-item v-for="(l, i) in logs" :key="i" :timestamp="formatDate(l.create_time)">
                {{ l.action }} - {{ l.operator_name || l.user_id }} - {{ l.remark || '' }}
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无操作日志" :image-size="60" />
          </el-card>
        </el-col>
      </el-row>
    </template>
    <el-empty v-else description="未找到该资产" />

    <!-- 申请/报修弹窗（复用） -->
    <el-dialog v-model="applyDialog.visible" :title="`发起${APPLY_TYPE_NAME[applyDialog.type]}申请`" width="520px" destroy-on-close>
      <el-form ref="applyFormRef" :model="applyDialog.form" :rules="applyDialogRules" label-width="90px" size="default">
        <el-form-item label="资产编号" prop="asset_code">
          <el-input v-model="applyDialog.form.asset_code" placeholder="请输入资产编号" @blur="onAssetCodeBlur">
            <template #append>
              <el-button @click="onAssetCodeBlur"><el-icon><Search /></el-icon></el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="资产名称">
          <el-input v-model="applyDialog.form.asset_name" disabled />
        </el-form-item>
        <el-form-item v-if="applyDialog.type !== 'RETURN'" label="资产状态">
          <el-tag v-if="applyDialog.form.asset_status_name" :type="ASSET_STATUS_TYPE[applyDialog.form.asset_status] || 'info'" size="small">
            {{ applyDialog.form.asset_status_name }}
          </el-tag>
          <span v-else class="text-muted">-</span>
        </el-form-item>
        <!-- 预计归还时间：仅 BORROW 显示，可选 -->
        <el-form-item v-if="applyDialog.type === 'BORROW'" label="预计归还">
          <el-date-picker
            v-model="applyDialog.form.expect_return_time"
            type="datetime"
            placeholder="可选，例：2026-08-15 18:00"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="applyDialog.form.remark" type="textarea" :rows="3" placeholder="可填写使用目的/归还原因/报废原因等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="applyDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="applyDialog.loading" @click="onSubmitApply">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="repairDialog.visible" title="发起报修" width="520px" destroy-on-close>
      <el-form ref="repairFormRef" :model="repairDialog.form" :rules="repairDialogRules" label-width="90px" size="default">
        <el-form-item label="资产编号" prop="asset_code">
          <el-input v-model="repairDialog.form.asset_code" placeholder="请输入资产编号" @blur="onRepairAssetBlur">
            <template #append>
              <el-button @click="onRepairAssetBlur"><el-icon><Search /></el-icon></el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="资产名称">
          <el-input v-model="repairDialog.form.asset_name" disabled />
        </el-form-item>
        <el-form-item label="故障描述" prop="fault_desc">
          <el-input v-model="repairDialog.form.fault_desc" type="textarea" :rows="4" placeholder="请详细描述故障现象" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="repairDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="repairDialog.loading" @click="onSubmitRepair">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  Box, ArrowLeft, Document, RefreshRight, Tools, Delete, Search,
} from '@element-plus/icons-vue'
import { getAssetDetailApi } from '@/api/asset'
import { formatMoney, formatDate } from '@/utils/format'
import { ASSET_STATUS_NAME, ASSET_STATUS_TYPE, APPLY_TYPE_NAME } from '@/types'
import { useUserStore } from '@/store/user'
import { useApplyDialog } from '@/composables/useApplyDialog'

const userStore = useUserStore()
const route = useRoute()
const id = Number(route.params.id)

const loading = ref(false)
const detail = ref<any>(null)
const logs = ref<any[]>([])

const {
  applyFormRef, applyDialog, applyDialogRules,
  repairFormRef, repairDialog, repairDialogRules,
  openApplyDialog, openRepairDialog,
  onAssetCodeBlur, onRepairAssetBlur,
  onSubmitApply, onSubmitRepair,
} = useApplyDialog()

/** 当前用户是否校管/院管（无部门限制） */
const isStaff = computed(() => userStore.hasRole(['admin', 'college_admin']))

/** 领用：仅 IDLE 闲置 + 部门归属校验 */
const canBorrow = computed(() => {
  if (!detail.value) return false
  if (detail.value.status !== 1) return false  // 必须闲置
  if (isStaff.value) return true               // 校管/院管不限部门
  const myDept = userStore.userInfo?.dept_id
  const assetDept = detail.value.dept_id
  return !myDept || !assetDept || assetDept === myDept
})
const borrowTip = computed(() => {
  if (!detail.value) return '资产信息加载中'
  if (detail.value.status !== 1) return '仅【闲置】状态的资产可发起领用'
  if (!isStaff.value && userStore.userInfo?.dept_id && detail.value.dept_id !== userStore.userInfo.dept_id) {
    return '仅可领用本部门资产'
  }
  return ''
})

/** 归还：仅 USING 在用 + 必须是当前使用人（谁借谁还，校管/院管也不允许代发起） */
const canReturn = computed(() => {
  if (!detail.value) return false
  if (detail.value.status !== 2) return false
  return detail.value.user_id === userStore.userInfo?.user_id
})
const returnTip = computed(() => {
  if (!detail.value) return '资产信息加载中'
  if (detail.value.status !== 2) return '仅【在用】状态的资产可发起归还'
  if (detail.value.user_id !== userStore.userInfo?.user_id) {
    return '仅资产当前使用人本人可发起归还，无法代他人发起'
  }
  return ''
})

/** 报修：仅 IDLE 闲置 + 部门归属校验（按业务规则，闲置资产才能发起报修） */
const canRepair = computed(() => {
  if (!detail.value) return false
  if (detail.value.status !== 1) return false  // 仅 IDLE 可报修
  if (isStaff.value) return true
  const myDept = userStore.userInfo?.dept_id
  const assetDept = detail.value.dept_id
  return !myDept || !assetDept || assetDept === myDept
})
const repairTip = computed(() => {
  if (!detail.value) return '资产信息加载中'
  if (detail.value.status !== 1) return '仅【闲置】状态的资产可发起报修'
  if (!isStaff.value && userStore.userInfo?.dept_id && detail.value.dept_id !== userStore.userInfo.dept_id) {
    return '仅可报修本部门资产'
  }
  return ''
})

/** 报废：仅校管/院管 + 闲置 */
const canScrap = computed(() => {
  if (!detail.value) return false
  if (!isStaff.value) return false
  return detail.value.status === 1
})
const scrapTip = computed(() => {
  if (!isStaff.value) return '仅校管/院管可发起报废'
  if (detail.value && detail.value.status !== 1) return '仅【闲置】状态的资产可发起报废'
  return ''
})

async function fetchDetail() {
  loading.value = true
  try {
    const res: any = await getAssetDetailApi(id)
    detail.value = res?.data || null
    logs.value = detail.value?.logs || []
  } finally {
    loading.value = false
  }
}

onMounted(fetchDetail)
</script>

<style scoped>
.page-title-inline {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
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
.action-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.action-grid .el-button { width: 100%; }
</style>
