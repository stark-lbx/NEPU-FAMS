<template>
  <div class="dash-root">
    <!-- 全屏跳转按钮（绝对定位右上角） -->
    <el-button
      class="fullscreen-btn"
      :icon="FullScreen"
      size="small"
      @click="openFullscreen"
    >
      全屏大屏
    </el-button>

    <!-- 顶部欢迎栏（所有角色通用） -->
    <el-card class="welcome-card" shadow="never">
      <div class="welcome-row">
        <div class="welcome-left">
          <h2 class="welcome-title">
            <el-icon><Sunny /></el-icon>
            {{ greet }}，{{ userStore.userInfo?.nickname || '用户' }}
          </h2>
          <p class="welcome-sub">
            今天是 {{ today }} · 当前角色：
            <el-tag :type="roleTagType" size="small" effect="dark">{{ roleLabel }}</el-tag>
            <span v-if="deptName" class="dept-tag">· {{ deptName }}</span>
          </p>
        </div>
        <div class="welcome-right">
          <!-- 校管/院管：本月新增资产 -->
          <el-statistic v-if="isStaff" title="本月新增资产" :value="overview.asset_new_this_month || 0">
            <template #suffix>件</template>
          </el-statistic>
          <!-- 维修工：待我处理工单 -->
          <el-statistic v-else-if="isRepairer" title="待我处理工单" :value="myPendingOrders.length">
            <template #suffix>单</template>
          </el-statistic>
          <!-- 普通师生：我领用中的资产 -->
          <el-statistic v-else title="我领用中的资产" :value="myBorrowedCount">
            <template #suffix>件</template>
          </el-statistic>
        </div>
      </div>
    </el-card>

    <!-- ========== 校管/院管 工作台 ========== -->
    <template v-if="isStaff">
      <el-row :gutter="12" class="kpi-row">
        <el-col v-for="k in kpis" :key="k.key" :xs="12" :sm="12" :md="6">
          <el-card class="kpi-card" shadow="hover" @click="k.onClick">
            <div class="kpi-inner" :style="{ '--c': k.color }">
              <el-icon class="kpi-icon"><component :is="k.icon" /></el-icon>
              <div class="kpi-body">
                <div class="kpi-num">{{ k.value }}</div>
                <div class="kpi-label">{{ k.label }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="12" class="chart-row">
        <el-col :xs="24" :md="12">
          <el-card shadow="never">
            <template #header>
              <div class="card-hd">
                <span><el-icon><TrendCharts /></el-icon> 近 6 月资产新增趋势</span>
              </div>
            </template>
            <div ref="lineRef" class="chart-box"></div>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="6">
          <el-card shadow="never">
            <template #header><div class="card-hd"><span><el-icon><PieChart /></el-icon> 资产状态分布</span></div></template>
            <div ref="pieRef" class="chart-box"></div>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="6">
          <el-card shadow="never">
            <template #header><div class="card-hd"><span><el-icon><Histogram /></el-icon> 资产分类分布</span></div></template>
            <div ref="catRef" class="chart-box"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="12" class="bottom-row">
        <el-col :xs="24" :md="8">
          <el-card shadow="never">
            <template #header>
              <div class="card-hd">
                <span><el-icon><Bell /></el-icon> 待我处理 ({{ allPendingItems.length }})</span>
                <el-link type="primary" :underline="false" @click="$router.push('/workflows/pending')">查看全部</el-link>
              </div>
            </template>
            <el-table :data="allPendingItems" size="small" max-height="280" empty-text="暂无待办">
              <el-table-column label="#" width="60">
                <template #default="{ row }">
                  <el-tag v-if="row._kind === 'repair'" size="small" type="warning">工单</el-tag>
                  <el-tag v-else size="small" type="info">申请</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="asset_name" label="资产" show-overflow-tooltip />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag v-if="row._kind === 'repair'"
                    :type="REPAIR_STATUS_TYPE[row.status] || 'warning'" size="small">
                    {{ REPAIR_STATUS_NAME[row.status] || row.status }}
                  </el-tag>
                  <el-tag v-else
                    :type="APPLY_STATUS_TYPE[row.status] || 'info'" size="small">
                    {{ APPLY_STATUS_NAME[row.status] || row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" align="center">
                <template #default="{ row }">
                  <el-button v-if="row._kind === 'repair'" type="primary" link size="small"
                    @click="$router.push(`/workflows/repair/${row.order_id}`)">处理</el-button>
                  <el-button v-else type="primary" link size="small"
                    @click="$router.push(`/workflows/apply/${row.apply_id}`)">审</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>

        <el-col :xs="24" :md="10">
          <el-card shadow="never">
            <template #header><div class="card-hd"><span><el-icon><OfficeBuilding /></el-icon> 各学院资产数量</span></div></template>
            <div ref="deptRef" class="chart-box chart-dept"></div>
          </el-card>
        </el-col>

        <el-col :xs="24" :md="6">
          <el-card shadow="never">
            <template #header><div class="card-hd"><span><el-icon><Aim /></el-icon> 快捷操作</span></div></template>
            <div class="shortcut-grid">
              <div v-for="s in shortcuts" :key="s.label" class="shortcut-item" @click="$router.push(s.path)">
                <el-icon :size="22" :color="s.color"><component :is="s.icon" /></el-icon>
                <span>{{ s.label }}</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <!-- ========== 普通师生 工作台 ========== -->
    <template v-else-if="isStudent">
      <el-row :gutter="12" class="kpi-row">
        <el-col :xs="12" :sm="6">
          <el-card class="kpi-card" shadow="hover" @click="$router.push('/my-borrows')">
            <div class="kpi-inner" style="--c:#409EFF">
              <el-icon class="kpi-icon"><Box /></el-icon>
              <div class="kpi-body">
                <div class="kpi-num">{{ myBorrowedCount }}</div>
                <div class="kpi-label">我领用中</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="6">
          <el-card class="kpi-card" shadow="hover" @click="$router.push('/workflows/done')">
            <div class="kpi-inner" style="--c:#67C23A">
              <el-icon class="kpi-icon"><Document /></el-icon>
              <div class="kpi-body">
                <div class="kpi-num">{{ myApplies.length }}</div>
                <div class="kpi-label">我的申请</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="6">
          <el-card class="kpi-card" shadow="hover" @click="$router.push('/my-borrows')">
            <div class="kpi-inner" style="--c:#E6A23C">
              <el-icon class="kpi-icon"><Tools /></el-icon>
              <div class="kpi-body">
                <div class="kpi-num">{{ myRepairCount }}</div>
                <div class="kpi-label">我报修中</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="6">
          <el-card class="kpi-card" shadow="hover" @click="$router.push('/assets')">
            <div class="kpi-inner" style="--c:#909399">
              <el-icon class="kpi-icon"><Box /></el-icon>
              <div class="kpi-body">
                <div class="kpi-num">{{ deptAssetCount }}</div>
                <div class="kpi-label">本部门资产</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="12" class="chart-row">
        <el-col :xs="24" :md="14">
          <el-card shadow="never">
            <template #header>
              <div class="card-hd">
                <span><el-icon><Document /></el-icon> 我最近发起的流程</span>
                <el-link type="primary" :underline="false" @click="$router.push('/workflows/done')">查看全部</el-link>
              </div>
            </template>
            <el-table :data="myApplies.slice(0, 5)" size="small" stripe>
              <el-table-column prop="apply_id" label="#" width="60" />
              <el-table-column prop="asset_name" label="资产" show-overflow-tooltip />
              <el-table-column prop="apply_type" label="类型" width="80">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ APPLY_TYPE_NAME[row.apply_type] }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="APPLY_STATUS_TYPE[row.status] || 'info'" size="small">
                    {{ APPLY_STATUS_NAME[row.status] }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="create_time" label="时间" width="140">
                <template #default="{ row }">{{ formatDate(row.create_time) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="60" align="center">
                <template #default="{ row }">
                  <el-button type="primary" link size="small" @click="$router.push(`/workflows/apply/${row.apply_id}`)">详情</el-button>
                </template>
              </el-table-column>
              <template #empty><el-empty description="暂无申请" /></template>
            </el-table>
          </el-card>
        </el-col>

        <el-col :xs="24" :md="10">
          <el-card shadow="never">
            <template #header><div class="card-hd"><span><el-icon><Aim /></el-icon> 快捷操作</span></div></template>
            <div class="shortcut-grid">
              <div class="shortcut-item" @click="$router.push('/workflows')">
                <el-icon :size="22" color="#409eff"><Document /></el-icon>
                <span>发起申请</span>
              </div>
              <div class="shortcut-item" @click="$router.push('/my-borrows')">
                <el-icon :size="22" color="#67c23a"><Goods /></el-icon>
                <span>我的申请</span>
              </div>
              <div class="shortcut-item" @click="$router.push('/assets')">
                <el-icon :size="22" color="#e6a23c"><Box /></el-icon>
                <span>查看资产</span>
              </div>
              <div class="shortcut-item" @click="$router.push('/profile')">
                <el-icon :size="22" color="#909399"><UserFilled /></el-icon>
                <span>个人信息</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <!-- ========== 维修工 工作台 ========== -->
    <template v-else>
      <el-row :gutter="12" class="kpi-row">
        <el-col :xs="12" :sm="6">
          <el-card class="kpi-card" shadow="hover" @click="goPendingTab('REPAIR', 'PENDING_REPAIR')">
            <div class="kpi-inner" style="--c:#E6A23C">
              <el-icon class="kpi-icon"><Tools /></el-icon>
              <div class="kpi-body">
                <div class="kpi-num">{{ pendingRepairCount }}</div>
                <div class="kpi-label">待我接单</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="6">
          <el-card class="kpi-card" shadow="hover" @click="goPendingTab('REPAIR', 'REPAIR_ACCEPTED')">
            <div class="kpi-inner" style="--c:#F56C6C">
              <el-icon class="kpi-icon"><Tools /></el-icon>
              <div class="kpi-body">
                <div class="kpi-num">{{ inProgressRepairCount }}</div>
                <div class="kpi-label">维修中</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="6">
          <el-card class="kpi-card" shadow="hover" @click="goPendingTab('REPAIR', 'ACCEPTANCE_REJECTED')">
            <div class="kpi-inner" style="--c:#E040FB">
              <el-icon class="kpi-icon"><Refresh /></el-icon>
              <div class="kpi-body">
                <div class="kpi-num">{{ reworkCount }}</div>
                <div class="kpi-label">待返工</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="6">
          <el-card class="kpi-card" shadow="hover" @click="$router.push('/workflows/done')">
            <div class="kpi-inner" style="--c:#67C23A">
              <el-icon class="kpi-icon"><Folder /></el-icon>
              <div class="kpi-body">
                <div class="kpi-num">{{ doneRepairCount }}</div>
                <div class="kpi-label">本月完成</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="12" class="chart-row">
        <el-col :xs="24" :md="16">
          <el-card shadow="never">
            <template #header>
              <div class="card-hd">
                <span><el-icon><Tools /></el-icon> 当前在修工单</span>
                <el-link type="primary" :underline="false" @click="$router.push('/workflows/pending')">查看全部</el-link>
              </div>
            </template>
            <el-table :data="myPendingOrders" size="small" stripe>
              <el-table-column prop="order_id" label="工单号" width="80" />
              <el-table-column prop="asset_name" label="资产" show-overflow-tooltip />
              <el-table-column prop="fault_desc" label="故障" show-overflow-tooltip />
              <el-table-column prop="status" label="状态" width="110">
                <template #default="{ row }">
                  <el-tag :type="REPAIR_STATUS_TYPE[row.status] || 'info'" size="small">
                    {{ REPAIR_STATUS_NAME[row.status] || row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="create_time" label="提交时间" width="160">
                <template #default="{ row }">{{ formatDate(row.create_time) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="80" align="center">
                <template #default="{ row }">
                  <el-button type="primary" link size="small" @click="$router.push(`/workflows/repair/${row.order_id}`)">处理</el-button>
                </template>
              </el-table-column>
              <template #empty><el-empty description="暂无在修工单" /></template>
            </el-table>
          </el-card>
        </el-col>

        <el-col :xs="24" :md="8">
          <el-card shadow="never">
            <template #header><div class="card-hd"><span><el-icon><Aim /></el-icon> 快捷操作</span></div></template>
            <div class="shortcut-grid">
              <div class="shortcut-item" @click="$router.push('/workflows/pending')">
                <el-icon :size="22" color="#e6a23c"><Bell /></el-icon>
                <span>待处理</span>
              </div>
              <div class="shortcut-item" @click="$router.push('/workflows/done')">
                <el-icon :size="22" color="#67c23a"><Folder /></el-icon>
                <span>已处理</span>
              </div>
              <div class="shortcut-item" @click="$router.push('/my-borrows')">
                <el-icon :size="22" color="#409eff"><Goods /></el-icon>
                <span>我的申请</span>
              </div>
              <div class="shortcut-item" @click="$router.push('/profile')">
                <el-icon :size="22" color="#909399"><UserFilled /></el-icon>
                <span>个人信息</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  Sunny, TrendCharts, PieChart, Histogram, Bell, OfficeBuilding, Aim,
  Box, Document, Tools, CircleCheck, Folder, Goods, UserFilled, Checked,
  FullScreen, Refresh,
} from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { getDashboardApi, getAssetReportApi } from '@/api/report'
import { listPendingAppliesApi, listMyAppliesApi, listRepairOrdersApi } from '@/api/workflow'
import { listAssetsApi, listAssetStatusApi } from '@/api/asset'
import { getDeptTreeApi } from '@/api/user'
import { useUserStore } from '@/store/user'
import { formatDate } from '@/utils/format'
import {
  APPLY_TYPE_NAME, APPLY_STATUS_NAME, APPLY_STATUS_TYPE,
  REPAIR_STATUS_NAME, REPAIR_STATUS_TYPE,
} from '@/types'

const router = useRouter()
const userStore = useUserStore()

// === 角色 ===
const isStaff = computed(() => userStore.isStaff())
const isRepairer = computed(() => userStore.isRepairer())
const isStudent = computed(() => userStore.isStudent())

// === 通用数据 ===
const overview = ref<any>({})
const pendingApplies = ref<any[]>([])
const pendingRepairs = ref<any[]>([])
const statusNameMap = ref<Record<number, string>>({})
const deptName = ref('')
const myApplies = ref<any[]>([])
const myPendingOrders = ref<any[]>([])
const deptAssetCount = ref(0)
const allAssets = ref<any[]>([])

/** 校管/院管「待我处理」汇总：申请 + 报修工单 */
const allPendingItems = computed(() => {
  const items: any[] = []
  pendingApplies.value.forEach((it) => items.push({ ...it, _kind: 'apply' }))
  pendingRepairs.value.forEach((it) => items.push({ ...it, _kind: 'repair' }))
  return items.slice(0, 8)
})

const myBorrowedCount = computed(() => {
  const me = userStore.userInfo?.user_id
  return allAssets.value.filter((a) => a.user_id === me && a.status === 2).length
})
const myRepairCount = computed(() => {
  return myPendingOrders.value.filter((o) =>
    ['PENDING_COLLEGE_APPROVE', 'PENDING_SCHOOL_APPROVE', 'PENDING_DISPATCH', 'PENDING_REPAIR', 'REPAIR_ACCEPTED']
      .includes(o.status)).length
})
/** 维修工 KPI：仅统计派给我的工单 */
const myOrders = computed(() => {
  const me = userStore.userInfo?.user_id
  return myPendingOrders.value.filter((o) => o.repairer_id === me)
})
const pendingRepairCount = computed(() =>
  myOrders.value.filter((o) => o.status === 'PENDING_REPAIR').length
)
const inProgressRepairCount = computed(() =>
  myOrders.value.filter((o) => o.status === 'REPAIR_ACCEPTED').length
)
const reworkCount = computed(() =>
  myOrders.value.filter((o) => o.status === 'ACCEPTANCE_REJECTED').length
)
const acceptanceCount = computed(() =>
  myOrders.value.filter((o) => o.status === 'PENDING_ACCEPTANCE').length
)
const doneRepairCount = computed(() => {
  // 本月已通过验收 + 派给我
  const now = new Date()
  const ym = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  return myOrders.value.filter((o) => o.status === 'ACCEPTANCE_PASSED'
    && (o.update_time || '').startsWith(ym)).length
})

// === 图表 ref ===
const lineRef = ref<HTMLElement>()
const pieRef = ref<HTMLElement>()
const catRef = ref<HTMLElement>()
const deptRef = ref<HTMLElement>()
const charts: echarts.ECharts[] = []

// === 角色显示 ===
const roleLabel = computed(() => {
  const r = userStore.roles
  if (r.includes('admin')) return '校级管理员'
  if (r.includes('college_admin')) return '院级管理员'
  if (r.includes('repairer')) return '维修工程师'
  return '普通师生'
})
const roleTagType = computed<'danger' | 'warning' | 'success' | 'info'>(() => {
  if (userStore.roles.includes('admin')) return 'danger'
  if (userStore.roles.includes('college_admin')) return 'warning'
  if (userStore.roles.includes('repairer')) return 'success'
  return 'info'
})

const hour = new Date().getHours()
const greet = hour < 6 ? '凌晨好' : hour < 11 ? '早上好' : hour < 14 ? '中午好' : hour < 18 ? '下午好' : '晚上好'
const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

// === 校管/院管 KPI ===
const kpis = computed(() => [
  { key: 'asset_total', label: '资产总数', value: overview.value.asset_total ?? 0, color: '#409EFF', icon: Box, onClick: () => router.push('/assets') },
  { key: 'pending_repairs', label: '待处理工单', value: overview.value.pending_repairs ?? 0, color: '#E6A23C', icon: Tools, onClick: () => router.push('/workflows/pending') },
  { key: 'in_progress', label: '维修中', value: overview.value.in_progress_repairs ?? 0, color: '#F56C6C', icon: Tools, onClick: () => router.push('/workflows/pending') },
  { key: 'pending_acceptance', label: '待验收', value: overview.value.pending_acceptance ?? 0, color: '#67C23A', icon: Checked, onClick: () => router.push('/workflows/pending') },
])

const shortcuts = computed(() => [
  { label: '我的申请', icon: Goods, color: '#409eff', path: '/my-borrows' },
  { label: '资产台账', icon: Box, color: '#67c23a', path: '/assets' },
  { label: '用户管理', icon: UserFilled, color: '#e6a23c', path: '/users' },
  { label: '流程管理', icon: Document, color: '#f56c6c', path: '/workflows' },
  { label: '资产盘点', icon: Folder, color: '#909399', path: '/checks' },
  { label: '个人信息', icon: UserFilled, color: '#909399', path: '/profile' },
])

// === 图表 ===
function makeLineChart(monthlyData: { month: string; count: number }[]) {
  if (!lineRef.value) return
  const chart = echarts.init(lineRef.value)
  const months = monthlyData.length ? monthlyData.map((d) => d.month) : genLast6Months()
  const values = monthlyData.length ? monthlyData.map((d) => d.count) : months.map(() => 0)
  // 蓝紫渐变 — 保留主基调
  chart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(20, 24, 60, 0.92)', borderColor: '#3b82f6', textStyle: { color: '#e0e7ff' } },
    grid: { left: 30, right: 16, top: 16, bottom: 28 },
    xAxis: { type: 'category', data: months, axisLine: { lineStyle: { color: 'rgba(99,102,241,0.4)' } }, axisLabel: { color: '#a5b4fc', fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { color: '#93c5fd' }, splitLine: { lineStyle: { color: 'rgba(99,102,241,0.12)' } } },
    series: [{
      name: '新增', type: 'line', smooth: true, data: values,
      lineStyle: { color: '#06b6d4', width: 3 },
      itemStyle: { color: '#22d3ee', borderColor: '#fff', borderWidth: 2 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(34, 211, 238, 0.45)' },
        { offset: 0.5, color: 'rgba(99, 102, 241, 0.25)' },
        { offset: 1, color: 'rgba(168, 85, 247, 0.05)' },
      ]) },
      symbol: 'circle', symbolSize: 8,
    }],
  })
  charts.push(chart)
}
function genLast6Months() {
  const arr: string[] = []
  const d = new Date()
  for (let i = 5; i >= 0; i--) {
    const dt = new Date(d.getFullYear(), d.getMonth() - i, 1)
    arr.push(`${dt.getMonth() + 1}月`)
  }
  return arr
}
function makePieChart(el: HTMLElement | undefined, data: { name: string; value: number }[]) {
  if (!el) return
  const chart = echarts.init(el)
  // 多彩配色：青蓝/紫/粉/橙/绿/黄
  const vibrantPalette = [
    '#22d3ee', '#3b82f6', '#a855f7', '#ec4899',
    '#f59e0b', '#10b981', '#8b5cf6', '#06b6d4',
  ]
  const themedData = data.length
    ? data.map((d, i) => ({ ...d, itemStyle: { color: vibrantPalette[i % vibrantPalette.length] } }))
    : [{ name: '暂无', value: 1, itemStyle: { color: 'rgba(99,102,241,0.20)' } }]
  chart.setOption({
    tooltip: { trigger: 'item', backgroundColor: 'rgba(20, 24, 60, 0.92)', borderColor: '#3b82f6', textStyle: { color: '#e0e7ff' } },
    legend: { bottom: 0, textStyle: { fontSize: 11, color: '#a5b4fc' } },
    series: [{
      type: 'pie',
      radius: ['38%', '70%'],
      center: ['50%', '45%'],
      data: themedData,
      label: { fontSize: 11, color: '#e0e7ff' },
      itemStyle: { borderColor: 'rgba(10, 14, 42, 0.6)', borderWidth: 2 },
    }],
  })
  charts.push(chart)
}
function makeDeptChart(el: HTMLElement | undefined, data: { name: string; value: number }[]) {
  if (!el) return
  const chart = echarts.init(el)
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(34,211,238,0.12)' } }, backgroundColor: 'rgba(20, 24, 60, 0.92)', borderColor: '#22d3ee', textStyle: { color: '#e0e7ff' } },
    grid: { left: 80, right: 20, top: 10, bottom: 20 },
    xAxis: { type: 'value', axisLabel: { color: '#93c5fd' }, splitLine: { lineStyle: { color: 'rgba(99,102,241,0.15)' } } },
    yAxis: { type: 'category', data: data.length ? data.map((d) => d.name) : ['暂无'], axisLabel: { color: '#a5b4fc', fontSize: 11 } },
    series: [{
      type: 'bar', data: data.length ? data.map((d) => d.value) : [0], barWidth: '55%',
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#06b6d4' },
          { offset: 0.6, color: '#3b82f6' },
          { offset: 1, color: '#a855f7' },
        ]),
        borderRadius: [0, 4, 4, 0],
        shadowBlur: 12,
        shadowColor: 'rgba(99, 102, 241, 0.5)',
      },
      label: { show: true, position: 'right', color: '#e0e7ff' },
    }],
  })
  charts.push(chart)
}

