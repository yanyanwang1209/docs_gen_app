<template>
  <div class="llm-config">
    <h2 style="margin: 0 0 20px 0; font-size: 20px; color: #303133">LLM 配置</h2>
    <el-card shadow="never" style="max-width: 800px">
      <!-- 配置来源提示 -->
      <el-alert v-if="form.source === 'default'" title="当前使用系统默认 LLM 配置。保存后将使用您的个人配置。" type="info" :closable="false" style="margin-bottom: 16px" show-icon />
      <el-alert v-else title="当前使用您的个人 LLM 配置" type="success" :closable="false" style="margin-bottom: 16px" show-icon />

      <el-form label-width="140px" :model="form" ref="formRef">
        <el-form-item label="API 地址">
          <el-input v-model="form.base_url" placeholder="http://localhost:8000/v1" />
          <div style="color: #999; font-size: 12px">OpenAI 兼容 API 的地址</div>
        </el-form-item>

        <el-form-item label="API Key">
          <el-input v-model="form.api_key" type="password" show-password
            placeholder="输入新的 API Key（已保存的 Key 将脱敏显示）" />
          <div style="color: #999; font-size: 12px">修改后点击保存即可生效</div>
        </el-form-item>

        <el-form-item label="默认模型">
          <el-input v-model="form.model" placeholder="default-model" />
        </el-form-item>

        <el-divider content-position="left">全局写作要求</el-divider>
        <el-form-item label="写作要求">
          <el-input v-model="form.global_requirements" type="textarea" :rows="4"
            placeholder="这些要求将应用于所有文档生成任务，例如：语言风格正式专业、内容详细具体..." />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="saveConfig" :loading="saving">
            <el-icon><Check /></el-icon> 保存配置
          </el-button>
          <el-button @click="testConnection" :loading="testing">
            <el-icon><Connection /></el-icon> 测试连接
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 测试结果 -->
      <el-alert v-if="testResult" :title="testResult.message" :type="testResult.ok ? 'success' : 'error'"
        :closable="false" style="margin-top: 16px" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { llmApi } from '../api/md2word'

const form = reactive({
  base_url: '',
  api_key: '',
  model: '',
  global_requirements: '',
  source: 'default',
})

const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)

onMounted(async () => {
  try {
    const res = await llmApi.getConfig()
    Object.assign(form, res.data)
  } catch (e) {
    console.error('加载 LLM 配置失败', e)
  }
})

async function saveConfig() {
  saving.value = true
  try {
    await llmApi.updateConfig({
      base_url: form.base_url,
      api_key: form.api_key,
      model: form.model,
      global_requirements: form.global_requirements,
    })
    ElMessage.success('配置已保存')
    const res = await llmApi.getConfig()
    Object.assign(form, res.data)
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    const res = await llmApi.testConnection({
      base_url: form.base_url,
      api_key: form.api_key,
      model: form.model,
    })
    testResult.value = res.data
  } catch (e) {
    testResult.value = { ok: false, message: '连接测试失败: ' + (e.response?.data?.detail || e.message) }
  } finally {
    testing.value = false
  }
}
</script>