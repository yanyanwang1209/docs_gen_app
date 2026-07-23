import api from './index'

export const adminApi = {
  getUsers(search) {
    return api.get('/admin/users', { params: search ? { search } : {} })
  },
  deleteUser(id) {
    return api.delete(`/admin/users/${id}`)
  },
  batchDeleteUsers(ids) {
    return api.post('/admin/users/batch-delete', { user_ids: ids })
  },
  resetPassword(id, newPassword) {
    return api.post(`/admin/users/${id}/reset-password`, newPassword ? { new_password: newPassword } : {})
  },
}