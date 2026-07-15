import request from './request'

export const listAssetsApi = (params: any) => request.get('/asset/list', { params })
export const getAssetDetailApi = (id: number) => request.get(`/asset/${id}`)
export const createAssetApi = (data: any) => request.post('/asset', data)
export const updateAssetApi = (data: any) => request.put('/asset', data)
export const deleteAssetApi = (id: number) => request.delete(`/asset/${id}`)
export const importAssetsApi = (form: FormData) =>
  request.post('/asset/import', form, { headers: { 'Content-Type': 'multipart/form-data' } })
export const exportAssetsApi = (params: any) =>
  request.get('/asset/export', { params, responseType: 'blob' })

export const listCategoriesApi = () => request.get('/asset/category/list')
export const listAssetStatusApi = () => request.get('/asset/status/list')
