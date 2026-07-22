import api from './index'

export const authApi = {
  login(data) {
    return api.post('/auth/login', data)
  },
  register(data) {
    return api.post('/auth/register', data)
  },
  me() {
    return api.get('/auth/me')
  },
  check() {
    return api.get('/auth/check')
  },
  changePassword(data) {
    return api.post('/auth/change-password', data)
  },
}