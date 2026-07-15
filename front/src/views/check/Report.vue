<template>
  <div class="page-container">
    <el-page-header :icon="ArrowLeft" content="返回盘点列表" @back="$router.push('/checks')">
      <template #content>
        <span class="page-title-inline">
          <el-icon><Collection /></el-icon> 差异报告 · 任务 #{{ taskId }}
        </span>
      </template>
    </el-page-header>

    <el-skeleton v-if="loading" :rows="6" animated class="mt-16" />

    <template v-else-if="report">
      <el-row :gutter="12" class="mt-16">
        <el-col :span="6"><el-card class="kpi" shadow="hover"><div class="kpi-num">{{ total }}</div><div class="kpi-label">盘点总数</div></el-card></el-col>
        <el-col :span="6"><el-card class="kpi" shadow="hover"><div class="kpi-num text-success">{{ matchedCount }}</div><div class="kpi-label">相符</div></el-card></el-col>
        <el-col :span="6"><el-card class="kpi" shadow="hover"><div class="kpi-num text-warning">{{ mismatchCount }}</div><div class="kpi-label">不符</div></el-card></el-col>
        <el-col :span="6"><el-card class="kpi" shadow="hover"><div class="kpi-num text-danger">{{ surplusCount + shortageCount }}</div><div class="kpi-label">盘盈/亏</div></el-card></el-col>
      </el-row>

      <el-row :gutter="12" class="mt-12">
        <el-col :xs="24" :md="8">
          <el-card shadow="never">
            <template #header><span>差异分布</span></template>
            <div ref="pieRef" class="chart-box"></div>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="16">
          <el-card shadow="never">
            <template #header>
              <div class="card-hd">
                <span>差异明细</span>
                <el-button
                  v-if="userStore.hasRole(['admin', 'college_admin']) && report.total_items > 0 && !confirmed"
                  type="primary" :icon="Check" @click="onConfirm"
                >确认盘点结果</el-button>
                <el-tag v-else-if="confirmed" type="info" effect="plain">已确认</el-tag>
              </div>
            </template>
            <el-table :data="diffItems" stripe border>
              <el-table-column prop="asset_code" label="资产编号" width="130" />
              <el-table-column prop="asset_name" label="资产名称" min-width="160" show-overflow-tooltip />
              <el-table-column label="差异类型" width="100">
                <template #default="{ row }">
                  <el-tag :type="diffTagType(row.diff_type)" size="small">
                    {{ DIFF_NAME[row.diff_type] || row.diff_type }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="book_location" label="账面地点" min-width="120" show-overflow-tooltip />
              <el-table-column prop="actual_location" label="实际地点" min-width="120" show-overflow-tooltip />
              <el-table-column label="账面状态" width="100">
                <template #default="{ row }">{{ ASSET_STATUS_NAME[row.book_status] || row.book_status || '-' }}</template>
              </el-table-column>
              <el-table-column label="实际状态" width="100">
                <template #default="{ row }">{{ ASSET_STATUS_NAME[row.actual_status] || row.actual_status || '-' }}</template>
              </el-table-column>
              <el-table-column prop="remark" label="差异说明" min-width="160" show-overflow-tooltip />
            </el-table>
            <el-empty v-if="diffItems.length === 0" description="暂无明细" />
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-empty v-else description="暂无差异报告" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { Collection, ArrowLeft, Check } from '@element-plus/icons-vue'
import { getDiffReportApi, confirmCheckApi } from '@/api/check'
import { useUserStore } from '@/store/user'
import { ASSET_STATUS_NAME } from '@/types'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const taskId = Number(route.params.id)

const loading = ref(false)
const report = ref<any>(null)
const diffItems = ref<any[]>([])

const DIFF_NAME: Record<string, string> = {
  MATCHED: '相符', MISMATCH: '不符', MISSING: '盘亏', EXTRA: '盘盈',
}

function diffTagType(t: string) {
  if (t === 'MISSING') return 'danger'
  if (t === 'EXTRA') return 'success'
  if (t === 'MISMATCH') return 'warning'
  return 'info'
}

const total = computed(() => diffItems.value.length)
const matchedCount = computed(() => diffItems.value.filter((d) => d.diff_type === 'MATCHED').length)
const mismatchCount = computed(() => diffItems.value.filter((d) => d.diff_type === 'MISMATCH').length)
const surplusCount = computed(() => diffItems.value.filter((d) => d.diff_type === 'EXTRA').length)
const shortageCount = computed(() => diffItems.value.filter((d) => d.diff_type === 'MISSING').length)
const confirmed = computed(() => report.value.status === 'CONFIRMED')

const pieRef = ref<HTMLElement>()
let chart: any = null

function makePie() {
  if (!pieRef.value) return
  if (!chart) chart = echarts.init(pieRef.value)
  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    color: ['#67C23A', '#E6A23C', '#F56C6C', '#909399'],
    series: [{
      type: 'pie', radius: ['38%', '70%'],
      data: [
        { name: '相符', value: matchedCount.value },
        { name: '不符', value: mismatchCount.value },
        { name: '盘盈', value: surplusCount.value },
        { name: '盘亏', value: shortageCount.value },
      ].filter((x) => x.value > 0),
    }],
  })
}

async function fetchReport() {
  loading.value = true
  try {
    const res: any = await getDiffReportApi(taskId)
    if (!res?.data) { report.value = null; return }
    report.value = res.data
    diffItems.value = res.data.diff_items || []
    await nextTick(); makePie()
  } finally { loading.value = false }
}

async function onConfirm() {
  if (confirmed.value) {
    ElMessage.warning(`该任务已结束`)
    return
  }
  await ElMessageBox.confirm('确认本次盘点结果？确认后不可再修改。', '提示', { type: 'warning' })
  await confirmCheckApi(taskId)
  ElMessage.success('已确认')
  router.push('/checks')
}

onMounted(fetchReport)
</script>

<style scoped>
.page-title-inline { font-size: 18px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; }
.kpi { text-align: center; padding: 4px; }
.kpi-num { font-size: 24px; font-weight: 700; color: #303133; }
.kpi-label { font-size: 12px; color: #909399; }
.card-hd { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.chart-box { width: 100%; height: 280px; }
</style>
