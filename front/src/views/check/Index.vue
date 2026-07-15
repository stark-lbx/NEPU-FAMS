<template>
  <div class="page-container">
    <div class="page-title">
      <el-icon><Collection /></el-icon> 资产盘点
    </div>

    <!-- KPI -->
    <el-row :gutter="12" class="kpi-row">
      <el-col :xs="6"><el-card class="kpi" shadow="hover"><div class="kpi-num">{{ kpi.total }}</div><div class="kpi-label">任务总数</div></el-card></el-col>
      <el-col :xs="6"><el-card class="kpi" shadow="hover"><div class="kpi-num text-warning">{{ kpi.pending }}</div><div class="kpi-label">待开始</div></el-card></el-col>
      <el-col :xs="6"><el-card class="kpi" shadow="hover"><div class="kpi-num text-primary">{{ kpi.ongoing }}</div><div class="kpi-label">进行中</div></el-card></el-col>
      <el-col :xs="6"><el-card class="kpi" shadow="hover"><div class="kpi-num text-success">{{ kpi.done }}</div><div class="kpi-label">已完成</div></el-card></el-col>
    </el-row>

    <!-- 过滤 -->
    <el-card class="search-card" shadow="never">
      <el-form :inline="true" :model="query" size="default" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" placeholder="任务名" clearable style="width:200px" @keyup.enter="onSearch" @clear="onSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable style="width:150px" @change="onSearch" @clear="onSearch">
            <el-option label="待开始" value="PENDING" />
            <el-option label="进行中" value="IN_PROGRESS" />
            <el-option label="已完成" value="CONFIRMED" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="onSearch">查询</el-button>
          <el-button :icon="Refresh" @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 操作栏 -->
    <el-card shadow="never" class="mb-12">
      <div class="toolbar">
        <span class="text-muted">共 {{ total }} 条</span>
        <div>
          <el-button
            v-if="userStore.hasRole(['admin', 'college_admin'])"
            type="primary" :icon="Plus" @click="openCreate"
          >创建盘点任务</el-button>
        </div>
      </div>
    </el-card>

    <!-- 表格 -->
    <el-card shadow="never">
      <el-table
        v-loading="loading"
        :data="displayList"
        stripe
        border
        @sort-change="handleSortChange"
      >
        <el-table-column prop="task_id" label="#" width="70" sortable="custom" />
        <el-table-column prop="task_name" label="任务名称" min-width="180" show-overflow-tooltip sortable="custom" />
        <el-table-column label="盘点范围" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <template v-if="row.scope_type === 'ALL'">全校</template>
            <template v-else-if="row.scope_type === 'ASSET'">
              <el-tag size="small" type="warning">按资产</el-tag>
              <span class="ml-4">已选 {{ (row.scope_asset_ids || []).length }} 项</span>
            </template>
            <template v-else>
              <el-tag size="small">按学院</el-tag>
              <span class="ml-4">{{ (row.scope_dept_ids || []).length }} 个</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column prop="manager_name" label="创建人" width="100" />
        <el-table-column prop="start_time" label="开始时间" width="160" show-overflow-tooltip sortable="custom" />
        <el-table-column prop="end_time" label="结束时间" width="160" show-overflow-tooltip sortable="custom" />
        <el-table-column label="状态" width="100" prop="status" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ CHECK_STATUS_NAME[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="160" sortable="custom">
          <template #default="{ row }">{{ formatDate(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="$router.push(`/checks/${row.task_id}`)">
              录入
            </el-button>
            <el-button type="success" link size="small" @click="$router.push(`/checks/${row.task_id}/report`)">
              报告
            </el-button>
            <el-button
              v-if="row.status === 'PENDING' && userStore.hasRole(['admin', 'college_admin'])"
              type="warning" link size="small" @click="onStart(row)"
            >开始</el-button>
            <el-button
              v-if="row.status === 'DONE' && userStore.hasRole(['admin', 'college_admin'])"
              type="info" link size="small" @click="onConfirm(row)"
            >确认</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无盘点任务" /></template>
      </el-table>
      <el-pagination
        class="pagination"
        v-model:current-page="query.page_num"
        v-model:page-size="query.page_size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="onSearch"
        @current-change="onSearch"
      />
    </el-card>

    <!-- 创建任务弹窗 -->
    <el-dialog v-model="dialogVisible" title="创建盘点任务" width="560px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" size="default">
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="form.task_name" placeholder="如：2026年春季学期资产盘点" />
        </el-form-item>
        <el-form-item label="盘点范围" prop="scope_type">
          <el-radio-group v-model="form.scope_type">
            <el-radio v-if="userStore.hasRole('admin')" value="ALL">全校</el-radio>
            <el-radio value="DEPT">按学院</el-radio>
            <!-- <el-radio value="ASSET">按具体资产</el-radio> -->
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.scope_type === 'DEPT'" label="选择学院" prop="scope_dept_ids">
          <el-select v-model="form.scope_dept_ids" multiple placeholder="请选择" style="width:100%">
            <el-option v-for="d in flatDeptList" :key="d.dept_id" :label="d.dept_name" :value="d.dept_id" />
          </el-select>
        </el-form-item>
        <!-- <el-form-item v-if="form.scope_type === 'ASSET'" label="选择资产" prop="scope_asset_ids">
          <el-select
            v-model="form.scope_asset_ids" multiple filterable remote
            :remote-method="searchAssets" :loading="assetSearching"
            placeholder="输入关键词搜索资产" style="width:100%"
          >
            <el-option
              v-for="a in assetOptions"
              :key="a.asset_id"
              :label="`${a.asset_code} · ${a.asset_name}${a.location ? '（' + a.location + '）' : ''}`"
              :value="a.asset_id"
            />
          </el-select>
        </el-form-item> -->
        <el-form-item label="开始时间" prop="start_time">
          <el-date-picker v-model="form.start_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="结束时间" prop="end_time">
          <el-date-picker v-model="form.end_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="盘点人员">
          <el-select v-model="form.checker_ids" multiple placeholder="可留空，全员可参与" filterable style="width:100%">
            <el-option v-for="u in userList" :key="u.user_id" :label="`${u.nickname} (${u.username})`" :value="u.user_id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Collection, Search, Refresh, Plus } from '@element-plus/icons-vue'
import {
  listCheckTasksApi, createCheckTaskApi, startCheckTaskApi, confirmCheckApi,
} from '@/api/check'
import { getDeptTreeApi, listUsersApi } from '@/api/user'
import { listAssetsApi } from '@/api/asset'
import { useUserStore } from '@/store/user'
import { useTableSort } from '@/composables/useTableSort'
import { formatDate } from '@/utils/format'

const userStore = useUserStore()
const { handleSortChange, applySort } = useTableSort()

const CHECK_STATUS_NAME: Record<string, string> = {
  PENDING: '待开始',
  IN_PROGRESS: '进行中',
  CONFIRMED: '已完成',
}
function statusTagType(s: string) {
  if (s === 'PENDING') return 'warning'
  if (s === 'IN_PROGRESS') return 'primary'
  if (s === 'CONFIRMED') return 'success'
  return 'info'
}

const loading = ref(false)
const submitting = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const userList = ref<any[]>([])
const flatDeptList = ref<any[]>([])

const query = reactive({
  keyword: '',
  status: '',
  page_num: 1,
  page_size: 10,
})

const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const assetOptions = ref<any[]>([])
const assetSearching = ref(false)
const form = reactive<any>({
  task_name: '',
  scope_type: 'DEPT',
  scope_dept_ids: [],
  scope_asset_ids: [],
  start_time: '',
  end_time: '',
  checker_ids: [],
})
const rules = {
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  scope_type: [{ required: true, message: '请选择盘点范围', trigger: 'change' }],
  scope_dept_ids: [{ required: true, type: 'array', min: 1, message: '请至少选择一个学院', trigger: 'change' }],
  scope_asset_ids: [{ required: true, type: 'array', min: 1, message: '请至少选择一个资产', trigger: 'change' }],
  start_time: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  end_time: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
}

/** 资产远程搜索（防抖） */
let assetSearchTimer: any = null
async function searchAssets(keyword: string) {
  clearTimeout(assetSearchTimer)
  assetSearchTimer = setTimeout(async () => {
    assetSearching.value = true
    try {
      const res: any = await listAssetsApi({ keyword: keyword || '', page_num: 1, page_size: 30 })
      assetOptions.value = res?.data?.list || []
    } finally { assetSearching.value = false }
  }, 250)
}

const kpi = computed(() => ({
  total: list.value.length,
  pending: list.value.filter((t) => t.status === 'PENDING').length,
  ongoing: list.value.filter((t) => t.status === 'IN_PROGRESS').length,
  done: list.value.filter((t) => t.status === 'CONFIRMED').length,
}))

const displayList = computed(() => applySort(list.value))

async function fetchList() {
  loading.value = true
  try {
    const res: any = await listCheckTasksApi({
      status: query.status,
      page_num: query.page_num,
      page_size: query.page_size,
    })
    let data = res?.data?.list || []
    if (query.keyword) {
      const kw = query.keyword.toLowerCase()
      data = data.filter((t: any) => (t.task_name || '').toLowerCase().includes(kw))
    }
    list.value = data
    total.value = res?.data?.total || 0
  } finally { loading.value = false }
}

function onSearch() { query.page_num = 1; fetchList() }
function onReset() { query.keyword = ''; query.status = ''; onSearch() }

function openCreate() {
  form.task_name = ''
  form.scope_type = 'DEPT'
  form.scope_dept_ids = []
  form.scope_asset_ids = []
  assetOptions.value = []
  form.start_time = ''
  form.end_time = ''
  form.checker_ids = []
  dialogVisible.value = true
}

async function onSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await createCheckTaskApi({ ...form })
    ElMessage.success('盘点任务已创建')
    dialogVisible.value = false
    fetchList()
  } finally { submitting.value = false }
}

