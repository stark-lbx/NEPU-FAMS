import request from './request'

// 申请
export const listMyAppliesApi = (params: any) => request.get('/apply/my', { params })
export const listPendingAppliesApi = (params: any) => request.get('/apply/pending', { params })
export const listApprovedAppliesApi = (params: any) => request.get('/apply/approved', { params })
export const getApplyDetailApi = (id: number) => request.get(`/apply/${id}`)
export const submitBorrowApi = (data: any) => request.post('/apply/borrow', data)
export const submitReturnApi = (data: any) => request.post('/apply/return', data)
export const submitScrapApi = (data: any) => request.post('/apply/scrap', data)
export const approveApplyApi = (data: {
  apply_id: number
  action: 'APPROVE' | 'REJECT'
  opinion?: string
}) => request.put('/apply/approve', data)
export const cancelApplyApi = (id: number, opinion = '') =>
  request.put(`/apply/cancel/${id}`, { opinion })

// 报修
export const listRepairOrdersApi = (params: any) => request.get('/repair/list', { params })
export const getRepairDetailApi = (id: number) => request.get(`/repair/${id}`)
export const submitRepairApi = (data: any) => request.post('/repair/submit', data)
export const collegeApproveApi = (data: { order_id: number; is_pass: boolean; opinion?: string }) =>
  request.put('/repair/college-approve', data)
export const schoolApproveApi = (data: { order_id: number; is_pass: boolean; opinion?: string }) =>
  request.put('/repair/school-approve', data)
export const dispatchOrderApi = (data: { order_id: number; repairer_id: number; deadline?: string; remark?: string }) =>
  request.put('/repair/dispatch', data)
export const acceptOrderApi = (data: { order_id: number }) =>
  request.put('/repair/accept', data)
export const updateRepairInfoApi = (data: { order_id: number; repair_detail?: string; repair_cost?: number; parts_detail?: string; invoice_files?: string }) =>
  request.put('/repair/update-repair', data)
export const finishRepairApi = (data: { order_id: number }) =>
  request.put('/repair/finish', data)
export const resubmitRepairApi = (order_id: number) =>
  request.put(`/repair/resubmit/${order_id}`)
export const acceptanceApi = (data: { order_id: number; is_pass: boolean; opinion?: string }) =>
  request.put('/repair/acceptance', data)
export const listRepairersApi = () => request.get('/user/repairers')
