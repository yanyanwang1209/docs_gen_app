<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="'章节模板编辑器'"
    width="900px"
    top="5vh"
    :close-on-click-modal="false"
  >
    <div v-loading="loading" style="display: flex; gap: 16px; height: 500px; overflow: hidden">
      <!-- 左侧：章节树 -->
      <div style="width: 350px; border-right: 1px solid #ebeef5; overflow-y: auto; padding-right: 8px">
        <!-- 模板名称（仅非系统模板可编辑） -->
        <div v-if="!isPreset" style="margin-bottom: 8px">
          <el-input v-model="templateName" placeholder="模板名称" size="small" />
        </div>
        <div v-else style="margin-bottom: 8px; font-weight: bold; font-size: 14px; color: #303133">
          {{ templateName }}
        </div>
        <div style="margin-bottom: 8px; display: flex; gap: 4px; flex-wrap: wrap">
          <el-button size="small" @click="addChapter(null)">添加章节</el-button>
          <el-button size="small" @click="autoNumber">自动编号</el-button>
          <el-button v-if="!isPreset" size="small" type="warning" @click="triggerAiAnalyze" :loading="aiAnalyzing">
            <el-icon style="margin-right: 2px"><MagicStick /></el-icon>
            AI 分析
          </el-button>
          <el-tooltip v-if="!isPreset" content="上传文档（.docx/.pdf/.txt/.md），由 AI 自动分析文档内容并生成章节结构，每个章节会自动填写内容提示语" placement="top">
            <el-icon style="margin-left: 2px; color: #909399; cursor: help; font-size: 16px"><QuestionFilled /></el-icon>
          </el-tooltip>
          <input
            ref="fileInputRef"
            type="file"
            accept=".docx,.pdf,.txt,.md"
            style="display: none"
            @change="onAiFileSelected"
          />
        </div>
        <el-tree
          v-if="treeData.length"
          :data="treeData"
          :props="{ children: 'children', label: 'title' }"
          node-key="id"
          default-expand-all
          highlight-current
          :expand-on-click-node="false"
          @node-click="onNodeClick"
          draggable
          :allow-drop="allowDrop"
          @node-drop="onNodeDrop"
        >
          <template #default="{ data }">
            <span style="font-size: 13px">
              <el-tag size="small" :type="data.title_only ? 'info' : ''" style="margin-right: 4px">
                {{ data.title_only ? '标题' : data.content_type === 'table' ? '表格' : data.content_type === 'mixed' ? '混合' : '文字' }}
              </el-tag>
              {{ data.title }}
            </span>
          </template>
        </el-tree>
        <el-empty v-else description="暂无章节，请添加" :image-size="80" />
      </div>

      <!-- 右侧：章节详情编辑面板 -->
      <div style="flex: 1; overflow-y: auto; padding-left: 8px">
        <div v-if="!selectedNode" style="color: #999; text-align: center; margin-top: 100px">
          <el-icon style="font-size: 48px"><InfoFilled /></el-icon>
          <div style="margin-top: 12px">点击左侧章节查看和编辑详情</div>
        </div>
        <el-form v-else label-width="100px" size="small">
          <el-form-item label="章节标题">
            <el-input v-model="selectedNode.title" />
          </el-form-item>
          <el-form-item label="仅生成标题">
            <el-switch v-model="selectedNode.title_only" />
            <span style="margin-left: 8px; color: #999; font-size: 12px">开启后该章节仅输出标题，不生成内容</span>
          </el-form-item>
          <el-form-item label="内容类型" v-if="!selectedNode.title_only">
            <el-radio-group v-model="selectedNode.content_type">
              <el-radio value="text">纯文字</el-radio>
              <el-radio value="table">表格</el-radio>
              <el-radio value="mixed">文字 + 表格</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="内容提示" v-if="!selectedNode.title_only">
            <el-input v-model="selectedNode.content_prompt" type="textarea" :rows="3"
              placeholder="告诉 AI 这个章节应该写什么内容..." />
          </el-form-item>

          <!-- 表格配置 -->
          <template v-if="!selectedNode.title_only && (selectedNode.content_type === 'table' || selectedNode.content_type === 'mixed')">
            <el-divider content-position="left">表格配置</el-divider>
            <el-form-item label="表格说明">
              <el-input v-model="tableConfig.header" placeholder="表格标题或说明文字" />
            </el-form-item>
            <el-form-item label="行列设置">
              <el-input-number v-model="tableConfig.rows" :min="1" :max="50" size="small" /> 行
              <el-input-number v-model="tableConfig.cols" :min="1" :max="20" size="small" style="margin-left: 8px" /> 列
              <el-button size="small" style="margin-left: 8px" @click="applyTableSize">应用</el-button>
            </el-form-item>

            <el-form-item label="表格内容">
              <div style="overflow-x: auto">
                <table class="config-table">
                  <tbody>
                    <tr v-for="ri in tableConfig.rows" :key="ri">
                      <td v-for="ci in tableConfig.cols" :key="ci"
                        :class="{ 'fixed-cell': isFixedCell(ri - 1, ci - 1) }"
                        @click="handleCellClick(ri - 1, ci - 1, $event)"
                        @dblclick="handleCellDblClick(ri - 1, ci - 1)">
                        <el-input
                          v-if="isFixedCell(ri - 1, ci - 1)"
                          :ref="(el) => setCellInputRef(ri - 1, ci - 1, el)"
                          :model-value="getFixedCellValue(ri - 1, ci - 1)"
                          @update:model-value="setFixedCellValue(ri - 1, ci - 1, $event)"
                          size="small" placeholder="固定值" style="width: 80px" />
                        <span v-else style="color: #999; font-size: 11px">AI 填充</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div style="color: #999; font-size: 11px; margin-top: 4px">点击单元格标记为固定内容并输入，双击固定单元格取消</div>
            </el-form-item>
          </template>

          <!-- 章节操作 -->
          <div style="margin-top: 16px; display: flex; gap: 8px">
            <el-button size="small" @click="addChapter(selectedNode.id)">添加子章节</el-button>
            <el-button size="small" @click="addSiblingChapter">添加同级章节</el-button>
            <el-button size="small" type="danger" @click="deleteChapter">删除此章节</el-button>
          </div>
        </el-form>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="saveTemplate" :loading="saving">保存模板</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick, QuestionFilled } from '@element-plus/icons-vue'
