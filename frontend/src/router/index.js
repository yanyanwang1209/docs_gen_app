import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/doc-generation',
  },
  {
    path: '/doc-generation',
    name: 'DocGeneration',
    component: () => import('../views/DocGeneration.vue'),
  },
  {
    path: '/md2word',
    name: 'Md2Word',
    component: () => import('../views/Md2Word.vue'),
  },
  {
    path: '/file-management',
    name: 'FileManagement',
    component: () => import('../views/FileManagement.vue'),
  },
  {
    path: '/llm-config',
    name: 'LlmConfig',
    component: () => import('../views/LlmConfig.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router