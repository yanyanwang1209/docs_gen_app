import api from './index'

export const fileApi = {
  list(params) {
    return api.get('/files', { params })
  },
  upload(formData) {
    return api.post('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  get(id) {
    return api.get(`/files/${id}`)
  },
  update(id, data) {
    return api.put(`/files/${id}`, data)
  },
  delete(id) {
    return api.delete(`/files/${id}`)
  },
  batchDelete(fileIds) {
    return api.post('/files/batch-delete', fileIds)
  },
  download(id) {
    return api.get(`/files/${id}/download`, { responseType: 'blob' })
  },
  getContent(id) {
    return api.get(`/files/${id}/content`)
  },
}