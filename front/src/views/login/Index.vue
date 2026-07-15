<template>
  <div class="login-bg">
    <div class="login-card">
      <div class="brand">
        <el-icon class="brand-icon"><Box /></el-icon>
        <div>
          <h1 class="brand-title">FAMS-NEPU</h1>
          <p class="brand-sub">固定资产协同管理系统 · v2</p>
        </div>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="onSubmit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" clearable />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" style="width:100%" @click="onSubmit">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <p class="hint">默认账号： admin / admin123（校管） · jzxy / 123456（院管）</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await userStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch {
    /* 错误提示由拦截器统一处理 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-bg {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
}
.login-card {
  width: 400px;
  padding: 36px 32px 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}
.brand-icon {
  font-size: 42px;
  color: #409eff;
}
.brand-title {
  font-size: 22px;
  margin: 0;
  color: #303133;
}
.brand-sub {
  font-size: 12px;
  color: #909399;
  margin: 4px 0 0;
}
.hint {
  font-size: 12px;
  color: #909399;
  text-align: center;
  margin-top: 8px;
  line-height: 1.5;
}
</style>
