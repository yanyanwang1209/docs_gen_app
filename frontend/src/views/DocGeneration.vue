<template>
  <div class="doc-generation">
    <h2 style="margin: 0 0 20px 0; font-size: 20px; color: #303133">文档生成</h2>

    <el-row :gutter="20">
      <!-- 左侧：配置区 -->
      <el-col :span="12">
        <!-- 基本设置 -->
        <el-card shadow="never" style="margin-bottom: 16px">
          <template #header><span style="font-weight: bold">基本设置</span></template>
          <el-form label-width="100px" size="default">
            <el-form-item label="文档类型" required>
              <el-select v-model="form.docType" placeholder="选择文档类型" style="width: 100%" @change="onDocTypeChange">
                <el-option v-for="item in docTypes" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="章节模板" required>
              <div style="width: 100%">
                <div style="display: flex; align-items: center; gap: 8px">
                  <el-select v-model="form.templateId" placeholder="选择模板" style="flex: 1" @change="onTemplateChange">
                    <el-option-group label="系统模板">
                      <el-option v-for="tpl in filteredPresetTemplates" :key="tpl.id" :label="tpl.name" :value="tpl.id" />
                    </el-option-group>
                    <el-option-group label="个人模板">
                      <el-option v-for="tpl in filteredMyTemplates" :key="tpl.id" :label="tpl.name" :value="tpl.id" />
                    </el-option-group>
                  </el-select>
                  <el-button size="small" type="primary" @click="openNewTemplateDialog">新建</el-button>
                  <el-button size="small" @click="openTemplateEditor(form.templateId)" :disabled="!form.templateId">编辑</el-button>
                  <el-button size="small" type="danger" @click="deleteCustomTemplateById(form.templateId)" :disabled="!form.templateId || isPresetSelected">删除</el-button>
                </div>
              </div>
            </el-form-item>
            <el-form-item label="输出文件名">
              <el-input v-model="form.outputFilename" placeholder="默认：文档类型+时间" />
            </el-form-item>
            <el-form-item label="写作要求">
              <el-input v-model="form.globalRequirements" type="textarea" :rows="3"
                placeholder="例如：语言风格正式、每章节不少于500字..." />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 参考文件 -->
        <el-card shadow="never" style="margin-bottom: 16px">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between">
              <span style="font-weight: bold">参考文件</span>
              <el-upload
                :auto-upload="false"
                :on-change="onRefFileChange"
                :show-file-list="false"
                multiple
                accept=".docx,.pdf,.txt,.md,.xlsx">
                <el-button type="primary" size="small">
                  <el-icon><Upload /></el-icon> 上传文件
                </el-button>
              </el-upload>
            </div>
          </template>
          <el-select v-model="form.referenceFileIds" placeholder="选择参考文件（可多选）" multiple filterable style="width: 100%" clearable>
            <el-option v-for="f in referenceFiles" :key="f.id" :label="f.original_name" :value="f.id" />
          </el-select>
        </el-card>

        <!-- 操作按钮 -->
        <el-button type="success" size="large" style="width: 100%" @click="startGeneration"
          :loading="store.generating" :disabled="!canGenerate">
          <el-icon><VideoPlay /></el-icon>
          {{ store.generating ? '生成中...' : '开始生成文档' }}
        </el-button>
      </el-col>

      <!-- 右侧：进度和章节结果 -->
      <el-col :span="12">
        <!-- 生成进度 -->
        <el-card v-if="store.generating || store.generationResult" shadow="never" style="margin-bottom: 16px">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between">
              <span style="font-weight: bold">生成进度</span>
              <el-button v-if="store.generating" type="danger" size="small" @click="cancelGeneration" :loading="cancelling">
                终止生成
              </el-button>
            </div>
          </template>
          <div v-if="store.progress">
            <el-progress
              :percentage="store.progress.total_chapters ? Math.round(store.progress.completed_chapters / store.progress.total_chapters * 100) : 0"
              :status="store.progress.status === 'completed' ? 'success' : (store.progress.status === 'failed' ? 'exception' : '')"
              style="margin-bottom: 12px" />
            <div style="text-align: center; color: #666; margin-bottom: 8px">
              {{ store.progress.message }}
            </div>
          </div>

          <!-- 章节列表 -->
          <div v-if="store.chapterList.length" style="margin-top: 12px; max-height: 400px; overflow-y: auto">
            <div v-for="ch in store.chapterList" :key="ch.id"
              style="display: flex; align-items: center; justify-content: space-between; padding: 6px 8px; border-bottom: 1px solid #f0f0f0; font-size: 13px">
              <div style="display: flex; align-items: center; gap: 8px">
                <el-icon v-if="ch._status === 'completed'" color="#67c23a"><CircleCheck /></el-icon>
                <el-icon v-else-if="ch._status === 'generating'" color="#409eff" style="animation: spin 1s linear infinite"><Loading /></el-icon>
                <el-icon v-else-if="ch._status === 'failed'" color="#f56c6c"><CircleClose /></el-icon>
                <el-icon v-else color="#c0c4cc"><Clock /></el-icon>
                <span :style="{ color: ch._status === 'failed' ? '#f56c6c' : '#333' }">{{ ch.title }}</span>
              </div>
              <el-button v-if="ch._status === 'completed' && !store.generating"
                type="warning" size="small" :loading="ch._retrying"
                @click="retryChapter(ch.id)">重新生成</el-button>
              <el-button v-if="ch._status === 'failed' && !store.generating"
                type="danger" size="small" :loading="ch._retrying"
                @click="retryChapter(ch.id)">重试</el-button>
            </div>
          </div>

          <!-- 生成中但章节列表尚未加载 -->
          <div v-else-if="store.generating" style="margin-top: 16px; text-align: center">
            <div style="display: flex; align-items: center; justify-content: center; gap: 8px; color: #909399">
              <el-icon style="animation: spin 1s linear infinite"><Loading /></el-icon>
              <span>正在加载章节信息...</span>
            </div>
          </div>

          <div v-if="store.generationResult?.status === 'completed'" style="text-align: center; margin-top: 16px">
            <el-button type="default" @click="openPreview" size="large">
              <el-icon><View /></el-icon> 预览
            </el-button>
            <el-button type="primary" @click="downloadWord" :loading="downloading" size="large">
              <el-icon><Download /></el-icon> 下载 Word 文档
            </el-button>
          </div>
        </el-card>

        <!-- 空状态 -->
        <el-empty v-if="!store.generating && !store.generationResult" description="选择文档类型和模板后，点击「开始生成文档」"
          style="margin-top: 60px" />
      </el-col>
    </el-row>

    <!-- 模板编辑器弹窗 -->
    <ChapterTreeEditor v-if="showTemplateEditor" v-model="showTemplateEditor"
      :template-id="editingTemplateId" @saved="onTemplateSaved" />

    <!-- 新建自定义模板弹窗 -->
    <el-dialog v-model="showNewTemplateDialog" title="新建模板" width="450px" :close-on-click-modal="false">
      <el-form label-width="80px" size="default">
        <el-form-item label="模板名称" required>
          <el-input v-model="newTemplateForm.name" placeholder="例如：我的测试模板" maxlength="50" />
        </el-form-item>
        <el-form-item label="关联类型">
          <el-select v-model="newTemplateForm.doc_type" placeholder="选择文档类型（可选）" style="width: 100%" clearable>
            <el-option v-for="item in docTypes" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newTemplateForm.description" type="textarea" :rows="2" placeholder="模板用途说明（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNewTemplateDialog = false">取消</el-button>
        <el-button type="primary" @click="createNewTemplate">创建并编辑章节</el-button>
      </template>
    </el-dialog>

    <!-- 预览弹窗 -->
    <el-dialog v-model="showPreview" :title="previewTitle" width="85%" top="20px" destroy-on-close>
      <div v-if="previewLoading" style="text-align: center; padding: 40px">
        <el-icon class="is-loading" style="font-size: 32px; color: #409eff"><Loading /></el-icon>
        <p style="margin-top: 12px; color: #999">加载中...</p>
      </div>
      <div v-else-if="previewHtml" style="display: flex; gap: 0; height: 70vh">
        <!-- 标题导航侧边栏 -->
        <div class="heading-nav" :class="{ collapsed: navCollapsed }">
          <div class="heading-nav-header">
            <span v-show="!navCollapsed" style="font-weight: 600; font-size: 14px">文档导航</span>
            <span @click="navCollapsed = !navCollapsed" class="nav-toggle-btn" :title="navCollapsed ? '展开导航' : '收起导航'">
              {{ navCollapsed ? '▶' : '◀' }}
            </span>
          </div>
          <div v-show="!navCollapsed" class="heading-nav-list">
            <div v-if="!headings.length" style="color: #999; font-size: 12px; text-align: center; padding: 20px 0">
              未检测到标题
            </div>
            <div
              v-for="(h, idx) in headings"
              :key="idx"
              class="heading-nav-item"
              :class="{ active: activeHeadingIndex === idx }"
              :style="{ paddingLeft: Math.min((h.level - 1) * 16 + 12, 60) + 'px' }"
              :title="h.text"
              @click="scrollToHeading(idx)"
            >
              {{ h.text }}
            </div>
          </div>
        </div>
        <!-- 预览内容 -->
        <div class="markdown-preview" ref="previewContentRef" @scroll="onPreviewScroll" v-html="previewHtml" />
      </div>
      <el-empty v-else description="暂无内容" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import { templateApi } from '../api/templates'
