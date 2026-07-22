<template>
  <div class="md2word-page">
    <h2 style="margin: 0 0 24px 0; font-size: 20px; color: #303133">MD 转 Word</h2>

    <div class="md2word-cards">
      <!-- 上传文件 -->
      <div class="md2word-card">
        <div class="md2word-card-header">
          <el-icon><UploadFilled /></el-icon>
          <span>上传 Markdown 文件</span>
        </div>
        <div class="md2word-card-body">
          <el-upload
            drag
            :auto-upload="false"
            :on-change="onFileChange"
            accept=".md,.txt,.markdown"
            :limit="1"
            class="upload-area"
          >
            <el-icon style="font-size: 42px; color: #c0c4cc"><FolderAdd /></el-icon>
            <div style="margin-top: 10px; color: #909399; font-size: 14px">将 .md 文件拖到此处</div>
            <div style="color: #c0c4cc; font-size: 12px; margin-top: 4px">或点击选择文件</div>
          </el-upload>
          <div v-if="mdFile" class="file-selected">
            <el-icon color="#67c23a"><CircleCheck /></el-icon>
            <span class="file-name">{{ mdFile.name }}</span>
            <el-button type="primary" size="small" @click="convertFile" :loading="converting">
              <el-icon><Switch /></el-icon> 转换并下载
            </el-button>
          </div>
        </div>
      </div>

      <!-- 粘贴内容 -->
      <div class="md2word-card">
        <div class="md2word-card-header">
          <el-icon><EditPen /></el-icon>
          <span>粘贴 Markdown 内容</span>
        </div>
        <div class="md2word-card-body">
          <el-input
            v-model="mdText"
            type="textarea"
            :rows="14"
            placeholder="在此粘贴 Markdown 格式的文本..."
            class="text-input"
          />
          <div class="paste-actions">
            <el-form-item label="文件名称" class="filename-item">
              <el-input v-model="outputFilename" placeholder="converted_document" style="width: 220px" size="small" />
            </el-form-item>
            <el-button type="primary" @click="convertText" :loading="converting" :disabled="!mdText.trim()">
              <el-icon><Switch /></el-icon> 转换并下载
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 转换历史 -->
    <el-card shadow="never" style="margin-top: 24px" v-loading="historyLoading">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between">
          <span style="font-weight: bold">转换历史</span>
          <el-button size="small" type="danger" :disabled="!selectedHistory.length" @click="batchDeleteHistory">
            批量删除 ({{ selectedHistory.length }})
          </el-button>
        </div>
      </template>
      <el-table :data="historyFiles" style="width: 100%" size="small" @selection-change="onHistorySelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column prop="original_name" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="file_size" label="大小" width="100">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="转换时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="downloadHistory(row)">下载</el-button>
            <el-button size="small" type="danger" @click="deleteHistory(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!historyFiles.length" description="暂无转换记录" :image-size="60" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { md2wordApi } from '../api/md2word'
import { fileApi } from '../api/files'

const mdFile = ref(null)
const mdText = ref('')
const outputFilename = ref('')
const converting = ref(false)

// 转换历史
const historyFiles = ref([])
const historyLoading = ref(false)
const selectedHistory = ref([])

onMounted(() => {
  loadHistory()
})

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await fileApi.list({ category: 'generated', page_size: 100 })
    historyFiles.value = res.data?.items || []
  } catch (e) {
    console.error('加载转换历史失败', e)
  } finally {
    historyLoading.value = false
  }
}

function onFileChange(file) {
  mdFile.value = file.raw
}

async function convertFile() {
  if (!mdFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  converting.value = true
  try {
    const formData = new FormData()
    formData.append('file', mdFile.value)
    formData.append('output_filename', outputFilename.value || mdFile.value.name)
    const res = await md2wordApi.convertFile(formData)
    downloadBlob(res.data, outputFilename.value || mdFile.value.name.replace(/\.\w+$/, '') + '.docx')
    ElMessage.success('转换成功')
    await loadHistory()
  } catch (e) {
    ElMessage.error('转换失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    converting.value = false
  }
}

async function convertText() {
  converting.value = true
  try {
    const formData = new FormData()
    formData.append('content', mdText.value)
    formData.append('output_filename', outputFilename.value || 'converted_document')
    const res = await md2wordApi.convertText(formData)
    downloadBlob(res.data, (outputFilename.value || 'converted_document') + '.docx')
    ElMessage.success('转换成功')
    await loadHistory()
  } catch (e) {
    ElMessage.error('转换失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    converting.value = false
  }
}

function downloadHistory(row) {
  fileApi.download(row.id).then(res => {
    downloadBlob(res.data, row.original_name)
  }).catch(() => {
    ElMessage.error('下载失败')
  })
}

async function deleteHistory(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.original_name}」吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await fileApi.delete(row.id)
    ElMessage.success('已删除')
    await loadHistory()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error('删除失败')
    }
  }
}

function onHistorySelectionChange(selection) {
  selectedHistory.value = selection
}

async function batchDeleteHistory() {
  if (!selectedHistory.value.length) return
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedHistory.value.length} 个文件吗？`, '批量删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const ids = selectedHistory.value.map(f => f.id)
    await fileApi.batchDelete(ids)
    ElMessage.success(`已删除 ${ids.length} 个文件`)
    selectedHistory.value = []
    await loadHistory()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error('批量删除失败')
    }
  }
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const str = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z'
  return new Date(str).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.md2word-cards {
  display: flex;
  gap: 24px;
}

.md2word-card {
  flex: 1;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.md2word-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  background: #fafafa;
  border-bottom: 1px solid #ebeef5;
}
.md2word-card-header .el-icon {
  font-size: 18px;
  color: #409eff;
}

.md2word-card-body {
  padding: 20px;
}

.upload-area {
  width: 100%;
}

.file-selected {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
  padding: 12px 16px;
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  border-radius: 6px;
}
.file-name {
  flex: 1;
  color: #303133;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-input {
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 13px;
}

.paste-actions {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  margin-top: 16px;
}

.filename-item {
  margin-bottom: 0;
}
</style>