<template>
  <div class="page-container">
    <el-skeleton v-if="loading" :rows="8" animated />
    <template v-else>
      <div class="page-title">
        <el-icon><Folder /></el-icon> 我的已处理
        <el-tag size="small" effect="plain" type="info" class="ml-8">
          共 {{ total }} 条
        </el-tag>
      </div>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="mb-12"
        title="本页面仅展示经过我处理（审批 / 驳回 / 派单 / 接单 / 验收）的流程记录"
        description="我发起的申请 / 报修请到【我的申请】页面查看"
      />

      <!-- 业务子 Tab：申请 / 报修 -->
      <el-tabs v-model="bizTab" class="biz-tabs">
        <el-tab-pane :label="`申请 (${approvedApplyList.length})`" name="APPLY">
          <el-card shadow="never">
            <el-table
              v-loading="loading"
              :data="displayApprovedApply"
              stripe
              border
              @sort-change="handleSortChange"
            >
              <el-table-column prop="apply_id" label="申请号" width="80" sortable="custom" />
              <el-table-column prop="apply_type" label="类型" width="80" sortable="custom">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ APPLY_TYPE_NAME[row.apply_type] || row.apply_type }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="asset_name" label="资产" min-width="160" show-overflow-tooltip sortable="custom" />
              <el-table-column prop="applicant_name" label="发起人" width="100" sortable="custom" />
              <el-table-column prop="dept_name" label="部门" width="140" show-overflow-tooltip sortable="custom" />
              <el-table-column prop="status" label="状态" width="100" sortable="custom">
                <template #default="{ row }">
                  <el-tag :type="APPLY_STATUS_TYPE[row.status] || 'info'" size="small">
                    {{ APPLY_STATUS_NAME[row.status] || row.status }}
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
              <template #empty>
                <el-empty description="暂无我部门已审批的申请（普通用户无此视图）" />
              </template>
            </el-table>
          </el-card>
        </el-tab-pane>

        <el-tab-pane :label="`报修 (${approvedRepairList.length})`" name="REPAIR">
          <el-card shadow="never">
            <el-table
              v-loading="loading"
              :data="displayApprovedRepair"
              stripe
              border
              @sort-change="handleSortChange"
            >
              <el-table-column prop="order_id" label="工单号" width="80" sortable="custom" />
              <el-table-column prop="asset_name" label="资产" min-width="160" show-overflow-tooltip sortable="custom" />
              <el-table-column prop="reporter_name" label="报修人" width="100" sortable="custom" />
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
              <template #empty>
                <el-empty description="暂无我部门已审批/已处理的报修" />
              </template>
            </el-table>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Folder } from '@element-plus/icons-vue'
import {
  listApprovedAppliesApi, listRepairOrdersApi,
} from '@/api/workflow'
import { useUserStore } from '@/store/user'
import { useTableSort } from '@/composables/useTableSort'
import { formatDate } from '@/utils/format'
import {
  APPLY_TYPE_NAME, APPLY_STATUS_NAME, APPLY_STATUS_TYPE,
  REPAIR_STATUS_NAME, REPAIR_STATUS_TYPE,
} from '@/types'

const userStore = useUserStore()
const { handleSortChange, applySort } = useTableSort()

const loading = ref(false)
const bizTab = ref<'APPLY' | 'REPAIR'>('APPLY')

const approvedApplyList = ref<any[]>([])
const approvedRepairList = ref<any[]>([])

const total = computed(() => approvedApplyList.value.length + approvedRepairList.value.length)

const displayApprovedApply = computed(() => applySort(approvedApplyList.value))
const displayApprovedRepair = computed(() => applySort(approvedRepairList.value))

async function fetchList() {
  loading.value = true
  try {
    // 仅校管/院管有"我处理过"的数据，普通用户保持空
    const isApprover = userStore.hasRole(['admin', 'college_admin'])
    if (isApprover) {
      const [a, rep]: any[] = await Promise.all([
        listApprovedAppliesApi({ page_num: 1, page_size: 50 }),
        listRepairOrdersApi({ status: 'ACCEPTANCE_PASSED,ACCEPTANCE_REJECTED', page_num: 1, page_size: 50 }),
      ])
      approvedApplyList.value = a?.data?.list || []
      approvedRepairList.value = rep?.data?.list || []
    } else {
      approvedApplyList.value = []
      approvedRepairList.value = []
    }
  } finally {
    loading.value = false
  }
}

onMounted(fetchList)
</script>

<style scoped>
.biz-tabs { margin-top: 8px; }
.ml-8 { margin-left: 8px; }
</style>
