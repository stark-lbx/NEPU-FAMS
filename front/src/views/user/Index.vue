<template>
  <div class="page-container">
    <div class="page-title">
      <el-icon><User /></el-icon> 用户管理
    </div>

    <!-- 多条件过滤 -->
    <el-card class="search-card" shadow="never">
      <el-form :inline="true" :model="query" size="default" @submit.prevent>
        <el-form-item label="关键词">
          <el-input
            v-model="query.keyword"
            placeholder="用户名 / 姓名 / 手机"
            clearable
            style="width: 200px"
            @keyup.enter="onSearch"
            @clear="onSearch"
          />
        </el-form-item>
        <el-form-item label="部门">
          <el-tree-select
            v-model="query.dept_id"
            :data="deptTree"
            :props="treeProps"
            placeholder="全部"
            clearable
            check-strictly
            style="width: 200px"
            @change="onSearch"
            @clear="onSearch"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select
            v-model="query.role_id"
            placeholder="全部"
            clearable
            style="width: 160px"
            @change="onSearch"
            @clear="onSearch"
          >
            <el-option v-for="r in roleList" :key="r.role_id" :label="r.role_name" :value="r.role_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px" @change="onSearch" @clear="onSearch">
            <el-option label="正常" :value="1" />
            <el-option label="停用" :value="0" />
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
          <el-button type="primary" :icon="Plus" @click="openDialog()">新增用户</el-button>
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
        size="default"
        :header-cell-style="{ background: '#f5f7fa' }"
        @sort-change="handleSortChange"
      >
        <el-table-column prop="user_id" label="ID" width="60" sortable="custom" />
        <el-table-column prop="username" label="用户名" width="110" sortable="custom" />
        <el-table-column prop="nickname" label="姓名" width="110" sortable="custom" />
        <el-table-column prop="dept_name" label="部门" min-width="160" show-overflow-tooltip sortable="custom" />
        <el-table-column prop="phone" label="手机号" width="130" sortable="custom" />
        <el-table-column prop="email" label="邮箱" width="180" show-overflow-tooltip sortable="custom" />
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <el-tag
              v-for="r in (row.roles || [])"
              :key="r.role_id"
              size="small"
              :type="roleTagType(r.role_key)"
              style="margin-right: 4px; margin-bottom: 2px"
            >
              {{ r.role_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
              {{ row.status === 1 ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="160" sortable="custom">
          <template #default="{ row }">{{ formatDate(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openDialog(row)">编辑</el-button>
            <el-button
              type="danger"
              link
              size="small"
              :disabled="row.user_id === userStore.userInfo?.user_id"
              @click="onDelete(row)"
            >删除</el-button>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无数据" />
        </template>
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
    <el-dialog v-model="dialogVisible" :title="form.user_id ? '编辑用户' : '新增用户'" width="540px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" size="default">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="!!form.user_id" />
        </el-form-item>
        <el-form-item label="姓名" prop="nickname">
          <el-input v-model="form.nickname" />
        </el-form-item>
        <el-form-item v-if="!form.user_id" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="部门" prop="dept_id">
          <el-tree-select
            v-model="form.dept_id"
            :data="deptTree"
            :props="treeProps"
            placeholder="请选择部门"
            check-strictly
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="角色" prop="role_ids">
          <el-select v-model="form.role_ids" multiple placeholder="请选择" style="width:100%">
            <el-option v-for="r in roleList" :key="r.role_id" :label="r.role_name" :value="r.role_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">正常</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
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
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { User, Search, Refresh, Plus } from '@element-plus/icons-vue'
import {
  listUsersApi, createUserApi, updateUserApi, deleteUserApi,
  listRolesApi, getDeptTreeApi,
} from '@/api/user'
import { useUserStore } from '@/store/user'
import { useTableSort } from '@/composables/useTableSort'
import { formatDate } from '@/utils/format'

const userStore = useUserStore()
const { handleSortChange, applySort } = useTableSort()

const loading = ref(false)
const submitting = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const roleList = ref<any[]>([])
const deptTree = ref<any[]>([])

const treeProps = { value: 'dept_id', label: 'dept_name', children: 'children' }

const query = reactive({
  keyword: '',
  dept_id: 0,
  role_id: 0,
  status: -1,
  page_num: 1,
  page_size: 10,
})

const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const form = reactive<any>({
  user_id: 0,
  username: '',
  nickname: '',
  password: '',
  dept_id: 0,
  role_ids: [],
  phone: '',
  email: '',
  status: 1,
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  nickname: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  dept_id: [{ required: true, message: '请选择部门', trigger: 'change' }],
  role_ids: [{ required: true, type: 'array', min: 1, message: '至少选择一个角色', trigger: 'change' }],
}

function roleTagType(key: string) {
  if (key === 'admin') return 'danger'
  if (key === 'college_admin') return 'warning'
  if (key === 'repairer') return 'success'
  return 'info'
}

async function fetchList() {
  loading.value = true
  try {
    const res: any = await listUsersApi({
      keyword: query.keyword,
      dept_id: query.dept_id,
      status: query.status,
      page_num: query.page_num,
      page_size: query.page_size,
    })
    // 客户端角色过滤（后端未支持 role_id 入参）
    let data = res?.data?.list || []
    if (query.role_id) {
      data = data.filter((u: any) => (u.roles || []).some((r: any) => r.role_id === query.role_id))
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
  query.dept_id = 0
  query.role_id = 0
  query.status = -1
  onSearch()
}

function openDialog(row?: any) {
  form.user_id = row?.user_id || 0
  form.username = row?.username || ''
  form.nickname = row?.nickname || ''
  form.password = ''
  form.dept_id = row?.dept_id || 0
  form.role_ids = (row?.roles || []).map((r: any) => r.role_id)
  form.phone = row?.phone || ''
  form.email = row?.email || ''
  form.status = row?.status ?? 1
  dialogVisible.value = true
}

async function onSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (form.user_id) {
      await updateUserApi({ ...form })
      ElMessage.success('更新成功')
    } else {
      await createUserApi({ ...form })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchList()
  } finally {
    submitting.value = false
  }
}

async function onDelete(row: any) {
  await ElMessageBox.confirm(`确定删除用户「${row.nickname || row.username}」？`, '提示', { type: 'warning' })
  await deleteUserApi(row.user_id)
  ElMessage.success('已删除')
  fetchList()
}

async function loadAux() {
  const [r, d] = await Promise.all([listRolesApi({ page_num: 1, page_size: 200 }), getDeptTreeApi()])
  roleList.value = (r as any)?.data?.list || []
  deptTree.value = (d as any)?.data || []
}

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
