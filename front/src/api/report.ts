import request from './request'

export const getDashboardApi = () => request.get('/report/dashboard')
export const getAssetReportApi = () => request.get('/report/asset')
export const getRepairReportApi = () => request.get('/report/repair')
export const getInventoryReportApi = () => request.get('/report/inventory')
