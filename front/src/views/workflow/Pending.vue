<template>
  <div class="page-container">
    <el-skeleton v-if="loading" :rows="8" animated />
    <template v-else>
      <div class="page-title">
        <el-icon><Bell /></el-icon> 待办清单
        <el-tag size="small" effect="plain" type="info" class="ml-8">
          共 {{ total }} 条
        </el-tag>
      </div>

      <el-alert
        v-if="!hasAnyPending"
        type="success"
        :closable="false"
        show-icon
        class="mb-12"
        title="当前没有需要您处理的流程"
        description="如需发起新申请，请使用页面右上角【发起申请】下拉按钮，或到【资产管理】/【我的申请】页内点击资产的快捷按钮。"
      />

      <!-- 业务子 Tab：申请 / 报修（维修工只显示报修） -->
      <el-tabs v-model="bizTab" class="biz-tabs">
        <el-tab-pane
          v-if="!userStore.hasRole('repairer') || userStore.hasRole('admin')"
          :label="`申请 (${applyList.length})`" name="APPLY">
          <el-card shadow="never">
            <el-table
              v-loading="loading"
              :data="displayApplyList"
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
                <el-empty description="当前没有需要您审批的申请" />
              </template>
            </el-table>
          </el-card>
        </el-tab-pane>

        <el-tab-pane :label="`报修 (${repairList.length})`" name="REPAIR">
          <el-card shadow="never">
            <el-table
              v-loading="loading"
              :data="displayRepairList"
              stripe
              border
              @sort-change="handleSortChange"
            >
              <el-table-column prop="order_id" label="工单号" width="80" sortable="custom" />
              <el-table-column prop="asset_name" label="资产" min-width="160" show-overflow-tooltip sortable="custom" />
              <el-table-column prop="reporter_name" label="报修人" width="100" sortable="custom" />
              <el-table-column prop="dept_name" label="部门" width="140" show-overflow-tooltip sortable="custom" />
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
                <el-empty description="当前没有需要您处理的报修工单" />
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
import { useRoute } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import {
  listPendingAppliesApi, listRepairOrdersApi,
} from '@/api/workflow'
import { useUserStore } from '@/store/user'
import { useTableSort } from '@/composables/useTableSort'
import { formatDate } from '@/utils/format'
import {
  APPLY_TYPE_NAME, APPLY_STATUS_NAME, APPLY_STATUS_TYPE,
  REPAIR_STATUS_NAME, REPAIR_STATUS_TYPE,
} from '@/types'

const route = useRoute()
const userStore = useUserStore()
const { handleSortChange, applySort } = useTableSort()

const loading = ref(false)
// 默认 Tab：维修工进报修；其他进申请。query.tab 可覆盖（如从大屏 KPI 跳转过来）
const initialTab: 'APPLY' | 'REPAIR' = (() => {
  const q = (route.query.tab as string) || ''
  if (q === 'REPAIR' || q === 'APPLY') return q
  return userStore.hasRole('repairer') && !userStore.hasRole('admin') ? 'REPAIR' : 'APPLY'
})()
const bizTab = ref<'APPLY' | 'REPAIR'>(initialTab)

const applyList = ref<any[]>([])
const repairList = ref<any[]>([])
const total = ref(0)

const displayApplyList = computed(() => applySort(applyList.value))
const displayRepairList = computed(() => applySort(repairList.value))
const hasAnyPending = computed(() => total.value > 0)

async function fetchList() {
  loading.value = true
  try {
    // 申请：/apply/pending 由后端按 role + dept 自动过滤
    // 校管/院管可看到 PENDING_COLLEGE / PENDING_SCHOOL
    const apRes: any = await listPendingAppliesApi({ page_num: 1, page_size: 50 })
    applyList.value = apRes?.data?.list || []

    // 报修：/repair/list 按 role 分流
    //   - 校管 (admin): 待校审 (PENDING_SCHOOL_APPROVE)
    //   - 院管 (college_admin): 待院审 (PENDING_COLLEGE_APPROVE) + 待派单 (PENDING_DISPATCH)
    //   - 维修工 (repairer): 待接单 (PENDING_REPAIR) + 维修中
    //   - 普通用户: 看不到任何（前端自动不调）
    const isAdmin = userStore.hasRole('admin')
    const isCollege = userStore.hasRole('college_admin') && !isAdmin
    const isRepairer = userStore.hasRole('repairer') && !isAdmin

    if (isAdmin) {
      const r1: any = await listRepairOrdersApi({ status: 'PENDING_SCHOOL_APPROVE,PENDING_DISPATCH,PENDING_ACCEPTANCE', page_num: 1, page_size: 50 })
      repairList.value = r1?.data?.list || []
    } else if (isCollege) {
      // 院管：待院审 (PENDING_COLLEGE_APPROVE)
      const r1: any = await listRepairOrdersApi({ status: 'PENDING_COLLEGE_APPROVE', page_num: 1, page_size: 50 })
      repairList.value = r1?.data?.list || []
    } else if (isRepairer) {
      // 维修工：派给自己的待接单 + 返工待重提
      const r1: any = await listRepairOrdersApi({
        status: 'PENDING_REPAIR,ACCEPTANCE_REJECTED',
        repairer_id: userStore.userInfo?.user_id || 0,
        page_num: 1, page_size: 50,
      })
      repairList.value = r1?.data?.list || []
    } else {
      repairList.value = []
    }
    total.value = applyList.value.length + repairList.value.length
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
