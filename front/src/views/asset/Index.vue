<template>
  <div class="page-container">
    <div class="page-title">
      <el-icon><Box /></el-icon> 资产管理
    </div>

    <!-- 多条件过滤 -->
    <el-card class="search-card" shadow="never">
      <el-form :inline="true" :model="query" size="default" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="query.keyword"
            placeholder="名称 / 编号 / 规格"
            clearable
            style="width: 200px"
            @keyup.enter="onSearch"
            @clear="onSearch"
          />
        </el-form-item>
        <el-form-item label="分类">
          <el-cascader
            v-model="categoryVal"
            :options="categoryList"
            :props="catProps"
            placeholder="全部"
            clearable
            style="width: 220px"
            @change="onCatChange"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 130px" @change="onSearch" @clear="onSearch">
            <el-option
              v-for="s in statusList"
              :key="s.status_id"
              :label="s.status_name"
              :value="s.status_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-tree-select
            v-model="query.dept_id"
            :data="deptTree"
            :props="treeProps"
            placeholder="全部"
            clearable
            check-strictly
            style="width: 180px"
            @change="onSearch"
            @clear="onSearch"
          />
        </el-form-item>
        <el-form-item label="地点">
          <el-input v-model="query.location" placeholder="存放地点" clearable style="width: 160px" @keyup.enter="onSearch" @clear="onSearch" />
        </el-form-item>
        <el-form-item label="购置日期">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            start-placeholder="开始"
            end-placeholder="结束"
            value-format="YYYY-MM-DD"
            style="width: 240px"
            @change="onDateChange"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="onSearch">查询</el-button>
          <el-button :icon="Refresh" @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="mb-12">
      <div class="toolbar">
        <span class="text-muted">共 {{ total }} 条 · 选中 {{ selected.length }} 条</span>
        <div v-if="canEdit">
          <el-button type="primary" :icon="Plus" @click="openDialog()">新增资产</el-button>
          <el-button type="success" :icon="Download" :disabled="selected.length === 0" @click="onExport">导出选中</el-button>
        </div>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table
        v-loading="loading"
        :data="displayList"
        stripe
        border
        size="default"
        :header-cell-style="{ background: '#f5f7fa' }"
        @selection-change="(rows: any[]) => (selected = rows)"
        @sort-change="handleSortChange"
      >
        <el-table-column type="selection" width="42" />
        <el-table-column prop="asset_code" label="资产编号" width="140" sortable="custom" />
        <el-table-column prop="asset_name" label="资产名称" min-width="160" show-overflow-tooltip sortable="custom" />
        <el-table-column prop="spec" label="规格型号" width="140" show-overflow-tooltip sortable="custom" />
        <el-table-column prop="category_name" label="分类" width="110" show-overflow-tooltip sortable="custom" />
        <el-table-column prop="book_value" label="账面价值" width="120" sortable="custom">
          <template #default="{ row }">¥{{ formatMoney(row.book_value) }}</template>
        </el-table-column>
        <el-table-column prop="dept_name" label="归属学院" min-width="160" show-overflow-tooltip sortable="custom" />
        <el-table-column prop="location" label="存放地点" width="140" show-overflow-tooltip sortable="custom" />
        <el-table-column prop="user_name" label="使用人" width="100" show-overflow-tooltip sortable="custom" />
        <el-table-column prop="status" label="状态" width="100" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="ASSET_STATUS_TYPE[row.status] || 'info'" size="small">
              {{ ASSET_STATUS_NAME[row.status] || row.status_name || '未知' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="purchase_date" label="购置日期" width="110" sortable="custom" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="$router.push(`/assets/detail/${row.asset_id}`)">
              详情
            </el-button>
            <template v-if="canEdit">
              <el-button type="warning" link size="small" @click="openDialog(row)">编辑</el-button>
              <el-button type="danger" link size="small" @click="onDelete(row)">删除</el-button>
            </template>
          </template>
        </el-table-column>

        <template #empty><el-empty description="暂无数据" /></template>
      </el-table>

      <el-pagination
        class="pagination"
        v-model:current-page="query.page_num"
        v-model:page-size="query.page_size"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="onSearch"
        @current-change="onSearch"
      />
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="form.asset_id ? '编辑资产' : '新增资产'"
      width="640px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" size="default">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="资产编号" prop="asset_code">
              <el-input v-model="form.asset_code" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="资产名称" prop="asset_name">
              <el-input v-model="form.asset_name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类" prop="category_id">
              <el-cascader
                v-model="form.category_id_path"
                :options="categoryList"
                :props="catProps"
                style="width: 100%"
                @change="(v: any) => (form.category_id = Array.isArray(v) ? (v.length ? v[v.length - 1] : 0) : (v ?? 0))"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="规格型号">
              <el-input v-model="form.spec" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="部门" prop="dept_id">
              <el-tree-select
                v-model="form.dept_id"
                :data="deptTree"
                :props="treeProps"
                check-strictly
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="存放地点">
              <el-input v-model="form.location" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="账面价值">
              <el-input-number v-model="form.book_value" :min="0" :precision="2" :step="100" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="购置日期" prop="purchase_date">
              <el-date-picker
                v-model="form.purchase_date"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="使用人">
              <el-input v-model="form.user_name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width: 100%">
                <el-option
                  v-for="s in statusList"
                  :key="s.status_id"
                  :label="s.status_name"
                  :value="s.status_id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Box, Search, Refresh, Plus, Download } from '@element-plus/icons-vue'
import {
  listAssetsApi, createAssetApi, updateAssetApi, deleteAssetApi,
  listCategoriesApi, listAssetStatusApi,
} from '@/api/asset'
import { getDeptTreeApi } from '@/api/user'
import { formatMoney, formatDate } from '@/utils/format'
import { useTableSort } from '@/composables/useTableSort'
import { useUserStore } from '@/store/user'
import { ASSET_STATUS_NAME, ASSET_STATUS_TYPE } from '@/types'

const userStore = useUserStore()
const canEdit = computed(() => userStore.hasRole(['admin', 'college_admin']))

const loading = ref(false)
const { handleSortChange, applySort } = useTableSort()
const submitting = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const selected = ref<any[]>([])

const categoryList = ref<any[]>([])
const statusList = ref<any[]>([])
const deptTree = ref<any[]>([])

const treeProps = { value: 'dept_id', label: 'dept_name', children: 'children' }
const catProps = { value: 'category_id', label: 'category_name', children: 'children', checkStrictly: true, emitPath: false }

const query = reactive({
  keyword: '',
  category_id: 0,
  status: 0,
  dept_id: 0,
  location: '',
  page_num: 1,
  page_size: 10,
})
const categoryVal = ref<any>(0)
const dateRange = ref<[string, string] | null>(null)

const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const form = reactive<any>({
  asset_id: 0,
  asset_code: '',
  asset_name: '',
  category_id: 0,
  category_id_path: 0,
  spec: '',
  dept_id: 0,
  location: '',
  book_value: 0,
  purchase_date: '',
  user_name: '',
  status: 1,
  remark: '',
})

const rules = {
  asset_code: [{ required: true, message: '请输入资产编号', trigger: 'blur' }],
  asset_name: [{ required: true, message: '请输入资产名称', trigger: 'blur' }],
  category_id: [{ required: true, message: '请选择分类', trigger: 'change' }],
  dept_id: [{ required: true, message: '请选择部门', trigger: 'change' }],
  // 新增购置日期必填校验
  purchase_date: [{ required: true, message: '请选择购置日期', trigger: 'change' }],
}

function onCatChange(v: number | null | undefined) {
  query.category_id = Number(v) || 0
  onSearch()
}
function onDateChange(v: any) {
  // 占位：后端未提供日期范围过滤，client side 过滤
  onSearch()
}

async function fetchList() {
  loading.value = true
  try {
    const res: any = await listAssetsApi({
      keyword: query.keyword,
      category_id: query.category_id,
      status: query.status,
      dept_id: query.dept_id,
      page_num: query.page_num,
      page_size: query.page_size,
    })
    let data = res?.data?.list || []
    if (query.location) {
      data = data.filter((a: any) => a.location && a.location.includes(query.location))
    }
    if (dateRange.value && dateRange.value.length === 2) {
      const [s, e] = dateRange.value
      data = data.filter((a: any) => a.purchase_date >= s && a.purchase_date <= e)
    }
    list.value = data
    total.value = res?.data?.total || 0
  } finally {
    loading.value = false
  }
}

const displayList = computed(() => applySort(list.value))

function onSearch() {
  query.page_num = 1
  fetchList()
}
function onReset() {
  query.keyword = ''
  query.category_id = 0
  categoryVal.value = 0
  query.status = 0
  query.dept_id = 0
  query.location = ''
  dateRange.value = null
  onSearch()
}

function openDialog(row?: any) {
  form.asset_id = row?.asset_id || 0
  form.asset_code = row?.asset_code || ''
  form.asset_name = row?.asset_name || ''
  form.category_id = row?.category_id || 0
  form.category_id_path = row?.category_id || 0
  form.spec = row?.spec || ''
  form.dept_id = row?.dept_id || 0
  form.location = row?.location || ''
  form.book_value = row?.book_value || 0
  form.purchase_date = row?.purchase_date || ''
  form.user_name = row?.user_name || ''
  form.status = row?.status ?? 1
  form.remark = row?.remark || ''
  dialogVisible.value = true
}

async function onSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (form.asset_id) {
      await updateAssetApi({ ...form })
      ElMessage.success('更新成功')
    } else {
      await createAssetApi({ ...form })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchList()
  } finally {
    submitting.value = false
  }
}

async function onDelete(row: any) {
  await ElMessageBox.confirm(`确定删除资产「${row.asset_name}」？`, '提示', { type: 'warning' })
  await deleteAssetApi(row.asset_id)
  ElMessage.success('已删除')
  fetchList()
}

function onExport() {
  ElMessage.info(`已选择 ${selected.value.length} 条（导出功能需后端配合）`)
}

async function loadAux() {
  const [c, s, d] = await Promise.all([listCategoriesApi(), listAssetStatusApi(), getDeptTreeApi()])
  categoryList.value = (c as any)?.data || []
  statusList.value = (s as any)?.data || []
  deptTree.value = (d as any)?.data || []
}

watch(categoryList, (v) => {
  // 首次加载后，将 status 1（IDLE）作为默认
  if (v.length && !query.status) query.status = 1
})

onMounted(async () => {
  await loadAux()
  await fetchList()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pagination {
  margin-top: 14px;
  justify-content: flex-end;
  display: flex;
}
</style>
