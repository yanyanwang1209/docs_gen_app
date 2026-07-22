import { createRouter, createWebHashHistory } from 'vue-router'
import { ElMessage } from 'element-plus'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    redirect: '/doc-generation',
  },
  {
    path: '/doc-generation',
    name: 'DocGeneration',
    component: () => import('../views/DocGeneration.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/md2word',
    name: 'Md2Word',
    component: () => import('../views/Md2Word.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/file-management',
    name: 'FileManagement',
    component: () => import('../views/FileManagement.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/llm-config',
    name: 'LlmConfig',
    component: () => import('../views/LlmConfig.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/Admin.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 路由守卫：未登录重定向到登录页
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    ElMessage.warning('请先登录')
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/doc-generation')
  } else if (to.meta.requiresAdmin) {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    if (!user.is_admin) {
      ElMessage.warning('仅管理员可访问此页面')
      next('/doc-generation')
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router