import { templateApi } from '../api/templates'

const props = defineProps({
  modelValue: Boolean,
  templateId: String,
})

const emit = defineEmits(['update:modelValue', 'saved'])

const treeData = ref([])
const selectedNode = ref(null)
const isPreset = ref(false)
const templateName = ref('')
const loading = ref(false)
const saving = ref(false)
const tableConfig = reactive({
  header: '',
  rows: 3,
  cols: 3,
  fixed_cells: [],
})

let nodeMap = {}
const cellInputRefs = {}
const fileInputRef = ref(null)
const aiAnalyzing = ref(false)

function setCellInputRef(row, col, el) {
  if (el) cellInputRefs[`${row}_${col}`] = el
}

// 当弹窗打开时加载模板数据
watch(() => props.modelValue, async (val) => {
  if (val && props.templateId) {
    await loadTemplate()
  }
}, { immediate: true })

async function loadTemplate() {
  loading.value = true
  try {
    const res = await templateApi.get(props.templateId)
    treeData.value = JSON.parse(JSON.stringify(res.data.chapters || []))
    isPreset.value = res.data.is_preset || false
    templateName.value = res.data.name || ''
    buildNodeMap(treeData.value)
    selectedNode.value = null
  } catch (e) {
    console.error('加载模板失败', e)
    ElMessage.error('加载模板失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

function buildNodeMap(nodes, map = {}) {
  for (const node of nodes) {
    map[node.id] = node
    if (node.children?.length) {
      buildNodeMap(node.children, map)
    }
  }
  nodeMap = map
}

function onNodeClick(data) {
  syncTableConfigToNode()
  selectedNode.value = data
  // 加载表格配置
  let tc = data.table_config
  if (typeof tc === 'string') {
    try { tc = JSON.parse(tc) } catch { tc = {} }
  }
  tc = tc || {}
  tableConfig.header = tc.header || ''
  tableConfig.rows = tc.rows || 3
  tableConfig.cols = tc.cols || 3
  tableConfig.fixed_cells = tc.fixed_cells || []
}

function addChapter(parentId) {
  const newId = 'new_' + Date.now()
  const newNode = {
    id: newId,
    title: '新章节',
    level: parentId ? (nodeMap[parentId]?.level || 1) + 1 : 1,
    sort_order: 0,
    title_only: false,
    content_type: 'text',
    content_prompt: '',
    table_config: {},
    content_blocks: [],
    children: [],
  }

  if (parentId) {
    const parent = nodeMap[parentId]
    if (parent) {
      if (!parent.children) parent.children = []
      parent.children.push(newNode)
    }
  } else {
    treeData.value.push(newNode)
  }
  buildNodeMap(treeData.value)
  selectedNode.value = newNode
}

function addSiblingChapter() {
  if (!selectedNode.value) return
  const parentId = findParentId(treeData.value, selectedNode.value.id)
  addChapter(parentId || null)
}

function findParentId(nodes, targetId, parentId = null) {
  for (const node of nodes) {
    if (node.id === targetId) return parentId
    if (node.children?.length) {
      const found = findParentId(node.children, targetId, node.id)
      if (found !== undefined) return found
    }
  }
  return undefined
}

function deleteChapter() {
  if (!selectedNode.value) return
  removeNode(treeData.value, selectedNode.value.id)
  buildNodeMap(treeData.value)
  selectedNode.value = null
}

function removeNode(nodes, targetId) {
  for (let i = nodes.length - 1; i >= 0; i--) {
    if (nodes[i].id === targetId) {
      nodes.splice(i, 1)
      return true
    }
    if (nodes[i].children?.length) {
      if (removeNode(nodes[i].children, targetId)) return true
    }
  }
  return false
}

function allowDrop(draggingNode, dropNode, type) {
  return type !== 'inner' || draggingNode.data.id !== dropNode.data.id
}

function onNodeDrop() {
  buildNodeMap(treeData.value)
}

function autoNumber() {
  autoNumberNodes(treeData.value, [])
  buildNodeMap(treeData.value)
}

function autoNumberNodes(nodes, parentNumbers) {
  nodes.forEach((node, i) => {
    const nums = [...parentNumbers, i + 1]
    node.title = nums.join('.') + ' ' + node.title.replace(/^\d+(\.\d+)*\s*/, '')
    node.level = nums.length
    if (node.children?.length) {
      autoNumberNodes(node.children, nums)
    }
  })
}

function isFixedCell(row, col) {
  return tableConfig.fixed_cells.some(c => c.row === row && c.col === col)
}

function handleCellClick(row, col, event) {
  // 点击在输入框组件内部时忽略，让用户正常输入
  if (event?.target?.closest('.el-input') || event?.target?.tagName === 'INPUT') {
    return
  }
  const isFixed = isFixedCell(row, col)
  if (isFixed) {
    // 已经固定：点击单元格空白区域聚焦到输入框
    const refKey = `${row}_${col}`
    const el = cellInputRefs[refKey]
    if (el) {
      el.focus()
    }
  } else {
    // 标记为固定值，然后聚焦输入框
    tableConfig.fixed_cells.push({ row, col, value: '' })
    nextTick(() => {
      const refKey = `${row}_${col}`
      const el = cellInputRefs[refKey]
      if (el) {
        el.focus()
      }
    })
  }
}

// 双击固定单元格取消固定标记
function handleCellDblClick(row, col) {
  const idx = tableConfig.fixed_cells.findIndex(c => c.row === row && c.col === col)
  if (idx >= 0) {
    tableConfig.fixed_cells.splice(idx, 1)
  }
}

function getFixedCellValue(row, col) {
  return tableConfig.fixed_cells.find(c => c.row === row && c.col === col)?.value || ''
}

function setFixedCellValue(row, col, value) {
  const cell = tableConfig.fixed_cells.find(c => c.row === row && c.col === col)
  if (cell) cell.value = value
}

function applyTableSize() {
  tableConfig.fixed_cells = tableConfig.fixed_cells.filter(
    c => c.row < tableConfig.rows && c.col < tableConfig.cols
  )
}

function syncTableConfigToNode() {
  if (selectedNode.value) {
    selectedNode.value.table_config = {
      header: tableConfig.header,
      rows: tableConfig.rows,
      cols: tableConfig.cols,
      fixed_cells: tableConfig.fixed_cells,
    }
  }
}

function triggerAiAnalyze() {
  fileInputRef.value?.click()
}

async function onAiFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return

  // 如果已有章节，弹出确认
  if (treeData.value.length > 0) {
    try {
      await ElMessageBox.confirm(
        'AI 分析将覆盖当前章节结构，是否继续？',
        '确认覆盖',
        { confirmButtonText: '继续', cancelButtonText: '取消', type: 'warning' }
      )
    } catch {
      // 用户取消，重置 file input
      if (fileInputRef.value) fileInputRef.value.value = ''
      return
    }
  }

  aiAnalyzing.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await templateApi.aiAnalyze(formData)
    const chapters = res.data?.chapters || []

    if (!chapters.length) {
      ElMessage.warning('AI 未分析出章节结构，请尝试其他文档')
      return
    }

    // 给每个节点生成临时 ID
    function assignIds(nodes) {
      for (const node of nodes) {
        node.id = 'ai_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
        node.sort_order = 0
        if (node.children?.length) {
          assignIds(node.children)
        }
      }
    }
    assignIds(chapters)

    treeData.value = chapters
    buildNodeMap(treeData.value)
    selectedNode.value = null
    ElMessage.success(`AI 已分析生成 ${countNodes(chapters)} 个章节`)
  } catch (e) {
    ElMessage.error('AI 分析失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    aiAnalyzing.value = false
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

function countNodes(nodes) {
  let count = 0
  for (const node of nodes) {
    count++
    if (node.children?.length) {
      count += countNodes(node.children)
    }
  }
  return count
}

async function saveTemplate() {
  syncTableConfigToNode()
  saving.value = true
  try {
    const res = await templateApi.update(props.templateId, {
      name: templateName.value || undefined,
      chapters: treeData.value,
    })
    // 编辑系统模板时，后端返回新创建的个人副本 ID
    const newId = res.data?.id
    if (newId && newId !== props.templateId) {
      ElMessage.success('已创建个人副本并保存')
    } else {
      ElMessage.success('模板已保存')
    }
    emit('saved', newId || props.templateId)
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.config-table {
  border-collapse: collapse;
  font-size: 12px;
}
.config-table th, .config-table td {
  border: 1px solid #dcdfe6;
  padding: 4px 6px;
  min-width: 90px;
  text-align: center;
}
.config-table th {
  background: #f5f7fa;
}
.fixed-cell {
  background: #ecf5ff;
  cursor: pointer;
}
.fixed-cell:hover {
  background: #d9ecff;
}
</style>