// === 加载数据 ===
async function loadStatusMap() {
  try {
    const res: any = await listAssetStatusApi()
    const list = res?.data || []
    const map: Record<number, string> = {}
    list.forEach((s: any) => (map[s.status_id] = s.status_name))
    statusNameMap.value = map
  } catch { /* ignore */ }
}

async function loadStudentData() {
  const [a, ap] = await Promise.all([
    listAssetsApi({ page_num: 1, page_size: 200 }),
    listMyAppliesApi({ page_num: 1, page_size: 50 }),
  ])
  allAssets.value = a?.data?.list || []
  deptAssetCount.value = a?.data?.total || 0
  myApplies.value = ap?.data?.list || []
}

async function loadRepairerData() {
  // 维修工：拉取派给自己的工单
  // 状态范围：PENDING_REPAIR(待接) / REPAIR_ACCEPTED(维修中) / ACCEPTANCE_REJECTED(待返工) / PENDING_ACCEPTANCE(待验收) / ACCEPTANCE_PASSED(已通过)
  const res: any = await listRepairOrdersApi({
    repairer_id: userStore.userInfo?.user_id || 0,
    page_num: 1, page_size: 50,
  })
  myPendingOrders.value = res?.data?.list || []
}

async function loadStaffData() {
  await Promise.all([
    getDashboardApi().then((r: any) => { overview.value = r?.data || {} }),
    getAssetReportApi().then((r: any) => {
      const ad = r?.data || {}
      const statusPie = (ad.status_pie || []).map((it: any) => ({
        name: it.status_name ?? statusNameMap.value[it.status_id] ?? `状态${it.status_id ?? ''}`,
        value: it.value ?? it.count ?? 0,
      }))
      const catPie = (ad.category_pie || []).map((it: any) => ({
        name: it.name ?? it.category_name ?? '未知',
        value: it.value ?? it.count ?? 0,
      }))
      const deptBar = (ad.dept_chart || []).map((it: any) => ({
        name: it.label || it.dept_name || '未知',
        value: it.value || it.count || 0,
      }))
      nextTick(() => {
        makeLineChart(ad.monthly_new || [])
        makePieChart(pieRef.value, statusPie)
        makePieChart(catRef.value, catPie)
        makeDeptChart(deptRef.value, deptBar)
      })
    }),
    listPendingAppliesApi({ page_num: 1, page_size: 5 }).then((r: any) => {
      pendingApplies.value = r?.data?.list || []
    }),
    // 维修工单：校管/院管各自的待办状态
    (async () => {
      const isAdmin = userStore.hasRole('admin')
      const isCollege = userStore.hasRole('college_admin') && !isAdmin
      const status = isAdmin
        ? 'PENDING_SCHOOL_APPROVE,PENDING_DISPATCH,PENDING_ACCEPTANCE'
        : isCollege
          ? 'PENDING_COLLEGE_APPROVE'
          : ''
      if (!status) { pendingRepairs.value = []; return }
      const r: any = await listRepairOrdersApi({ status, page_num: 1, page_size: 5 })
      pendingRepairs.value = r?.data?.list || []
    })(),
  ])
}