import { fileApi } from '../api/files'
import { generationApi } from '../api/generation'
import { useGenerationStore } from '../stores/generation'
import ChapterTreeEditor from '../components/ChapterTreeEditor.vue'

const store = useGenerationStore()

const docTypes = [
  { value: 'srs', label: '需求规格说明书' },
  { value: 'hld', label: '概要设计文档' },
  { value: 'dd', label: '详细设计文档' },
  { value: 'dbd', label: '数据库设计文档' },
  { value: 'tp', label: '测试计划' },
  { value: 'ts', label: '测试方案' },
  { value: 'tc', label: '测试用例' },
  { value: 'tr', label: '测试记录' },
  { value: 'trep', label: '测试报告' },
]

const form = reactive({
  docType: '',
  outputFilename: '',
  globalRequirements: '',
  templateId: '',
  referenceFileIds: [],
})

const referenceFiles = ref([])
const uploadingRefFiles = ref([])  // 待上传的参考文件
const templates = ref([])           // 所有模板列表
const presetTemplates = ref([])     // 系统模板
const myTemplates = ref([])         // 个人模板
const showTemplateEditor = ref(false)
const editingTemplateId = ref('')   // 当前编辑的模板ID
const showNewTemplateDialog = ref(false)
const newTemplateForm = reactive({
  name: '',
  description: '',
  doc_type: '',
})

