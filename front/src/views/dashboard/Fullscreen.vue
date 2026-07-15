<template>
  <div class="fullscreen-root">
    <!-- 顶部标题栏（带关闭/退出按钮） -->
    <div class="fs-header">
      <div class="fs-title">
        <el-icon :size="22" color="#22d3ee"><Monitor /></el-icon>
        <span>固定资产协同管理 · 数据大屏</span>
        <el-tag size="small" effect="dark" type="success" class="ml-8">实时</el-tag>
      </div>
      <div class="fs-info">
        <span class="fs-time">{{ now }}</span>
        <el-button :icon="Close" size="small" plain @click="exitFullscreen">退出全屏</el-button>
      </div>
    </div>

    <!-- KPI 指标行 -->
    <div class="fs-kpis">
      <div v-for="k in kpis" :key="k.key" class="fs-kpi" :style="{ '--c': k.color }">
        <el-icon :size="28"><component :is="k.icon" /></el-icon>
        <div class="fs-kpi-body">
          <div class="fs-kpi-num">{{ k.value }}</div>
          <div class="fs-kpi-label">{{ k.label }}</div>
        </div>
      </div>
    </div>

    <!-- 图表区（4 个图表铺满） -->
    <div class="fs-charts">
      <div class="fs-chart-box">
        <div class="fs-chart-title">近 6 月资产新增趋势</div>
        <div ref="lineRef" class="fs-chart-canvas"></div>
      </div>
      <div class="fs-chart-box">
        <div class="fs-chart-title">资产状态分布</div>
        <div ref="pieRef" class="fs-chart-canvas"></div>
      </div>
      <div class="fs-chart-box">
        <div class="fs-chart-title">资产分类分布</div>
        <div ref="catRef" class="fs-chart-canvas"></div>
      </div>
      <div class="fs-chart-box">
        <div class="fs-chart-title">各学院资产数量 TOP 10</div>
        <div ref="deptRef" class="fs-chart-canvas"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  Monitor, Box, Tools, Checked, Close,
} from '@element-plus/icons-vue'
import { getDashboardApi, getAssetReportApi } from '@/api/report'
import { listAssetStatusApi } from '@/api/asset'

const overview = ref<any>({})
const statusNameMap = ref<Record<number, string>>({})

const kpis = computed(() => [
  { key: 'asset_total', label: '资产总数', value: overview.value.asset_total ?? 0, color: '#22d3ee', icon: Box },
  { key: 'pending_repairs', label: '待处理工单', value: overview.value.pending_repairs ?? 0, color: '#f59e0b', icon: Tools },
  { key: 'in_progress', label: '维修中', value: overview.value.in_progress_repairs ?? 0, color: '#ec4899', icon: Tools },
  { key: 'pending_acceptance', label: '待验收', value: overview.value.pending_acceptance ?? 0, color: '#10b981', icon: Checked },
])

// 实时时间
const now = ref('')
let timeTimer: any = null
function tick() {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  const week = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
  now.value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} 周${week} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// 图表 ref
const lineRef = ref<HTMLElement>()
const pieRef = ref<HTMLElement>()
const catRef = ref<HTMLElement>()
const deptRef = ref<HTMLElement>()
const charts: echarts.ECharts[] = []

function genLast6Months() {
  const arr: string[] = []
  const d = new Date()
  for (let i = 5; i >= 0; i--) {
    const dt = new Date(d.getFullYear(), d.getMonth() - i, 1)
    arr.push(`${dt.getMonth() + 1}月`)
  }
  return arr
}

function makeLineChart(monthlyData: { month: string; count: number }[]) {
  if (!lineRef.value) return
  const chart = echarts.init(lineRef.value)
  const months = monthlyData.length ? monthlyData.map((d) => d.month) : genLast6Months()
  const values = monthlyData.length ? monthlyData.map((d) => d.count) : months.map(() => 0)
  chart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(20, 24, 60, 0.92)', borderColor: '#3b82f6', textStyle: { color: '#e0e7ff' } },
    grid: { left: 30, right: 16, top: 16, bottom: 28 },
    xAxis: { type: 'category', data: months, axisLine: { lineStyle: { color: 'rgba(99,102,241,0.4)' } }, axisLabel: { color: '#a5b4fc', fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { color: '#93c5fd' }, splitLine: { lineStyle: { color: 'rgba(99,102,241,0.12)' } } },
    series: [{
      name: '新增', type: 'line', smooth: true, data: values,
      lineStyle: { color: '#22d3ee', width: 3 },
      itemStyle: { color: '#22d3ee', borderColor: '#fff', borderWidth: 2 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(34, 211, 238, 0.55)' },
        { offset: 1, color: 'rgba(34, 211, 238, 0.05)' },
      ]) },
      symbol: 'circle', symbolSize: 8,
    }],
  })
  charts.push(chart)
}

