import api from './index'

export const generationApi = {
  start(data) {
    return api.post('/generation/start', data)
  },
  getTask(id) {
    return api.get(`/generation/${id}`)
  },
  previewTask(id) {
    return api.get(`/generation/${id}/preview`)
  },
  listTasks(params) {
    return api.get('/generation', { params })
  },
  retryChapter(taskId, chapterId, data = {}) {
    return api.post(`/generation/${taskId}/retry-chapter/${chapterId}`, data, {
      timeout: 300000, // 5 分钟，LLM 生成需要较长时间
    })
  },
  buildWord(taskId) {
    return api.post(`/generation/${taskId}/build-word`, null, {
      responseType: 'blob',
    })
  },
  deleteTask(id) {
    return api.delete(`/generation/${id}`)
  },
  getWsUrl(taskId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/api/generation/${taskId}/progress`
  },
}