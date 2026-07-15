<template>
  <div class="error-page">
    <el-result icon="warning" title="403" :sub-title="subTitle">
      <template #extra>
        <el-button type="primary" @click="goHome">返回首页</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()

const subTitle = computed(() => {
  const r = userStore.roles
  if (r.length === 0) return '您还未登录或会话已过期'
  if (r.includes('user') || r.includes('repairer')) {
    return '抱歉，您当前角色（' + roleLabel.value + '）没有访问此页面的权限。如需使用相关功能，请联系校级管理员。'
  }
  if (r.includes('college_admin')) {
    return '抱歉，您当前角色（院级管理员）没有访问此页面的权限。部分功能仅校级管理员可用。'
  }
  return '抱歉，您没有访问此页面的权限'
})

const roleLabel = computed(() => {
  const r = userStore.roles
  if (r.includes('admin')) return '校级管理员'
  if (r.includes('college_admin')) return '院级管理员'
  if (r.includes('repairer')) return '维修工'
  return '普通用户'
})

function goHome() {
  router.push('/dashboard')
}
</script>

<style scoped>
.error-page { height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }
</style>