async function onStart(row: any) {
  await ElMessageBox.confirm(`确定开始「${row.task_name}」盘点任务？`, '提示', { type: 'warning' })
  await startCheckTaskApi(row.task_id)
  ElMessage.success('任务已开始')
  fetchList()
}

async function onConfirm(row: any) {
  await ElMessageBox.confirm('确认盘点结果？', '提示', { type: 'warning' })
  await confirmCheckApi(row.task_id)
  ElMessage.success('已确认')
  fetchList()
}

async function loadAux() {
  const [dt, ur] = await Promise.all([getDeptTreeApi(), listUsersApi({ page_num: 1, page_size: 200 })])
  // 扁平化部门树
  const flat: any[] = []
  const walk = (nodes: any[]) => {
    for (const n of nodes || []) {
      flat.push({ dept_id: n.dept_id, dept_name: n.dept_name })
      if (n.children?.length) walk(n.children)
    }
  }
  walk((dt as any)?.data || [])
  flatDeptList.value = flat
  userList.value = (ur as any)?.data?.list || []
}

onMounted(async () => {
  await loadAux()
  await fetchList()
})
</script>

<style scoped>
.kpi-row { margin-bottom: 12px; }
.kpi { text-align: center; padding: 4px; }
.kpi-num { font-size: 22px; font-weight: 700; color: #303133; }
.kpi-label { font-size: 12px; color: #909399; }
.toolbar { display: flex; align-items: center; justify-content: space-between; }
.pagination { margin-top: 14px; justify-content: flex-end; display: flex; }
</style>
