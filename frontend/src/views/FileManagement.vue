<template>
  <div class="file-management">
    <h2 style="margin: 0 0 20px 0; font-size: 20px; color: #303133">文件管理</h2>
    <el-tabs v-model="activeTab" @tab-change="loadFiles">
      <el-tab-pane label="参考文件" name="reference" />
      <el-tab-pane label="生成文件" name="generated" />
    </el-tabs>

    <!-- 工具栏 -->
    <div style="display: flex; gap: 12px; margin-bottom: 16px; align-items: center; flex-wrap: wrap">
      <el-input v-model="searchText" placeholder="搜索文件名或标签" style="width: 300px" clearable
        @clear="loadFiles" @keyup.enter="loadFiles">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="fileTypeFilter" placeholder="文件类型" style="width: 120px" clearable @change="loadFiles">
        <el-option label="DOCX" value="docx" />
        <el-option label="PDF" value="pdf" />
        <el-option label="TXT" value="txt" />
        <el-option label="MD" value="md" />
        <el-option label="XLSX" value="xlsx" />
      </el-select>
      <el-button type="primary" @click="loadFiles">
        <el-icon><Search /></el-icon> 搜索
      </el-button>
      <el-upload v-if="activeTab === 'reference'"
        :auto-upload="false" :on-change="onUploadChange" :show-file-list="false" multiple
        accept=".docx,.pdf,.txt,.md,.xlsx">
        <el-button type="success">
          <el-icon><Upload /></el-icon> 上传文件
        </el-button>
      </el-upload>
      <el-button v-if="selectedIds.length" type="danger" @click="batchDelete" :loading="batchDeleting">
        <el-icon><Delete /></el-icon> 批量删除 ({{ selectedIds.length }})
      </el-button>
    </div>

    <!-- 文件表格 -->
    <el-table :data="files" stripe style="width: 100%" v-loading="loading"
      @selection-change="onSelectionChange" ref="tableRef">
      <el-table-column type="selection" width="45" />
      <el-table-column prop="original_name" label="文件名" min-width="200" show-overflow-tooltip />
      <el-table-column prop="file_type" label="类型" width="70">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.file_type.toUpperCase() }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="file_size" label="大小" width="90">
        <template #default="{ row }">
          {{ formatSize(row.file_size) }}
        </template>
      </el-table-column>
      <el-table-column prop="tags" label="标签" width="150" show-overflow-tooltip />
      <el-table-column prop="notes" label="备注" width="150" show-overflow-tooltip />
      <el-table-column prop="created_at" :label="activeTab === 'generated' ? '生成时间' : '上传时间'" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="downloadFile(row)">
            <el-icon><Download /></el-icon>
          </el-button>
          <el-button size="small" @click="editFile(row)">
            <el-icon><Edit /></el-icon>
          </el-button>
          <el-button size="small" type="danger" @click="deleteFile(row)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div style="margin-top: 16px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadFiles"
      />
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editVisible" title="编辑文件信息" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="文件名">
          <el-input v-model="editForm.original_name" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="editForm.tags" placeholder="逗号分隔多个标签" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.notes" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fileApi } from '../api/files'

const activeTab = ref('reference')
const searchText = ref('')
const fileTypeFilter = ref('')
const files = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const tableRef = ref(null)
const selectedIds = ref([])

const editVisible = ref(false)
const editForm = ref({})
const editId = ref('')
const uploadingFiles = ref([])

// 批量删除
const batchDeleting = ref(false)

onMounted(() => loadFiles())

async function loadFiles() {
  loading.value = true
  selectedIds.value = []
  try {
    const res = await fileApi.list({
      category: activeTab.value,
      search: searchText.value || undefined,
      file_type: fileTypeFilter.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    files.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    ElMessage.error('加载文件列表失败')
  } finally {
    loading.value = false
  }
}

function onSelectionChange(selection) {
  selectedIds.value = selection.map(r => r.id)
}

async function onUploadChange(file) {
  uploadingFiles.value.push(file.raw)
  await uploadFiles()
}

async function uploadFiles() {
  if (!uploadingFiles.value.length) return
  const formData = new FormData()
  for (const f of uploadingFiles.value) {
    formData.append('files', f)
  }
  formData.append('category', activeTab.value)
  try {
    await fileApi.upload(formData)
    uploadingFiles.value = []
    ElMessage.success('上传成功')
    loadFiles()
  } catch (e) {
    ElMessage.error('上传失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function downloadFile(row) {
  try {
    const res = await fileApi.download(row.id)
    const blob = new Blob([res.data])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = row.original_name
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

function editFile(row) {
  editId.value = row.id
  editForm.value = {
    original_name: row.original_name,
    tags: row.tags,
    notes: row.notes,
  }
  editVisible.value = true
}

async function saveEdit() {
  try {
    await fileApi.update(editId.value, {
      filename: editForm.value.original_name,
      tags: editForm.value.tags,
      notes: editForm.value.notes,
    })
    editVisible.value = false
    ElMessage.success('保存成功')
    loadFiles()
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

async function deleteFile(row) {
  try {
    await ElMessageBox.confirm(`确定删除文件 "${row.original_name}" 吗？`, '确认删除', {
      type: 'warning',
    })
    await fileApi.delete(row.id)
    ElMessage.success('删除成功')
    loadFiles()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function batchDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedIds.value.length} 个文件吗？此操作不可恢复。`,
      '批量删除确认',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
    batchDeleting.value = true
    await fileApi.batchDelete(selectedIds.value)
    ElMessage.success(`成功删除 ${selectedIds.value.length} 个文件`)
    loadFiles()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('批量删除失败: ' + (e.response?.data?.detail || e.message))
    }
  } finally {
    batchDeleting.value = false
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
  // 后端 SQLite func.now() 返回 UTC 时间，JSON 序列化后不带时区标识
  // 需要加上 'Z' 让 JS 识别为 UTC，再用 Asia/Shanghai 转换
  const str = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z'
  return new Date(str).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}
</script>