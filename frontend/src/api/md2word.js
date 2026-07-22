import api from './index'

export const md2wordApi = {
  convertFile(formData) {
    return api.post('/md2word/convert', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob',
    })
  },
  convertText(formData) {
    return api.post('/md2word/convert-text', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob',
    })
  },
}

export const llmApi = {
  getConfig() {
    return api.get('/llm/config')
  },
  updateConfig(data) {
    return api.put('/llm/config', data)
  },
  testConnection() {
    return api.post('/llm/test')
  },
}