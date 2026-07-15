<template>
  <div class="page-container">
    <el-page-header :icon="ArrowLeft" content="返回盘点列表" @back="$router.push('/checks')">
      <template #content>
        <span class="page-title-inline">
          <el-icon><Collection /></el-icon> 协同盘点 · 任务 #{{ taskId }}
        </span>
      </template>
    </el-page-header>

    <el-skeleton v-if="loading" :rows="6" animated class="mt-16" />

    <template v-else-if="task">
      <el-row :gutter="12" class="mt-16">
        <el-col :span="8">
          <el-card shadow="never">
            <template #header><span>任务信息</span></template>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="任务名称">{{ task.task_name }}</el-descriptions-item>
              <el-descriptions-item label="盘点范围">
                <el-tag v-if="task.scope_type === 'ALL'" size="small">全校</el-tag>
                <el-tag v-else-if="task.scope_type === 'ASSET'" size="small" type="warning">按资产 · {{ (task.scope_asset_ids||[]).length }} 项</el-tag>
                <el-tag v-else size="small">按学院 · {{ (task.scope_dept_ids||[]).length }} 个</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="创建人">{{ task.manager_name }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="statusType(task.status)" size="small">
                  {{ CHECK_STATUS_NAME[task.status] || task.status }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="开始时间">{{ task.start_time || '-' }}</el-descriptions-item>
              <el-descriptions-item label="结束时间">{{ task.end_time || '-' }}</el-descriptions-item>
              <el-descriptions-item label="盘点明细">
                <el-statistic :value="details.length" style="display:inline-block" />
                <span class="text-muted"> 条 · 已录入 {{ filledCount }} 条</span>
              </el-descriptions-item>
            </el-descriptions>
            <div class="mt-12 action-row">
              <el-button
                v-if="task.status === 'PENDING' && userStore.hasRole(['admin', 'college_admin'])"
                type="warning" @click="onStart" :loading="starting"
              >开始盘点</el-button>
              <el-button
                v-if="task.status === 'IN_PROGRESS'"
                type="primary" @click="onSave" :loading="saving"
              >保存录入</el-button>
              <el-button
                v-if="task.status === 'IN_PROGRESS'"
                type="success" @click="onAnalyze" :loading="analyzing"
              >生成差异报告</el-button>
            </div>
            <el-alert
              v-if="task.status === 'PENDING'"
              class="mt-8" type="info" :closable="false" show-icon
              title="提示：点击「开始盘点」后会自动按范围生成账面快照行"
            />
            <el-alert
              v-else-if="task.status === 'IN_PROGRESS'"
              class="mt-8" type="success" :closable="false" show-icon
              :title="`提示：行数固定 ${details.length}，只可编辑「实盘」3 列；点击保存后自动跳过空白行`"
            />
          </el-card>
        </el-col>

        <el-col :span="16">
          <el-card shadow="never">
            <template #header>
              <div class="card-hd">
                <span>盘点明细表</span>
                <span class="text-muted">
                  只读：资产编号/名称/规格/账面地点/账面状态；可编辑：实盘地点/实盘状态/备注
                </span>
              </div>
            </template>

            <div
              v-if="task.status !== 'PENDING'"
              id="luckysheet-container"
              class="luckysheet-host"
            ></div>
            <el-empty
              v-else description="请先点击「开始盘点」生成账面快照行"
            />
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-empty v-else description="任务不存在" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Collection, ArrowLeft } from '@element-plus/icons-vue'
import {
  getSheetDataApi, saveSheetDataApi, analyzeDiffApi, startCheckTaskApi,
} from '@/api/check'
import { listAssetStatusApi } from '@/api/asset'
import { useUserStore } from '@/store/user'

// import luckysheet from 'luckysheet'
// window.luckysheet = luckysheet

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const taskId = Number(route.params.id)

const loading = ref(false)
const saving = ref(false)
const analyzing = ref(false)
const starting = ref(false)
const task = ref<any>(null)
const details = ref<any[]>([])
const assetStatusOptions = ref<any[]>([])

const CHECK_STATUS_NAME: Record<string, string> = {
  PENDING: '待开始', IN_PROGRESS: '进行中', CONFIRMED: '已完成'
}
function statusType(s: string) {
  if (s === 'PENDING') return 'warning'
  if (s === 'IN_PROGRESS') return 'primary'
  // if (s === 'DONE') return 'success'
  if (s === 'CONFIRMED') return 'success'
  return 'info'
}

const filledCount = ref(0)
let luckysheetRef: any = null



const COLUMNS = [
  { key: 'asset_code',      label: '资产编号', readonly: true },
  { key: 'asset_name',      label: '资产名称', readonly: true },
  { key: 'asset_spec',      label: '规格',     readonly: true },
  { key: 'book_location',   label: '账面地点', readonly: true },
  { key: 'book_status',     label: '账面状态', readonly: true },
  { key: 'actual_location', label: '实盘地点', readonly: false },
  { key: 'actual_status',   label: '实盘状态', readonly: false, type: 'dropdown' },
  { key: 'remark',          label: '备注',     readonly: false },
]

async function fetchAll() {
  loading.value = true
  try {
    const res: any = await getSheetDataApi(taskId)
    if (res?.data?.error) {
      ElMessage.error(res.data.error)
      task.value = null
      return
    }
    task.value = res?.data?.task || null
    details.value = res?.data?.details || []
    if (task.value) {
      nextTick(() => renderLuckysheet())
    }
  } finally { loading.value = false }
}

/**
 * 构造 Luckysheet 标准数据格式
 * Luckysheet 期望 data 是 sheet 对象数组：[{ name, index, celldata, config }]
 * - celldata 每个 cell 必须填（空字符串占位），避免 Luckysheet 把缺失识别为 null
 * - data 中所有字段（r, c, v）必须同时存在
 */
function buildLuckysheetData() {
  const celldata: any[] = []

  // 表头
  COLUMNS.forEach((c, cIdx) => {
    celldata.push({
      r: 0,
      c: cIdx,
      v: { v: c.label, m: c.label, bl: 1, ct: { fa: 'General', t: 's' } },
    })
  })

  // 数据行
  details.value.forEach((d, rowIndex) => {
    const r = rowIndex + 1
    COLUMNS.forEach((c, cIdx) => {
      let raw: any = d[c.key]
      if (c.type === 'dropdown' && c.key === 'actual_status'
          && raw !== '' && raw !== null && raw !== undefined) {
        // 把后端 status_id 数字 / status_code 字符串统一转 status_code 显示
        const found = assetStatusOptions.value.find(
          (s) => String(s.status_id) === String(raw) || s.status_code === raw
        )
        raw = found ? found.status_code : raw
      }
      const v = raw === null || raw === undefined ? '' : String(raw)
      celldata.push({
        r, c: cIdx,
        v: { v, m: v, ct: { fa: 'General', t: 's' } },
      })
    })
  })

  // 占位空行（防止 Luckysheet 把"超出长度"识别为 null）
  for (let r = details.value.length + 1; r <= details.value.length + 5; r++) {
    for (let cIdx = 0; cIdx < COLUMNS.length; cIdx++) {
      celldata.push({ r, c: cIdx, v: { v: '', m: '', ct: { fa: 'General', t: 's' } } })
    }
  }

  return [
    {
      name: '盘点明细',
      index: 0,
      status: 0,
      order: 0,
      celldata,
      config: {
        freeze: 'A2',
        columnlen: {
          0: 140, 1: 180, 2: 140, 3: 160, 4: 100, 5: 160, 6: 100, 7: 200,
        },
        rowlen: { 0: 28 },
      },
    },
  ]
}

function buildLuckysheetColumn() {
  return COLUMNS.map((c, idx) => {
    const col: any = {
      index: idx,
      width: (c.key === 'asset_name' || c.key === 'asset_spec' || c.key === 'remark') ? 160 : 120,
      name: c.label,
    }
    if (c.readonly) col.locked = true
    return col
  })
}

/**
 * 等待容器就绪 + 确认 jQuery mousewheel 插件已挂上 + window.luckysheet 已就绪
 * webview 端验证过的写法，避免 race condition
 */
function waitLuckysheetReady(maxMs = 5000): Promise<void> {
  return new Promise((resolve, reject) => {
    const start = Date.now()
    const tick = () => {
      const el = document.getElementById('luckysheet-container')
      const $ = (window as any).$
      const luckysheet = (window as any).luckysheet
      // 注意：不检查 el.offsetHeight，因为 Luckysheet 渲染时会替换容器内容，offsetHeight 可能瞬时为 0
      if (el && $?.fn?.mousewheel && luckysheet) {
        resolve()
        return
      }
      if (Date.now() - start > maxMs) {
        reject(new Error('Luckysheet 依赖未就绪（jQuery / mousewheel / window.luckysheet）'))
        return
      }
      setTimeout(tick, 30)
    }
    tick()
  })
}

async function renderLuckysheet() {
  // index.html 同步加载了 jQuery / jquery-mousewheel / luckysheet UMD
  // 此时 window.$ / window.jQuery / $.fn.mousewheel / window.luckysheet 都已经就绪
  const cluckysheet = (window as any).luckysheet
  if (!cluckysheet) {
    ElMessage.error('Luckysheet 加载失败：window.luckysheet 不存在（请检查 index.html 中 <script src="/luckysheet.umd.js"> 是否被加载）')
    console.error('[Sheet] window.luckysheet=', cluckysheet, 'window.$=', (window as any).$, '$.fn.mousewheel=', (window as any).$?.fn?.mousewheel)
    return
  }
  if (!(window as any).$ || !(window as any).jQuery) {
    ElMessage.error('jQuery 未挂载到 window（请检查 index.html 中 <script src="/jquery.min.js">）')
    return
  }
  if (!(window as any).$?.fn?.mousewheel) {
    ElMessage.error('jquery-mousewheel 插件未挂载到 $.fn（请检查 index.html 中 <script src="/jquery.mousewheel.min.js"> 是否在 luckysheet 之前加载）')
    return
  }

  try {
    await waitLuckysheetReady()
  } catch (e) {
    ElMessage.error(String((e as Error).message || e))
    return
  }

  try { cluckysheet.destroy?.() } catch { /* ignore */ }

  const data = buildLuckysheetData()
  const column = buildLuckysheetColumn()

  cluckysheet.create({
    container: 'luckysheet-container',
    title: '',
    lang: 'zh',
    showtoolbar: false,
    showinfobar: false,
    showsheetbar: false,
    showstatisticBar: false,
    enableAddRow: false,
    enableAddCol: false,
    enableDelRow: false,
    enableDelCol: false,
    data,
    column,
    allowEdit: true,
    allowCopy: true,
    hook: {
      workbookCreateAfter: () => {
        console.log('[Sheet] Luckysheet 创建成功，行数=', details.value.length)
      },
    },
  })
  luckysheetRef = cluckysheet
  recalcFilled()
}

function recalcFilled() {
  let n = 0
  details.value.forEach((d) => {
    if (d.actual_location || d.actual_status || d.remark) n++
  })
  filledCount.value = n
}

/**
 * 把 Luckysheet 当前 cellData 抽取成 details 数组（强清洗）
 * - 任何 null / undefined / 'null' / 'undefined' / 空白 → 视为未录入
 * - 全部 3 个可编辑列都空的行不发送
 */
function extractDetailsFromSheet(): any[] {
  if (!luckysheetRef) return []

  const norm = (v: any): any => {
    if (v === null || v === undefined) return null
    if (typeof v === 'object' && v !== null) {
      const inner = v.v ?? v
      if (inner === null || inner === undefined) return null
      if (typeof inner === 'object') return null
      if (typeof inner === 'string') {
        const s = inner.trim()
        if (s === '' || ['null', 'undefined', 'none', 'nan'].includes(s.toLowerCase())) return null
        return s
      }
      return inner
    }
    if (typeof v === 'string') {
      const s = v.trim()
      if (s === '' || ['null', 'undefined', 'none', 'nan'].includes(s.toLowerCase())) return null
      return s
    }
    return v
  }

  const out: any[] = []
  const rowCount = details.value.length

  // 优先用 v2 getSheetData(0) 返回二维数组（webview 验证过最稳）
  let gridData: any[][] | null = null
  if (typeof luckysheetRef.getSheetData === 'function') {
    try {
      const data = luckysheetRef.getSheetData(0)
      if (Array.isArray(data) && Array.isArray(data[0])) {
        gridData = data
      }
    } catch (e) {
      console.warn('[Sheet] getSheetData 失败，回退 getAllData', e)
    }
  }
  // fallback：v1 风格的 getAllData / celldata
  if (!gridData) {
    const allSheets: any[] = luckysheetRef.getAllData?.() || []
    const sheet = allSheets[0]
    const cells: any[] = sheet?.celldata || []
    const byRow = new Map<number, any>()
    for (const c of cells) {
      if (!byRow.has(c.r)) byRow.set(c.r, {})
      byRow.get(c.r)[c.c] = c
    }
    // 转成二维
    gridData = []
    for (let r = 0; r <= rowCount; r++) {
      const rowCells = byRow.get(r) || {}
      const row: any[] = []
      for (let c = 0; c < COLUMNS.length; c++) {
        row.push(rowCells[c]?.v ?? null)
      }
      gridData.push(row)
    }
  }

  // 表头是第 0 行，从第 1 行开始取数据
  for (let rIdx = 0; rIdx < rowCount; rIdx++) {
    const r = rIdx + 1
    const orig = details.value[rIdx]
    const gridRow = gridData[r] || []
    const row: any = {
      asset_id: orig.asset_id,
      asset_code: orig.asset_code || '',
      asset_name: orig.asset_name || '',
      asset_spec: orig.asset_spec || '',
      book_location: orig.book_location || '',
      book_status: orig.book_status || '',
    }
    for (let cIdx = 0; cIdx < COLUMNS.length; cIdx++) {
      const key = COLUMNS[cIdx].key
      let v: any
      if (typeof gridRow[cIdx] === 'object' && gridRow[cIdx] !== null) {
        v = gridRow[cIdx].v ?? gridRow[cIdx].m ?? null
      } else {
        v = gridRow[cIdx]
      }
      row[key] = norm(v)
    }
    // actual_status 字符串 → 数字 id
    if (row.actual_status) {
      const found = assetStatusOptions.value.find((s) => s.status_code === row.actual_status)
      if (found) row.actual_status = found.status_id
    }
    out.push(row)
  }
  return out
}

async function onStart() {
  await ElMessageBox.confirm('确定开始盘点？系统将按盘点范围自动生成账面快照行。', '提示', { type: 'warning' })
  starting.value = true
  try {
    const res: any = await startCheckTaskApi(taskId)
    if (res?.data?.error) { ElMessage.error(res.data.error); return }
    ElMessage.success('已开始')
    await fetchAll()
  } finally { starting.value = false }
}

async function onSave() {
  if (!luckysheetRef) { ElMessage.warning('表格未就绪'); return }
  const raw = extractDetailsFromSheet()
  const cleaned = raw.filter((d) => {
    if (d.actual_location) return true
    if (d.actual_status !== null && d.actual_status !== undefined && d.actual_status !== '') return true
    if (d.remark) return true
    return false
  })
  if (cleaned.length === 0) { ElMessage.warning('没有任何实盘录入，请填写后再保存'); return }
  saving.value = true
  try {
    const res: any = await saveSheetDataApi({ task_id: taskId, details: cleaned })
    if (res?.data?.error) { ElMessage.error(res.data.error); return }
    ElMessage.success(`保存成功 ${res?.data?.saved_count ?? cleaned.length} 条（跳过空行 ${res?.data?.skipped_count ?? 0}）`)
    // 同步回本地 details 用于刷新已录入数
    details.value = details.value.map((d, idx) => {
      const upd = cleaned.find((c) => c.asset_id === d.asset_id)
      return upd ? { ...d, ...upd } : d
    })
    recalcFilled()
  } finally { saving.value = false }
}

async function onAnalyze() {
  if (!details.value?.length) {
    ElMessage.warning('无盘点明细数据，请先开始盘点')
    return
  }
  if (filledCount.value === 0) {
    await ElMessageBox.confirm('当前任务还没有任何实盘录入，仍要继续生成差异报告吗？', '提示', { type: 'warning' })
  } else {
    await ElMessageBox.confirm('将基于当前明细生成差异报告，是否继续？', '提示', { type: 'warning' })
  }
  analyzing.value = true
  try {
    const res: any = await analyzeDiffApi(taskId)
    if (res?.data?.error) { ElMessage.error(res.data.error); return }
    ElMessage.success('差异已生成')
    router.push(`/checks/${taskId}/report`)
  } finally { analyzing.value = false }
}

async function loadStatusOptions() {
  const res: any = await listAssetStatusApi()
  // 仅显示 asset 阶段的状态（IDLE/USING/REPAIRING/ABANDON）
  assetStatusOptions.value = (res?.data || []).filter(
    (s: any) => s.phase === 'asset' && ['IDLE', 'USING', 'REPAIRING', 'ABANDON'].includes(s.status_code)
  )
}

onMounted(async () => {
  await loadStatusOptions()
  await fetchAll()
})

onBeforeUnmount(() => {
  try { luckysheetRef?.destroy?.() } catch { /* ignore */ }
})
</script>

<style scoped>
.page-title-inline {
  font-size: 18px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.card-hd { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.text-muted { color: #909399; }
.action-row { display: flex; flex-wrap: wrap; gap: 8px; }
.luckysheet-host {
  width: 100%;
  height: 540px;
  margin: 0;
  padding: 0;
}
</style>
