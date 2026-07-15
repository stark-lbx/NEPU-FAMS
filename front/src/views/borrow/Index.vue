<template>
  <div class="page-container">
    <div class="page-title">
      <el-icon><Goods /></el-icon> 我的申请
    </div>

    <!-- 概览 KPI -->
    <el-row :gutter="12" class="kpi-row">
      <el-col :xs="12" :sm="6">
        <el-card class="kpi-card" shadow="hover">
          <div class="kpi-inner" style="--c:#409EFF">
            <el-icon class="kpi-icon"><Box /></el-icon>
            <div>
              <div class="kpi-num">{{ kpi.using }}</div>
              <div class="kpi-label">领用中资产</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card class="kpi-card" shadow="hover">
          <div class="kpi-inner" style="--c:#67C23A">
            <el-icon class="kpi-icon"><Document /></el-icon>
            <div>
              <div class="kpi-num">{{ kpi.pendingApply }}</div>
              <div class="kpi-label">申请进行中</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card class="kpi-card" shadow="hover">
          <div class="kpi-inner" style="--c:#E6A23C">
            <el-icon class="kpi-icon"><Tools /></el-icon>
            <div>
              <div class="kpi-num">{{ kpi.repairing }}</div>
              <div class="kpi-label">维修中</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card class="kpi-card" shadow="hover">
          <div class="kpi-inner" style="--c:#F56C6C">
            <el-icon class="kpi-icon"><Warning /></el-icon>
            <div>
              <div class="kpi-num">{{ kpi.acceptance }}</div>
              <div class="kpi-label">待我验收</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Tab：领用资产 / 维修工单 / 历史 -->
    <el-tabs v-model="tab" class="mt-12">
      <el-tab-pane label="领用资产" name="borrowed">
        <el-card shadow="never">
          <template #header>
            <div class="card-hd">
              <span>我正在使用的资产 ({{ borrowedAssets.length }})</span>
              <el-button type="success" size="small" :disabled="selectedAssets.length === 0" @click="batchReturn">
                批量归还 ({{ selectedAssets.length }})
              </el-button>
            </div>
          </template>
          <el-table
            v-loading="loading"
            :data="displayBorrowed"
            stripe
            border
            @selection-change="(rows: any[]) => (selectedAssets = rows)"
            @sort-change="handleSortChange"
          >
            <el-table-column v-if="borrowedAssets.length" type="selection" width="42" />
            <el-table-column prop="asset_code" label="编号" width="130" sortable="custom" />
            <el-table-column prop="asset_name" label="资产名称" min-width="180" show-overflow-tooltip sortable="custom" />
            <el-table-column prop="category_name" label="分类" width="120" sortable="custom" />
            <el-table-column prop="book_value" label="价值" width="100" sortable="custom">
              <template #default="{ row }">¥{{ formatMoney(row.book_value) }}</template>
            </el-table-column>
            <el-table-column prop="dept_name" label="归属" min-width="140" show-overflow-tooltip sortable="custom" />
            <el-table-column prop="location" label="存放点" width="140" show-overflow-tooltip sortable="custom" />
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="$router.push(`/assets/detail/${row.asset_id}`)">详情</el-button>
                <el-tooltip v-if="!canReturnAsset(row)" content="仅资产当前使用人本人可发起归还，无法代他人发起" placement="top">
                  <el-button type="success" link size="small" disabled>归还</el-button>
                </el-tooltip>
                <el-button v-else type="success" link size="small" @click="quickReturn(row)">归还</el-button>
                <el-tooltip v-if="!canRepairAsset(row)" content="仅【闲置】资产可报修，且仅限本部门" placement="top">
                  <el-button type="warning" link size="small" disabled>报修</el-button>
                </el-tooltip>
                <el-button v-else type="warning" link size="small" @click="quickRepair(row)">报修</el-button>
              </template>
            </el-table-column>
            <template #empty><el-empty description="暂未领用资产" /></template>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="维修工单" name="repair">
        <el-card shadow="never">
          <template #header>
            <div class="card-hd">
              <span>我的维修工单 ({{ myOrders.length }})</span>
            </div>
          </template>
          <el-table v-loading="loading" :data="displayOrders" stripe border @sort-change="handleSortChange">
            <el-table-column prop="order_id" label="工单号" width="80" sortable="custom" />
            <el-table-column prop="asset_name" label="资产" min-width="160" show-overflow-tooltip sortable="custom" />
            <el-table-column prop="fault_desc" label="故障" min-width="160" show-overflow-tooltip sortable="custom" />
            <el-table-column prop="status" label="状态" width="110" sortable="custom">
              <template #default="{ row }">
                <el-tag :type="REPAIR_STATUS_TYPE[row.status] || 'info'" size="small">
                  {{ REPAIR_STATUS_NAME[row.status] || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="create_time" label="提交时间" width="160" sortable="custom">
              <template #default="{ row }">{{ formatDate(row.create_time) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="$router.push(`/workflows/repair/${row.order_id}`)">详情</el-button>
              </template>
            </el-table-column>
            <template #empty><el-empty description="暂无维修工单" /></template>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="我的申请" name="apply">
        <el-card shadow="never">
          <template #header>
            <div class="card-hd">
              <span>我的领用/归还/报废申请 ({{ myApplies.length }})</span>
              <el-button type="primary" size="small" @click="openApplyDialog('BORROW')">去发起</el-button>
            </div>
          </template>
          <el-table v-loading="loading" :data="displayApplies" stripe border @sort-change="handleSortChange">
            <el-table-column prop="apply_id" label="#" width="60" sortable="custom" />
            <el-table-column prop="asset_name" label="资产" min-width="160" show-overflow-tooltip sortable="custom" />
            <el-table-column prop="apply_type" label="类型" width="80" sortable="custom">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ APPLY_TYPE_NAME[row.apply_type] }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100" sortable="custom">
              <template #default="{ row }">
                <el-tag :type="APPLY_STATUS_TYPE[row.status] || 'info'" size="small">
                  {{ APPLY_STATUS_NAME[row.status] }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="create_time" label="提交时间" width="160" sortable="custom">
              <template #default="{ row }">{{ formatDate(row.create_time) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="$router.push(`/workflows/apply/${row.apply_id}`)">详情</el-button>
              </template>
            </el-table-column>
            <template #empty><el-empty description="暂无申请" /></template>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 申请/报修弹窗（复用 composable） -->
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Goods, Box, Document, Tools, Warning, Search } from '@element-plus/icons-vue'
import { listAssetsApi } from '@/api/asset'
import {
  listMyAppliesApi, listRepairOrdersApi,
  submitReturnApi,
} from '@/api/workflow'
import { useUserStore } from '@/store/user'
import { useTableSort } from '@/composables/useTableSort'
import { useApplyDialog } from '@/composables/useApplyDialog'
import { formatDate, formatMoney } from '@/utils/format'
import {
  APPLY_TYPE_NAME, APPLY_STATUS_NAME, APPLY_STATUS_TYPE,
  REPAIR_STATUS_NAME, REPAIR_STATUS_TYPE,
  ASSET_STATUS_TYPE,
} from '@/types'

const router = useRouter()
const userStore = useUserStore()
const { handleSortChange, applySort } = useTableSort()
const {
  applyFormRef, applyDialog, applyDialogRules,
  repairFormRef, repairDialog, repairDialogRules,
  openApplyDialog, openRepairDialog,
  onAssetCodeBlur, onRepairAssetBlur,
  onSubmitApply, onSubmitRepair,
} = useApplyDialog()

const tab = ref<'borrowed' | 'repair' | 'apply'>('borrowed')
const loading = ref(false)

const allAssets = ref<any[]>([])
const myApplies = ref<any[]>([])
const myOrders = ref<any[]>([])
const selectedAssets = ref<any[]>([])

/** 我正在领用中的资产：user_id 匹配我自己 且 status=2(USING) */
const borrowedAssets = computed(() => {
  const me = userStore.userInfo?.user_id
  return allAssets.value.filter((a) => a.user_id === me && a.status === 2)
})

/** 是否校管/院管（无部门限制） */
const isStaff = computed(() => userStore.hasRole(['admin', 'college_admin']))

/** 校验：当前用户是否有权对某资产发起归还（必须本人，校管/院管也不能代发起） */
function canReturnAsset(asset: any): boolean {
  if (!asset) return false
  if (asset.status !== 2) return false
  return asset.user_id === userStore.userInfo?.user_id
}

/** 校验：当前用户是否有权对某资产发起报修（仅 IDLE 闲置） */
function canRepairAsset(asset: any): boolean {
  if (!asset) return false
  if (asset.status !== 1) return false  // 仅 IDLE 闲置可报修
  if (isStaff.value) return true
  const myDept = userStore.userInfo?.dept_id
  return !myDept || !asset.dept_id || asset.dept_id === myDept
}

const kpi = computed(() => {
  const pendingApply = myApplies.value.filter((a) => ['PENDING_COLLEGE', 'PENDING_SCHOOL'].includes(a.status)).length
  const repairing = myOrders.value.filter((o) => ['PENDING_COLLEGE_APPROVE', 'PENDING_SCHOOL_APPROVE', 'PENDING_DISPATCH', 'PENDING_REPAIR', 'REPAIR_ACCEPTED'].includes(o.status)).length
  const acceptance = myOrders.value.filter((o) => o.status === 'PENDING_ACCEPTANCE').length
  return {
    using: borrowedAssets.value.length,
    pendingApply,
    repairing,
    acceptance,
  }
})

// 排序后展示列表
const displayBorrowed = computed(() => applySort(borrowedAssets.value))
const displayOrders = computed(() => applySort(myOrders.value))
const displayApplies = computed(() => applySort(myApplies.value))

async function fetchAll() {
  loading.value = true
  try {
    // 我作为普通用户，资产列表自动被后端按 dept_id 过滤，这里拉取较大分页即可
    const [a, ap, o] = await Promise.all([
      listAssetsApi({ page_num: 1, page_size: 200 }),
      listMyAppliesApi({ page_num: 1, page_size: 50 }),
      listRepairOrdersApi({ page_num: 1, page_size: 50 }),
    ])
    allAssets.value = a?.data?.list || []
    myApplies.value = ap?.data?.list || []
    // /repair/list 普通用户分支：自动按 reporter_id 过滤
    myOrders.value = o?.data?.list || []
  } finally {
    loading.value = false
  }
}

async function quickReturn(asset: any) {
  await ElMessageBox.confirm(
    `确定对「${asset.asset_name}」发起归还申请？`,
    '快捷归还',
    { type: 'info' }
  )
  try {
    await submitReturnApi({ asset_id: asset.asset_id, reason: '快捷归还' })
    ElMessage.success('归还申请已提交，等待审批')
    fetchAll()
  } catch {
    /* 拦截器已提示 */
  }
}

async function batchReturn() {
  await ElMessageBox.confirm(
    `对 ${selectedAssets.value.length} 个资产批量发起归还申请？`,
    '批量归还',
    { type: 'info' }
  )
  let success = 0
  for (const a of selectedAssets.value) {
    try {
      await submitReturnApi({ asset_id: a.asset_id, reason: '批量归还' })
      success++
    } catch { /* 单条失败跳过 */ }
  }
  ElMessage.success(`成功提交 ${success} 条归还申请`)
  selectedAssets.value = []
  fetchAll()
}

async function quickRepair(asset: any) {
  // 改用弹窗（与其他页面统一），预填资产编号
  openRepairDialog(asset.asset_code)
}

onMounted(fetchAll)
</script>

<style scoped>
.kpi-row { margin-top: 4px; }
.kpi-card { transition: transform 0.2s; }
.kpi-card:hover { transform: translateY(-2px); }
.kpi-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}
.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--c) 12%, white);
  color: var(--c);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}
.kpi-num { font-size: 24px; font-weight: 700; color: var(--c); }
.kpi-label { font-size: 12px; color: #909399; margin-top: 2px; }

.card-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
</style>
