<template>
  <div class="admin-page">
    <h2 style="margin: 0 0 20px 0; font-size: 20px; color: #303133">用户管理</h2>

    <el-table :data="users" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="username" label="用户名" min-width="150" />
      <el-table-column prop="is_admin" label="角色" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="row.is_admin ? 'danger' : 'info'">
            {{ row.is_admin ? '管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="has_llm_config" label="LLM 配置" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="row.has_llm_config ? 'success' : 'warning'">
            {{ row.has_llm_config ? '已配置' : '未配置' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="warning" @click="resetPassword(row)" :disabled="row.is_admin">
            重置密码
          </el-button>
          <el-button size="small" type="danger" @click="deleteUser(row)" :disabled="row.is_admin">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '../api/admin'

const users = ref([])
const loading = ref(false)

onMounted(() => loadUsers())

async function loadUsers() {
  loading.value = true
  try {
    const res = await adminApi.getUsers()
    users.value = res.data.items || []
  } catch (e) {
    ElMessage.error('加载用户列表失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

async function resetPassword(row) {
  try {
    const { value: newPassword } = await ElMessageBox.prompt(
      `请输入用户「${row.username}」的新密码（至少6位）：`,
      '重置密码',
      {
        confirmButtonText: '确定重置',
        cancelButtonText: '取消',
        inputType: 'text',
        inputPlaceholder: '输入新密码，留空则随机生成',
        inputValidator: (val) => {
          if (val && val.length < 6) return '密码至少 6 位'
          return true
        },
      }
    )
    const res = await adminApi.resetPassword(row.id, newPassword || undefined)
    ElMessageBox.alert(
      `用户「${row.username}」的密码已重置。<br>新密码为：<br><strong style="font-size: 18px; color: #409eff">${res.data.new_password}</strong>`,
      '密码已重置',
      { dangerouslyUseHTMLString: true, confirmButtonText: '我知道了' }
    )
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error('重置失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

async function deleteUser(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户「${row.username}」吗？此操作将同时删除该用户的所有模板、文件和生成任务，不可恢复。`,
      '删除用户',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
    await adminApi.deleteUser(row.id)
    ElMessage.success(`用户「${row.username}」已删除`)
    await loadUsers()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const str = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z'
  return new Date(str).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}
</script>