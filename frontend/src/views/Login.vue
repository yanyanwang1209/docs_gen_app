<template>
  <div class="login-page">
    <div class="login-card">
      <h2 class="login-title">
        <el-icon style="margin-right: 8px"><Document /></el-icon>
        验收文档生成器
      </h2>
      <p class="login-subtitle">{{ isRegister ? '注册新账号' : '登录到您的账号' }}</p>

      <el-form :model="form" ref="formRef" @keyup.enter="submit">
        <el-form-item v-if="isRegister">
          <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item v-else>
          <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="User" />
        </el-form-item>

        <el-form-item>
          <el-input v-model="form.password" type="password" show-password
            placeholder="密码" size="large" :prefix-icon="Lock" />
        </el-form-item>

        <el-form-item v-if="isRegister">
          <el-input v-model="form.confirmPassword" type="password" show-password
            placeholder="确认密码" size="large" :prefix-icon="Lock" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" size="large" style="width: 100%" @click="submit" :loading="loading">
            {{ isRegister ? '注册' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div style="text-align: center; color: #909399; font-size: 13px">
        <span v-if="!isRegister">
          还没有账号？<a href="javascript:void(0)" @click="isRegister = true" style="color: #409eff">立即注册</a>
        </span>
        <span v-else>
          已有账号？<a href="javascript:void(0)" @click="isRegister = false" style="color: #409eff">返回登录</a>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { authApi } from '../api/auth'

const router = useRouter()
const isRegister = ref(false)
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})

async function submit() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  if (isRegister.value && form.password !== form.confirmPassword) {
    ElMessage.warning('两次密码不一致')
    return
  }
  if (isRegister.value && form.password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }

  loading.value = true
  try {
    const api = isRegister.value ? authApi.register : authApi.login
    const res = await api({ username: form.username.trim(), password: form.password })
    const data = res.data
    localStorage.setItem('token', data.token)
    localStorage.setItem('user', JSON.stringify({
      user_id: data.user_id,
      username: data.username,
      is_admin: data.is_admin,
    }))
    ElMessage.success(isRegister.value ? '注册成功' : '登录成功')
    router.push('/doc-generation')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f0f2f5;
}
.login-card {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}
.login-title {
  margin: 0 0 4px 0;
  font-size: 22px;
  color: #303133;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
}
.login-subtitle {
  margin: 0 0 32px 0;
  text-align: center;
  color: #909399;
  font-size: 14px;
}
</style>