function makePieChart(el: HTMLElement | undefined, data: { name: string; value: number }[]) {
  if (!el) return
  const chart = echarts.init(el)
  // 多彩配色
  const palette = ['#22d3ee', '#3b82f6', '#a855f7', '#ec4899', '#f59e0b', '#10b981', '#8b5cf6', '#06b6d4']
  const themedData = data.length
    ? data.map((d, i) => ({ ...d, itemStyle: { color: palette[i % palette.length] } }))
    : [{ name: '暂无', value: 1, itemStyle: { color: 'rgba(99,102,241,0.20)' } }]
  chart.setOption({
    tooltip: { trigger: 'item', backgroundColor: 'rgba(20, 24, 60, 0.92)', borderColor: '#3b82f6', textStyle: { color: '#e0e7ff' } },
    legend: { bottom: 0, textStyle: { fontSize: 11, color: '#a5b4fc' } },
    series: [{
      type: 'pie', radius: ['38%', '70%'], center: ['50%', '45%'],
      data: themedData, label: { fontSize: 11, color: '#e0e7ff' },
      itemStyle: { borderColor: 'rgba(10, 14, 42, 0.6)', borderWidth: 2 },
    }],
  })
  charts.push(chart)
}

function makeDeptChart(el: HTMLElement | undefined, data: { name: string; value: number }[]) {
  if (!el) return
  // 只取 TOP 10
  const top = [...data].sort((a, b) => b.value - a.value).slice(0, 10)
  const chart = echarts.init(el)
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(34,211,238,0.12)' } }, backgroundColor: 'rgba(20, 24, 60, 0.92)', borderColor: '#22d3ee', textStyle: { color: '#e0e7ff' } },
    grid: { left: 90, right: 30, top: 10, bottom: 20 },
    xAxis: { type: 'value', axisLabel: { color: '#93c5fd' }, splitLine: { lineStyle: { color: 'rgba(99,102,241,0.12)' } } },
    yAxis: { type: 'category', data: top.length ? top.map((d) => d.name) : ['暂无'], axisLabel: { color: '#a5b4fc', fontSize: 11 } },
    series: [{
      type: 'bar',
      data: top.length ? top.map((d) => d.value) : [0],
      barWidth: '50%',
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#06b6d4' },
          { offset: 0.6, color: '#3b82f6' },
          { offset: 1, color: '#a855f7' },
        ]),
        borderRadius: [0, 4, 4, 0],
        shadowBlur: 12,
        shadowColor: 'rgba(99, 102, 241, 0.6)',
      },
      label: { show: true, position: 'right', color: '#e0e7ff' },
    }],
  })
  charts.push(chart)
}

async function loadStatusMap() {
  try {
    const res: any = await listAssetStatusApi()
    const list = res?.data || []
    const map: Record<number, string> = {}
    list.forEach((s: any) => (map[s.status_id] = s.status_name))
    statusNameMap.value = map
  } catch { /* ignore */ }
}

function handleResize() {
  charts.forEach((c) => c.resize())
}

/** 退出全屏（关 tab） */
function exitFullscreen() {
  // 先尝试退出浏览器全屏
  try {
    if (document.fullscreenElement) {
      const exit = document.exitFullscreen || (document as any).webkitExitFullscreen
        || (document as any).mozCancelFullScreen || (document as any).msExitFullscreen
      if (exit) exit.call(document)
    }
  } catch { /* ignore */ }
  // 然后关闭当前 tab
  setTimeout(() => {
    try { window.close() }
    catch { ElMessage.info('请按 Ctrl+W 关闭此页') }
  }, 200)
}

onMounted(async () => {
  tick()
  timeTimer = setInterval(tick, 1000)
  await loadStatusMap()
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
      setTimeout(() => {
        makeLineChart(ad.monthly_new || [])
        makePieChart(pieRef.value, statusPie)
        makePieChart(catRef.value, catPie)
        makeDeptChart(deptRef.value, deptBar)
      }, 50)
    }),
  ])
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  if (timeTimer) clearInterval(timeTimer)
  charts.forEach((c) => c.dispose())
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
/* 全屏大屏根容器 — 蓝紫渐变 + 光斑 */
.fullscreen-root {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  padding: 16px 24px;
  background:
    radial-gradient(ellipse 1000px 600px at 10% 10%, rgba(34, 211, 238, 0.18) 0%, transparent 60%),
    radial-gradient(ellipse 1200px 700px at 90% 30%, rgba(99, 102, 241, 0.22) 0%, transparent 60%),
    radial-gradient(ellipse 1100px 600px at 50% 95%, rgba(168, 85, 247, 0.18) 0%, transparent 60%),
    linear-gradient(135deg, #050918 0%, #0a1130 30%, #141b4d 60%, #0d1635 100%);
  overflow: hidden;
}
.fullscreen-root::before {
  content: '';
  position: absolute;
  top: -200px; right: -200px;
  width: 600px; height: 600px;
  background: radial-gradient(circle, rgba(34, 211, 238, 0.35) 0%, transparent 70%);
  filter: blur(60px);
  animation: float 20s ease-in-out infinite;
  pointer-events: none;
}
.fullscreen-root::after {
  content: '';
  position: absolute;
  bottom: -200px; left: -200px;
  width: 600px; height: 600px;
  background: radial-gradient(circle, rgba(168, 85, 247, 0.35) 0%, transparent 70%);
  filter: blur(60px);
  animation: float 24s ease-in-out infinite reverse;
  pointer-events: none;
}
@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(60px, -40px) scale(1.15); }
}

