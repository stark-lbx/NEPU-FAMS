import axios, { type AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'
import { getToken, removeToken } from '@/utils/auth'

const service: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

service.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

service.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data && typeof data === 'object' && 'code' in data) {
      if (data.code === 401) {
        ElMessage.error('登录已过期，请重新登录')
        removeToken()
        window.location.href = '/login'
        return Promise.reject(new Error('token expired'))
      }
      if (data.code !== 200) {
        ElMessage.error(data.message || '请求失败')
        return Promise.reject(new Error(data.message || 'fail'))
      }
      return data
    }
    return response.data
  },
  (error) => {
    ElMessage.error(error.message || '网络错误')
    return Promise.reject(error)
  }
)

export default service