const downloading = ref(false)
const cancelling = ref(false)

const isPresetSelected = computed(() => {
  const tpl = templates.value.find(t => t.id === form.templateId)
  return tpl?.is_preset || false
})

// 按文档类型过滤模板
const filteredPresetTemplates = computed(() => {
  if (!form.docType) return presetTemplates.value
  return presetTemplates.value.filter(t => t.doc_type === form.docType)
})
const filteredMyTemplates = computed(() => {
  if (!form.docType) return myTemplates.value
  return myTemplates.value.filter(t => t.doc_type === form.docType)
})

// 预览弹窗
const showPreview = ref(false)
const previewTitle = ref('')
const previewLoading = ref(false)
const previewHtml = ref('')
const previewContentRef = ref(null)
const headings = ref([])           // 提取的标题列表 [{level, text, element}]
const activeHeadingIndex = ref(-1) // 当前激活的标题索引
const navCollapsed = ref(false)    // 导航是否折叠

const canGenerate = computed(() => form.docType && form.templateId)

onMounted(async () => {
  await loadReferenceFiles()
  await loadTemplates()
  // 如果之前有任务（生成中或已完成），恢复状态和表单
  if (store.currentTaskId) {
    await store.restoreTask(store.currentTaskId)
    restoreFormFromTask()
  }
})

async function loadReferenceFiles() {
  try {
    const res = await fileApi.list({ category: 'reference', page_size: 100 })
    referenceFiles.value = res.data.items
  } catch (e) {
    console.error('加载参考文件失败', e)
  }
}