async function fetchDeptName() {
  try {
    const res: any = await getDeptTreeApi()
    const tree = res?.data || []
    const flat: any[] = []
    const walk = (arr: any[]) => arr.forEach((n) => { flat.push(n); if (n.children?.length) walk(n.children) })
    walk(tree)
    const me = userStore.userInfo?.dept_id
    const d = flat.find((x) => x.dept_id === me)
    if (d) deptName.value = d.dept_name
  } catch { /* ignore */ }
}

function handleResize() {
  charts.forEach((c) => c.resize())
}

/** 维修工 KPI 卡片跳转待办列表对应 Tab */
function goPendingTab(tab: 'REPAIR', statusFilter?: string) {
  router.push({
    path: '/workflows/pending',
    query: { tab, status: statusFilter || '' },
  })
}

/** 打开全屏大屏（新浏览器 tab，自动请求浏览器全屏） */
function openFullscreen() {
  // 1. 打开新 tab（router 用 history 模式，所以直接是路径）
  const win = window.open(
    window.location.origin + '/dashboard/fullscreen',
    '_blank',
    'noopener=yes'
  )
  if (!win) {
    ElMessage.warning('浏览器拦截了新窗口，请允许弹窗后重试')
    return
  }
  // 2. 等页面加载完再调用浏览器全屏 API
  const tryFullscreen = () => {
    try {
      const el = win.document.documentElement
      const req = el.requestFullscreen || (el as any).webkitRequestFullscreen
        || (el as any).mozRequestFullScreen || (el as any).msRequestFullscreen
      if (req) req.call(el)
    } catch { /* 用户可能取消或浏览器拒绝 */ }
  }
  // 新 tab load 后延迟一点执行
  const tick = () => {
    if (win.closed) return
    try { if (win.document.readyState === 'complete') tryFullscreen(); else setTimeout(tick, 200) }
    catch { setTimeout(tick, 200) }
  }
  setTimeout(tick, 400)
}

