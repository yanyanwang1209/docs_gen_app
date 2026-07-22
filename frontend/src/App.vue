<template>
  <div id="app">
    <el-container style="min-height: 100vh">
      <!-- 侧边栏 -->
      <el-aside width="220px" style="background: #304156; display: flex; flex-direction: column">
        <div style="height: 60px; display: flex; align-items: center; justify-content: center; border-bottom: 1px solid rgba(255,255,255,0.1)">
          <h1 style="color: white; margin: 0; font-size: 17px; white-space: nowrap">
            <el-icon style="margin-right: 6px"><Document /></el-icon>
            验收文档生成器
          </h1>
        </div>
        <el-menu
          :default-active="currentRoute"
          :router="true"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409eff"
          style="border-right: none; flex: 1"
        >
          <el-menu-item index="/doc-generation">
            <el-icon><Edit /></el-icon>
            <span>文档生成</span>
          </el-menu-item>
          <el-menu-item index="/md2word">
            <el-icon><Switch /></el-icon>
            <span>MD 转 Word</span>
          </el-menu-item>
          <el-menu-item index="/file-management">
            <el-icon><FolderOpened /></el-icon>
            <span>文件管理</span>
          </el-menu-item>
          <el-menu-item index="/llm-config">
            <el-icon><Setting /></el-icon>
            <span>LLM 配置</span>
          </el-menu-item>
          <el-menu-item v-if="isAdmin" index="/admin">
            <el-icon><UserFilled /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
        </el-menu>
        <!-- 底部用户信息 -->
        <div style="padding: 12px 16px; border-top: 1px solid rgba(255,255,255,0.1); color: #bfcbd9; font-size: 13px">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
            <el-icon><User /></el-icon>
            <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ username }}</span>
          </div>
          <div style="display: flex; gap: 4px">
            <el-button size="small" text style="color: #bfcbd9" @click="showChangePasswordDialog = true">修改密码</el-button>
            <el-button size="small" text style="color: #bfcbd9" @click="logout">退出登录</el-button>
          </div>
        </div>
      </el-aside>

      <!-- 主内容区 -->
      <el-container>
        <el-main style="background: #f0f2f5; padding: 24px; min-height: 100vh">
          <router-view />
        </el-main>
      </el-container>
    </el-container>

    <!-- 修改密码弹窗 -->
    <el-dialog v-model="showChangePasswordDialog" title="修改密码" width="400px" :close-on-click-modal="false">
      <el-form :model="passwordForm" label-width="80px" size="default">
        <el-form-item label="原密码">
          <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="输入原密码" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showChangePasswordDialog = false">取消</el-button>
        <el-button type="primary" @click="changePassword" :loading="changingPassword">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, watch, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from './api/auth'

const route = useRoute()
const router = useRouter()
const currentRoute = computed(() => route.hash ? route.hash.slice(1) : route.path)

const username = ref(getStoredUsername())
const isAdmin = ref(getStoredIsAdmin())

const showChangePasswordDialog = ref(false)
const changingPassword = ref(false)
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

function getStoredUsername() {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  return user.username || '未登录'
}

function getStoredIsAdmin() {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  return user.is_admin || false
}

// 路由变化时刷新用户名（登录后跳转会触发）
watch(() => route.fullPath, () => {
  username.value = getStoredUsername()
  isAdmin.value = getStoredIsAdmin()
})

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}

async function changePassword() {
  if (!passwordForm.old_password) {
    ElMessage.warning('请输入原密码')
    return
  }
  if (!passwordForm.new_password || passwordForm.new_password.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  changingPassword.value = true
  try {
    await authApi.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    ElMessage.success('密码修改成功')
    showChangePasswordDialog.value = false
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  } finally {
    changingPassword.value = false
  }
}
</script>

<style>
body {
  margin: 0;
  font-family: 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
}
#app {
  height: 100vh;
}
</style>