async function loadTemplates() {
  try {
    const res = await templateApi.list()
    const items = res.data?.items || []
    templates.value = items.map(t => ({
      ...t,
      label: t.name,
      chapterCount: t.chapter_count,
    }))
    // 分组：系统模板 + 个人模板
    presetTemplates.value = templates.value.filter(t => t.is_preset)
    myTemplates.value = templates.value.filter(t => !t.is_preset)
  } catch (e) {
    console.error('加载模板失败', e)
  }
}

function onDocTypeChange(docType) {
  if (!docType) {
    form.templateId = ''
    return
  }
  // 检查当前选中的模板是否匹配新类型
  const currentTpl = templates.value.find(t => t.id === form.templateId)
  if (currentTpl && currentTpl.doc_type === docType) {
    return // 当前模板匹配，保持不变
  }
  // 自动匹配该类型的系统模板
  const match = presetTemplates.value.find(t => t.doc_type === docType)
  form.templateId = match?.id || ''
}

function onTemplateChange(val) {
  // 选中的模板变化时无需额外操作
}

function openTemplateEditor(templateId) {
  if (!templateId) return
  editingTemplateId.value = templateId
  showTemplateEditor.value = true
}

async function deleteCustomTemplateById(templateId) {
  if (!templateId) return
  const tpl = myTemplates.value.find(t => t.id === templateId)
  if (!tpl) return
  try {
    await ElMessageBox.confirm(`确定要删除模板「${tpl.name}」吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await templateApi.delete(templateId)
    ElMessage.success('模板已删除')
    form.templateId = ''
    await loadTemplates()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

async function createNewTemplate() {
  if (!newTemplateForm.name.trim()) {
    ElMessage.warning('请输入模板名称')
    return
  }
  try {
    const res = await templateApi.create({
      name: newTemplateForm.name.trim(),
      doc_type: newTemplateForm.doc_type || form.docType || 'srs',
      description: newTemplateForm.description.trim(),
      chapters: [],
    })
    ElMessage.success('模板创建成功')
    showNewTemplateDialog.value = false
    newTemplateForm.name = ''
    newTemplateForm.description = ''
    newTemplateForm.doc_type = ''
    await loadTemplates()
    // 自动选中新模板
    form.templateId = res.data.id
    // 打开编辑器让用户编辑章节
    openTemplateEditor(res.data.id)
  } catch (e) {
    ElMessage.error('创建失败: ' + (e.response?.data?.detail || e.message))
  }
}

function openNewTemplateDialog() {
  newTemplateForm.name = ''
  newTemplateForm.description = ''
  newTemplateForm.doc_type = form.docType || ''
  showNewTemplateDialog.value = true
}

function onTemplateSaved(newId) {
  showTemplateEditor.value = false
  loadTemplates()
  // 如果是编辑系统模板后创建的个人副本，自动选中新模板
  if (newId && newId !== editingTemplateId.value) {
    form.templateId = newId
  }
}

function onRefFileChange(file) {
  uploadingRefFiles.value.push(file.raw)
  uploadRefFiles()
}

async function uploadRefFiles() {
  if (!uploadingRefFiles.value.length) return
  const formData = new FormData()
  for (const f of uploadingRefFiles.value) {
    formData.append('files', f)
  }
  formData.append('category', 'reference')
  try {
    const res = await fileApi.upload(formData)
    const newFiles = res.data || []
    const newIds = newFiles.map(f => f.id)
    form.referenceFileIds.push(...newIds)
    await loadReferenceFiles()
    uploadingRefFiles.value = []
    ElMessage.success(`成功上传 ${newFiles.length} 个文件`)
  } catch (e) {
    ElMessage.error('上传失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function startGeneration() {
  store.generating = true
  store.generationResult = null
  store.progress = null
  store.chapterList = []

  // 保存当前表单数据，用于页面切换回来时恢复
  store.currentTaskData = {
    doc_type: form.docType,
    template_id: form.templateId,
    output_filename: form.outputFilename,
    global_requirements: form.globalRequirements,
    reference_file_ids: form.referenceFileIds,
  }

  try {
    const res = await generationApi.start({
      doc_type: form.docType,
      output_filename: form.outputFilename,
      global_requirements: form.globalRequirements,
      template_id: form.templateId,
      reference_file_ids: form.referenceFileIds,
    })
    store.connectWebSocket(res.data.id)
  } catch (e) {
    store.generating = false
    store.currentTaskData = null
    ElMessage.error('启动生成失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function cancelGeneration() {
  if (!store.currentTaskId) return
  try {
    await ElMessageBox.confirm('确定要终止当前文档生成吗？已生成的内容将保留。', '确认终止', {
      confirmButtonText: '终止',
      cancelButtonText: '取消',
      type: 'warning',
    })
    cancelling.value = true
    await generationApi.cancelTask(store.currentTaskId)
    store.generating = false
    store.progress = { status: 'failed', message: '用户取消生成' }
    ElMessage.warning('文档生成已终止')
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error('终止失败: ' + (e.response?.data?.detail || e.message))
    }
  } finally {
    cancelling.value = false
  }
}

async function retryChapter(chapterId) {
  const item = store.chapterList.find(ch => ch.id === chapterId)
  if (!item) return

  // 构建历史修改要求提示
  const prevReasons = item._retryReasons || []
  const lastReason = prevReasons.length > 0 ? prevReasons[prevReasons.length - 1] : ''
  let hintText = ''
  if (prevReasons.length > 0) {
    hintText = '历史修改要求：\n' + prevReasons.map((r, i) => `  ${i + 1}. ${r}`).join('\n')
    hintText += '\n\n请在下方输入本次额外的修改要求（将综合以上所有历史要求进行调整）：'
  }

  try {
    const { value } = await ElMessageBox.prompt(
      hintText || '请输入重新生成的原因和额外要求（可选）',
      `重新生成: ${item.title}`,
      {
        confirmButtonText: '开始生成',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputValue: lastReason,
        inputRows: 6,
        inputPlaceholder: '例如：内容不够详细、需要加入更多数据示例、请使用更正式的措辞...',
        customStyle: { width: '520px' },
      }
    )
    item._retrying = true
    await generationApi.retryChapter(store.currentTaskId, chapterId, { retry_reason: value || '' })
    ElMessage.success(`章节 "${item.title}" 重新生成成功`)
    await store.loadTaskResult(store.currentTaskId)
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error('重试失败: ' + (e.response?.data?.detail || e.message))
    }
  } finally {
    item._retrying = false
  }
}

async function downloadWord() {
  if (!store.generationResult) return
  downloading.value = true
  try {
    const res = await generationApi.buildWord(store.generationResult.id)
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = (store.generationResult.output_filename || 'document') + '.docx'
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (e) {
    ElMessage.error('下载失败')
  } finally {
    downloading.value = false
  }
}

// 从 store 中保存的任务数据恢复表单
function restoreFormFromTask() {
  const task = store.currentTaskData
  if (!task) return
  // 恢复基本设置
  if (task.doc_type) {
    form.docType = task.doc_type
  }
  if (task.template_id) {
    form.templateId = task.template_id
  }
  if (task.output_filename) {
    form.outputFilename = task.output_filename
  }
  if (task.global_requirements) {
    form.globalRequirements = task.global_requirements
  }
  // 恢复参考文件
  if (task.reference_file_ids) {
    try {
      const ids = typeof task.reference_file_ids === 'string'
        ? JSON.parse(task.reference_file_ids)
        : task.reference_file_ids
      form.referenceFileIds = ids
    } catch {
      form.referenceFileIds = []
    }
  }
}

async function openPreview() {
  if (!store.generationResult) return
  showPreview.value = true
  previewTitle.value = store.generationResult.output_filename || '文档预览'
  previewLoading.value = true
  previewHtml.value = ''
  headings.value = []
  activeHeadingIndex.value = -1
  try {
    const res = await generationApi.previewTask(store.generationResult.id)
    const md = res.data.markdown || ''
    previewHtml.value = marked.parse(md)
    // 等待 v-html 渲染完成（nextTick 可能不够，需要额外延迟）
    await nextTick()
    setTimeout(() => {
      extractHeadings()
    }, 100)
  } catch (e) {
    previewHtml.value = '<p style="color: #f56c6c">加载预览失败</p>'
    ElMessage.error('加载预览失败')
  } finally {
    previewLoading.value = false
  }
}

function extractHeadings() {
  const el = previewContentRef.value
  if (!el) return
  const headingEls = el.querySelectorAll('h1, h2, h3, h4, h5, h6')
  const result = []
  headingEls.forEach((h) => {
    const level = parseInt(h.tagName.charAt(1))
    const text = h.textContent || ''
    if (text.trim()) {
      // 给每个标题加上 id 以便跳转
      const id = 'heading-' + result.length
      h.id = id
      result.push({ level, text: text.trim(), id })
    }
  })
  headings.value = result
}

function scrollToHeading(idx) {
  const el = previewContentRef.value
  if (!el) return
  const target = el.querySelector('#heading-' + idx)
  if (target) {
    target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    activeHeadingIndex.value = idx
  }
}

function onPreviewScroll() {
  const el = previewContentRef.value
  if (!el || !headings.value.length) return
  const scrollTop = el.scrollTop
  let activeIdx = -1
  // 从后往前找到第一个在可视区域内的标题
  const headingEls = el.querySelectorAll('[id^="heading-"]')
  for (let i = headingEls.length - 1; i >= 0; i--) {
    const h = headingEls[i]
    if (h.offsetTop <= scrollTop + 60) {
      activeIdx = i
      break
    }
  }
  activeHeadingIndex.value = activeIdx
}
</script>

<style scoped>
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.markdown-preview {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
  line-height: 1.8;
  color: #333;
  font-size: 14px;
}
.markdown-preview :deep(h1) { font-size: 24px; border-bottom: 1px solid #eee; padding-bottom: 8px; margin: 16px 0 12px; }
.markdown-preview :deep(h2) { font-size: 20px; border-bottom: 1px solid #f0f0f0; padding-bottom: 6px; margin: 14px 0 10px; }
.markdown-preview :deep(h3) { font-size: 17px; margin: 12px 0 8px; }
.markdown-preview :deep(h4) { font-size: 15px; margin: 10px 0 6px; }
.markdown-preview :deep(h5) { font-size: 14px; margin: 8px 0 6px; }
.markdown-preview :deep(p) { margin: 8px 0; text-indent: 2em; }
.markdown-preview :deep(table) { border-collapse: collapse; width: 100%; margin: 12px 0; }
.markdown-preview :deep(th), .markdown-preview :deep(td) { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
.markdown-preview :deep(th) { background: #f5f7fa; font-weight: 600; }
.markdown-preview :deep(code) { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: Consolas, monospace; font-size: 13px; }
.markdown-preview :deep(pre) { background: #f5f5f5; padding: 12px 16px; border-radius: 4px; overflow-x: auto; }
.markdown-preview :deep(pre code) { background: none; padding: 0; }
.markdown-preview :deep(ul), .markdown-preview :deep(ol) { padding-left: 2em; margin: 8px 0; }
.markdown-preview :deep(li) { margin: 4px 0; }
.markdown-preview :deep(blockquote) { border-left: 4px solid #ddd; padding: 4px 12px; margin: 8px 0; color: #666; }
.markdown-preview :deep(img) { max-width: 100%; }
.markdown-preview :deep(hr) { border: none; border-top: 1px solid #eee; margin: 16px 0; }

/* 标题导航侧边栏 */
.heading-nav {
  width: 220px;
  min-width: 220px;
  border-right: 1px solid #e8e8e8;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  transition: width 0.2s, min-width 0.2s;
  overflow: hidden;
}
.heading-nav.collapsed {
  width: 36px;
  min-width: 36px;
}
.heading-nav-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #e8e8e8;
  flex-shrink: 0;
}
.nav-toggle-btn {
  cursor: pointer;
  font-size: 12px;
  color: #909399;
  padding: 2px 6px;
  border-radius: 3px;
  user-select: none;
}
.nav-toggle-btn:hover {
  color: #409eff;
  background: #ecf5ff;
}
.heading-nav-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}
.heading-nav-item {
  font-size: 12px;
  line-height: 1.5;
  padding: 6px 12px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #606266;
  border-left: 2px solid transparent;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.heading-nav-item:hover {
  background: #ecf5ff;
  color: #409eff;
}
.heading-nav-item.active {
  background: #ecf5ff;
  color: #409eff;
  border-left-color: #409eff;
  font-weight: 600;
}
</style>