/* 顶部标题栏 */
.fs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.20) 0%, rgba(99, 102, 241, 0.18) 50%, rgba(168, 85, 247, 0.20) 100%);
  border: 1px solid rgba(99, 102, 241, 0.40);
  border-radius: 14px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 4px 24px rgba(59, 130, 246, 0.25);
  position: relative;
  z-index: 1;
  margin-bottom: 16px;
}
.fs-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #f0f4ff;
  text-shadow: 0 0 20px rgba(34, 211, 238, 0.5);
  letter-spacing: 1px;
}
.fs-title :deep(.el-tag) {
  background: linear-gradient(135deg, #10b981 0%, #22d3ee 100%) !important;
  border: none !important;
  color: #fff !important;
}
.fs-info { display: flex; align-items: center; gap: 12px; }
.fs-time {
  font-size: 14px;
  color: #a5b4fc;
  font-family: 'Consolas', 'Monaco', monospace;
  letter-spacing: 0.5px;
}
.fs-info :deep(.el-button) {
  background: rgba(239, 68, 68, 0.15) !important;
  border-color: rgba(239, 68, 68, 0.5) !important;
  color: #fecaca !important;
}
.fs-info :deep(.el-button:hover) {
  background: rgba(239, 68, 68, 0.30) !important;
  color: #fff !important;
}

/* KPI 指标行 */
.fs-kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
}
.fs-kpi {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  background: linear-gradient(135deg,
    rgba(34, 211, 238, 0.12) 0%,
    rgba(99, 102, 241, 0.10) 50%,
    rgba(168, 85, 247, 0.12) 100%);
  border: 1px solid var(--c);
  border-radius: 14px;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 4px 20px color-mix(in srgb, var(--c) 30%, transparent);
  transition: transform 0.25s, box-shadow 0.25s;
  position: relative;
  overflow: hidden;
}
.fs-kpi::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent 0%, var(--c) 50%, transparent 100%);
}
.fs-kpi:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 32px color-mix(in srgb, var(--c) 50%, transparent);
}
.fs-kpi .el-icon {
  color: var(--c);
  filter: drop-shadow(0 0 12px var(--c));
}
.fs-kpi-body { flex: 1; }
.fs-kpi-num {
  font-size: 32px;
  font-weight: 700;
  color: var(--c);
  line-height: 1.1;
  text-shadow: 0 0 16px color-mix(in srgb, var(--c) 50%, transparent);
  font-family: 'DIN Pro', 'Helvetica Neue', sans-serif;
}
.fs-kpi-label {
  font-size: 13px;
  color: #a5b4fc;
  margin-top: 4px;
  letter-spacing: 0.5px;
}

/* 图表区（2x2 网格） */
.fs-charts {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 16px;
  min-height: 0;
  position: relative;
  z-index: 1;
}
.fs-chart-box {
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg,
    rgba(34, 211, 238, 0.10) 0%,
    rgba(99, 102, 241, 0.08) 50%,
    rgba(168, 85, 247, 0.10) 100%);
  border: 1px solid rgba(99, 102, 241, 0.30);
  border-radius: 14px;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 4px 24px rgba(59, 130, 246, 0.18);
  padding: 16px 20px;
  overflow: hidden;
  position: relative;
}
.fs-chart-box::before {
  content: '';
  position: absolute;
  top: 0; left: 16px; right: 16px;
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, #22d3ee 50%, transparent 100%);
}
.fs-chart-title {
  font-size: 15px;
  font-weight: 600;
  color: #e0e7ff;
  text-shadow: 0 0 12px rgba(34, 211, 238, 0.4);
  margin-bottom: 8px;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}
.fs-chart-canvas {
  flex: 1;
  min-height: 0;
}

.ml-8 { margin-left: 8px; }
</style>