onMounted(async () => {
  await loadStatusMap()
  await fetchDeptName()
  if (isStaff.value) {
    await loadStaffData()
  } else if (isRepairer.value) {
    await loadRepairerData()
  } else {
    await loadStudentData()
  }
  window.addEventListener('resize', handleResize)
})
onBeforeUnmount(() => {
  charts.forEach((c) => c.dispose())
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
/* ========== 全屏按钮 ========== */
.fullscreen-btn {
  position: absolute;
  top: 22px;
  right: 22px;
  z-index: 5;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.30) 0%, rgba(168, 85, 247, 0.30) 100%) !important;
  border: 1px solid rgba(192, 132, 252, 0.50) !important;
  color: #e0e7ff !important;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 2px 12px rgba(99, 102, 241, 0.30);
  transition: all 0.25s;
}
.fullscreen-btn:hover {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.55) 0%, rgba(168, 85, 247, 0.55) 100%) !important;
  box-shadow: 0 4px 20px rgba(168, 85, 247, 0.50);
  transform: translateY(-1px);
}

/* ========== 资产台 蓝紫炫酷主题 ========== */
.dash-root {
  padding: 0;
  position: relative;
  min-height: calc(100vh - 88px);
  /* 蓝紫混合：左侧紫罗兰 + 右侧深空蓝 + 底部靛蓝 */
  background:
    radial-gradient(ellipse 800px 400px at 10% 5%, rgba(139, 92, 246, 0.32) 0%, transparent 60%),
    radial-gradient(ellipse 700px 500px at 90% 30%, rgba(59, 130, 246, 0.28) 0%, transparent 60%),
    radial-gradient(ellipse 900px 500px at 50% 95%, rgba(99, 102, 241, 0.22) 0%, transparent 60%),
    linear-gradient(135deg, #0a0e2a 0%, #1a1138 30%, #1e1b5e 55%, #1a2552 80%, #0f1a3a 100%);
  border-radius: 12px;
  padding: 16px;
  overflow: hidden;
}
/* 装饰光晕球 */
.dash-root::before {
  content: '';
  position: absolute;
  top: -120px;
  right: -120px;
  width: 360px;
  height: 360px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.50) 0%, transparent 70%);
  filter: blur(40px);
  pointer-events: none;
  animation: floatBlob 18s ease-in-out infinite;
}
.dash-root::after {
  content: '';
  position: absolute;
  bottom: -150px;
  left: -100px;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(168, 85, 247, 0.45) 0%, transparent 70%);
  filter: blur(50px);
  pointer-events: none;
  animation: floatBlob 22s ease-in-out infinite reverse;
}
@keyframes floatBlob {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(40px, -30px) scale(1.1); }
}

