import api from './index'

export const templateApi = {
  list(params) {
    return api.get('/templates', { params })
  },
  create(data) {
    return api.post('/templates', data)
  },
  get(id) {
    return api.get(`/templates/${id}`)
  },
  update(id, data) {
    return api.put(`/templates/${id}`, data)
  },
  delete(id) {
    return api.delete(`/templates/${id}`)
  },
  extractWord(formData) {
    return api.post('/templates/extract-word', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  aiAnalyze(formData) {
    return api.post('/templates/ai-analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}