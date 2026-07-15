<template>
  <div class="page-container">
    <div class="page-title">
      <el-icon><UserFilled /></el-icon> 个人信息
    </div>

    <el-row :gutter="12">
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="profile-card">
          <el-avatar :size="80" style="background:#409eff; font-size:32px; margin: 0 auto;">
            {{ avatarChar }}
          </el-avatar>
          <h2 class="profile-name">{{ userStore.userInfo?.nickname || '用户' }}</h2>
          <p class="profile-username">@{{ userStore.userInfo?.username }}</p>
          <div class="profile-roles">
            <el-tag
              v-for="r in (userStore.userInfo?.roles || [])"
              :key="r.role_id"
              :type="roleTagType(r.role_key)"
              size="small"
            >{{ r.role_name }}</el-tag>
          </div>
          <el-descriptions :column="1" border class="mt-12">
            <el-descriptions-item label="所属部门">{{ userStore.userInfo?.dept_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ userStore.userInfo?.phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ userStore.userInfo?.email || '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDate(userStore.userInfo?.create_time) }}</el-descriptions-item>
            <el-descriptions-item label="账号状态">
              <el-tag :type="userStore.userInfo?.status === 1 ? 'success' : 'danger'" size="small">
                {{ userStore.userInfo?.status === 1 ? '正常' : '停用' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-hd"><span>修改密码</span></div>
          </template>
          <el-form ref="pwdRef" :model="pwdForm" :rules="pwdRules" label-width="100px" size="default" style="max-width:480px">
            <el-form-item label="原密码" prop="old_password">
              <el-input v-model="pwdForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input v-model="pwdForm.new_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm">
              <el-input v-model="pwdForm.confirm" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="pwdLoading" @click="onChangePwd">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never" class="mt-12">
          <template #header>
            <div class="card-hd"><span>操作</span></div>
          </template>
          <el-space wrap>
            <el-button :icon="RefreshRight" @click="refreshInfo">刷新资料</el-button>
            <el-button type="danger" :icon="SwitchButton" @click="userStore.logout()">退出登录</el-button>
          </el-space>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import { UserFilled, SwitchButton, RefreshRight } from '@element-plus/icons-vue'
import { changePasswordApi } from '@/api/user'
import { useUserStore } from '@/store/user'
import { formatDate } from '@/utils/format'

const userStore = useUserStore()
const pwdRef = ref<FormInstance>()
const pwdLoading = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '', confirm: '' })

const pwdRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 位', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_r: any, v: any, cb: any) =>
        v === pwdForm.new_password ? cb() : cb(new Error('两次密码不一致')),
      trigger: 'blur',
    },
  ],
}

const avatarChar = () => (userStore.userInfo?.nickname || userStore.userInfo?.username || 'U').charAt(0).toUpperCase()

function roleTagType(key: string) {
  if (key === 'admin') return 'danger'
  if (key === 'college_admin') return 'warning'
  if (key === 'repairer') return 'success'
  return 'info'
}

async function onChangePwd() {
  const valid = await pwdRef.value?.validate().catch(() => false)
  if (!valid) return
  pwdLoading.value = true
  try {
    await changePasswordApi({ old_password: pwdForm.old_password, new_password: pwdForm.new_password })
    ElMessage.success('密码修改成功，请重新登录')
    userStore.logout()
  } finally {
    pwdLoading.value = false
  }
}

async function refreshInfo() {
  await userStore.fetchUserInfo()
  ElMessage.success('已刷新')
}

onMounted(async () => {
  if (!userStore.userInfo) await userStore.fetchUserInfo().catch(() => {})
})
</script>

<style scoped>
.profile-card { text-align: center; }
.profile-name { font-size: 20px; margin: 12px 0 4px; }
.profile-username { color: #909399; font-size: 12px; margin: 0 0 12px; }
.profile-roles { display: flex; gap: 4px; flex-wrap: wrap; justify-content: center; margin-bottom: 8px; }
.card-hd { font-weight: 600; }
</style>