/* ========== 欢迎卡片：蓝紫玻璃拟态 ========== */
.welcome-card {
  margin-bottom: 12px;
  background: linear-gradient(135deg,
    rgba(99, 102, 241, 0.22) 0%,
    rgba(139, 92, 246, 0.16) 50%,
    rgba(34, 211, 238, 0.20) 100%) !important;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(99, 102, 241, 0.40) !important;
  box-shadow:
    0 8px 32px rgba(59, 130, 246, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.10) !important;
  position: relative;
  z-index: 1;
}
.welcome-card :deep(.el-card__body) { color: #e0e7ff; }
.welcome-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.welcome-left { flex: 1; min-width: 0; }
.welcome-title {
  font-size: 20px;
  margin: 0;
  color: #f0f4ff;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  text-shadow: 0 0 20px rgba(99, 102, 241, 0.5);
}
.welcome-title .el-icon { color: #60a5fa; filter: drop-shadow(0 0 8px rgba(96, 165, 250, 0.7)); }
.welcome-sub {
  font-size: 12px;
  color: #a5b4fc;
  margin: 8px 0 0;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.welcome-sub :deep(.el-tag) {
  background: linear-gradient(135deg, #3b82f6 0%, #a855f7 100%) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 500;
}
.dept-tag { color: #93c5fd; }
.welcome-right :deep(.el-statistic__head) { color: #a5b4fc !important; }
.welcome-right :deep(.el-statistic__content) { color: #f0f4ff !important; font-weight: 700; }
.welcome-right :deep(.el-statistic__suffix) { color: #93c5fd; font-size: 12px; }

/* ========== KPI 卡片：蓝紫霓虹 ========== */
.kpi-row { margin-bottom: 12px; }
.kpi-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.3s;
  background: linear-gradient(135deg,
    rgba(59, 130, 246, 0.18) 0%,
    rgba(168, 85, 247, 0.12) 100%) !important;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(99, 102, 241, 0.35) !important;
  box-shadow:
    0 4px 20px rgba(59, 130, 246, 0.22),
    inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
  position: relative;
  z-index: 1;
  overflow: hidden;
}
.kpi-card::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg,
    transparent 0%, var(--c) 50%, transparent 100%);
  opacity: 0.7;
}
.kpi-card:hover {
  transform: translateY(-3px);
  box-shadow:
    0 8px 32px rgba(99, 102, 241, 0.40),
    0 0 0 1px var(--c),
    inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
}
.kpi-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}
.kpi-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  background: linear-gradient(135deg,
    color-mix(in srgb, var(--c) 35%, transparent) 0%,
    color-mix(in srgb, var(--c) 15%, transparent) 100%) !important;
  color: var(--c) !important;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  filter: drop-shadow(0 0 12px color-mix(in srgb, var(--c) 50%, transparent));
  border: 1px solid color-mix(in srgb, var(--c) 30%, transparent);
}
.kpi-body { flex: 1; }
.kpi-num {
  font-size: 28px;
  font-weight: 700;
  color: var(--c) !important;
  line-height: 1.1;
  text-shadow: 0 0 16px color-mix(in srgb, var(--c) 40%, transparent);
  font-family: 'DIN Pro', 'Helvetica Neue', sans-serif;
}
.kpi-label {
  font-size: 12px;
  color: #c4b5fd;
  margin-top: 4px;
  letter-spacing: 0.5px;
}

/* ========== 普通卡片（图表 / 表格）：蓝紫玻璃 ========== */
.chart-row { margin-bottom: 12px; position: relative; z-index: 1; }
.chart-row .el-col { margin-bottom: 12px; }
.chart-row :deep(.el-card) {
  background: linear-gradient(135deg,
    rgba(59, 130, 246, 0.12) 0%,
    rgba(168, 85, 247, 0.08) 100%) !important;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(99, 102, 241, 0.30) !important;
  box-shadow:
    0 4px 20px rgba(59, 130, 246, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
}
.chart-row :deep(.el-card__header) {
  border-bottom: 1px solid rgba(99, 102, 241, 0.25) !important;
  padding: 14px 16px;
}
.bottom-row .el-col { margin-bottom: 12px; }
.bottom-row :deep(.el-card) {
  background: linear-gradient(135deg,
    rgba(59, 130, 246, 0.12) 0%,
    rgba(168, 85, 247, 0.08) 100%) !important;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(99, 102, 241, 0.30) !important;
  box-shadow:
    0 4px 20px rgba(59, 130, 246, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
}
.bottom-row :deep(.el-card__header) {
  border-bottom: 1px solid rgba(99, 102, 241, 0.25) !important;
  padding: 14px 16px;
}

.chart-box { height: 260px; }
.chart-dept { height: 320px; }

/* ========== 卡片标题：蓝紫霓虹文字 ========== */
.card-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  color: #e0e7ff !important;
}
.card-hd > span {
  display: flex;
  align-items: center;
  gap: 6px;
}
.card-hd .el-icon { color: #60a5fa !important; filter: drop-shadow(0 0 6px rgba(96, 165, 250, 0.6)); }
.card-hd :deep(.el-link) { color: #93c5fd !important; }
.card-hd :deep(.el-link:hover) { color: #c4b5fd !important; }

/* ========== 表格：深蓝紫风格 ========== */
:deep(.el-table) {
  --el-table-bg-color: transparent !important;
  --el-table-tr-bg-color: transparent !important;
  --el-table-header-bg-color: rgba(99, 102, 241, 0.15) !important;
  --el-table-row-hover-bg-color: rgba(99, 102, 241, 0.14) !important;
  --el-table-border-color: rgba(99, 102, 241, 0.22) !important;
  --el-table-header-text-color: #e0e7ff !important;
  --el-table-text-color: #c7d2fe !important;
  color: #c7d2fe !important;
}
:deep(.el-table th.el-table__cell) {
  background: rgba(99, 102, 241, 0.18) !important;
  color: #e0e7ff !important;
  font-weight: 600;
  border-bottom: 1px solid rgba(99, 102, 241, 0.30) !important;
}
:deep(.el-table td.el-table__cell) {
  background: transparent !important;
  border-bottom: 1px solid rgba(99, 102, 241, 0.15) !important;
  color: #c7d2fe !important;
}
:deep(.el-table tr:hover > td.el-table__cell) {
  background: rgba(99, 102, 241, 0.14) !important;
}
:deep(.el-table .el-table__empty-block) {
  background: transparent !important;
  color: #93c5fd !important;
}
:deep(.el-table .el-empty__description p) { color: #93c5fd !important; }

/* ========== 标签 ========== */
:deep(.el-tag--plain) {
  background: rgba(99, 102, 241, 0.12) !important;
  border-color: rgba(99, 102, 241, 0.35) !important;
  color: #a5b4fc !important;
}

/* ========== 快捷操作 ========== */
.shortcut-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.shortcut-item {
  height: 70px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: linear-gradient(135deg,
    rgba(59, 130, 246, 0.14) 0%,
    rgba(168, 85, 247, 0.10) 100%);
  border: 1px solid rgba(99, 102, 241, 0.30);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s;
  font-size: 12px;
  color: #a5b4fc;
  position: relative;
  overflow: hidden;
}
.shortcut-item::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 0%, rgba(99, 102, 241, 0.25) 100%);
  opacity: 0;
  transition: opacity 0.25s;
}
.shortcut-item:hover {
  background: linear-gradient(135deg,
    rgba(59, 130, 246, 0.30) 0%,
    rgba(168, 85, 247, 0.25) 100%);
  border-color: rgba(96, 165, 250, 0.7);
  color: #f0f4ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.40);
}
.shortcut-item:hover::before { opacity: 1; }
.shortcut-item .el-icon, .shortcut-item > span { position: relative; z-index: 1; }
</style>
