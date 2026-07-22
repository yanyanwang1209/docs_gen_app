import api from './index'

export const adminApi = {
  getUsers() {
    return api.get('/admin/users')
  },
  deleteUser(id) {
    return api.delete(`/admin/users/${id}`)
  },
  resetPassword(id, newPassword) {
    return api.post(`/admin/users/${id}/reset-password`, newPassword ? { new_password: newPassword } : {})
  },
}