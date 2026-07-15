import request from './request'

// 盘点任务
export const listCheckTasksApi = (params: any) => request.get('/check/task/list', { params })
export const createCheckTaskApi = (data: any) => request.post('/check/task', data)
export const startCheckTaskApi = (id: number) => request.put(`/check/task/${id}/start`)

// 盘点明细（协同录入）
export const getSheetDataApi = (taskId: number) => request.get(`/check/sheet/${taskId}`)
export const saveSheetDataApi = (data: { task_id: number; details: any[] }) =>
  request.post('/check/sheet/save', data)

// 差异报告
export const analyzeDiffApi = (taskId: number) => request.post('/check/diff/analyze', { task_id: taskId })
export const getDiffReportApi = (taskId: number) => request.get(`/check/diff/${taskId}`)
export const confirmCheckApi = (taskId: number) => request.put('/check/confirm', { task_id: taskId })
