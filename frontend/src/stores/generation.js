import { ref, reactive } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { generationApi } from '../api/generation'

export const useGenerationStore = defineStore('generation', () => {
  // 生成状态
  const generating = ref(false)
  const progress = ref(null)
  const chapterList = ref([])
  const generationResult = ref(null)
  const currentTaskId = ref(null)
  // 保存当前任务的原始数据，用于页面切换回来时恢复表单
  const currentTaskData = ref(null)
  let wsConnection = null

  let pollTimer = null

  function pollTaskStatus(taskId) {
    // 如果已有轮询，先清除
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
    console.log('[轮询] 开始轮询任务状态:', taskId)
    pollTimer = setInterval(async () => {
      try {
        const res = await generationApi.getTask(taskId)
        const task = res.data
        if (task.status === 'completed') {
          clearInterval(pollTimer)
          pollTimer = null
          generating.value = false
          generationResult.value = task
          const results = JSON.parse(task.chapter_results || '{}')
          // 优先使用 API 返回的 chapter_list
          if (task.chapter_list && task.chapter_list.length > 0) {
            updateChapterList(task.chapter_list, results)
          } else if (chapterList.value.length) {
            updateChapterList(chapterList.value, results)
          } else {
            chapterList.value = buildChapterListFromResults(results)
          }
          progress.value = {
            status: 'completed',
            total_chapters: task.total_chapters || 0,
            completed_chapters: task.total_chapters || 0,
            message: '文档生成完成！',
          }
          ElMessage.success('文档生成完成！')
        } else if (task.status === 'failed') {
          clearInterval(pollTimer)
          pollTimer = null
          generating.value = false
          progress.value = { status: 'failed', message: task.error_message || '生成失败' }
          ElMessage.error(task.error_message || '生成失败')
        } else {
          // 还在生成中，更新章节结果
          const results = JSON.parse(task.chapter_results || '{}')
          const completedCount = Object.values(results).filter(r => r.status === 'completed').length
          const totalChapters = task.total_chapters || 0
          // 优先使用 API 返回的 chapter_list（包含章节标题）
          if (task.chapter_list && task.chapter_list.length > 0) {
            updateChapterList(task.chapter_list, results)
          } else if (chapterList.value.length) {
            updateChapterList(chapterList.value, results)
          } else if (Object.keys(results).length > 0) {
            chapterList.value = buildChapterListFromResults(results)
          }
          progress.value = {
            status: 'generating',
            total_chapters: totalChapters,
            completed_chapters: completedCount,
            message: totalChapters > 0
              ? `正在生成... (${completedCount}/${totalChapters})`
              : '正在生成...',
            chapter_results: results,
          }
        }
      } catch (e) {
        console.error('[轮询] 获取任务状态失败', e)
      }
    }, 2000)
  }

  function connectWebSocket(taskId, initialChapters = 0) {
    // 先关闭旧连接
    if (wsConnection) {
      wsConnection.close()
      wsConnection = null
    }
    currentTaskId.value = taskId
    generating.value = true
    // 立即设置初始进度状态，确保进度条渲染
    progress.value = {
      status: 'generating',
      total_chapters: initialChapters,
      completed_chapters: 0,
      message: '正在准备生成...',
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/api/generation/${taskId}/progress`
    console.log('[WebSocket] 正在连接:', url)
    wsConnection = new WebSocket(url)

    let firstMessageReceived = false

    // 安全超时：5 秒内未收到消息则启动轮询
    const safetyTimer = setTimeout(() => {
      if (!firstMessageReceived && generating.value) {
        console.warn('[WebSocket] 5 秒内未收到消息，启动轮询回退')
        if (wsConnection) { wsConnection.close(); wsConnection = null }
        pollTaskStatus(taskId)
      }
    }, 5000)

    wsConnection.onopen = () => {
      console.log('[WebSocket] 连接成功')
    }
    wsConnection.onmessage = (event) => {
      if (!firstMessageReceived) {
        firstMessageReceived = true
        clearTimeout(safetyTimer)
      }
      const data = JSON.parse(event.data)
      console.log('[WebSocket] 收到消息:', data.status, data.total_chapters, '章节列表:', (data.chapter_list || []).length)
      if (data.type === 'ping') return
      // 如果收到非 generating 状态，说明任务已结束
      if (data.status === 'completed' || data.status === 'failed') {
        progress.value = data
        generating.value = false
        if (wsConnection) { wsConnection.close(); wsConnection = null }
        if (data.status === 'completed') {
          ElMessage.success('文档生成完成！')
          loadTaskResult(taskId)
        } else {
          ElMessage.error(data.message || '生成失败')
        }
        return
      }
      progress.value = data
      // 只有当 chapter_list 不为 null/undefined 时才更新（初始推送可能是 null）
      if (data.chapter_list && data.chapter_list.length > 0) {
        chapterList.value = (data.chapter_list || []).map(ch => ({
          ...ch,
          _status: (data.chapter_results || {})[ch.id]?.status || (ch.title_only ? 'completed' : 'pending'),
          _retrying: false,
          _retryReasons: (data.chapter_results || {})[ch.id]?.retry_reasons || [],
        }))
        console.log('[WebSocket] 章节列表已更新:', chapterList.value.length, '个章节')
      } else if (data.chapter_results && Object.keys(data.chapter_results).length > 0) {
        // 从 chapter_results 构建章节列表（fallback）
        chapterList.value = buildChapterListFromResults(data.chapter_results)
        console.log('[WebSocket] 从 chapter_results 构建章节列表:', chapterList.value.length, '个章节')
      }
    }
    wsConnection.onerror = (e) => {
      clearTimeout(safetyTimer)
      console.error('[WebSocket] 连接错误', e)
      // 连接失败时尝试通过 HTTP 轮询获取任务状态
      pollTaskStatus(taskId)
    }
    wsConnection.onclose = (e) => {
      clearTimeout(safetyTimer)
      console.log('[WebSocket] 连接关闭', e.code, e.reason)
      // 非正常关闭时尝试通过 HTTP 轮询获取任务状态
      if (e.code !== 1000 && generating.value) {
        pollTaskStatus(taskId)
      }
    }
  }

  function updateChapterList(chList, chResults) {
    if (!chList || !chList.length) {
      chapterList.value = buildChapterListFromResults(chResults || {})
      return
    }
    chapterList.value = (chList || []).map(ch => ({
      ...ch,
      _status: chResults?.[ch.id]?.status || (ch.title_only ? 'completed' : 'pending'),
      _retrying: false,
      _retryReasons: chResults?.[ch.id]?.retry_reasons || [],
    }))
  }

  function buildChapterListFromResults(results) {
    return Object.entries(results).map(([id, r]) => {
      const content = r.content || ''
      const firstLine = content.trim().split('\n')[0] || ''
      const title = firstLine.replace(/^#+\s*/, '') || id
      return {
        id,
        title: title.length > 50 ? title.slice(0, 50) + '...' : title,
        title_only: false,
        _status: r.status,
        _retrying: false,
        _retryReasons: r.retry_reasons || [],
      }
    })
  }

  async function loadTaskResult(taskId) {
    try {
      const res = await generationApi.getTask(taskId)
      generationResult.value = res.data
      const results = JSON.parse(res.data.chapter_results || '{}')
      // 优先使用 API 返回的 chapter_list
      if (res.data.chapter_list && res.data.chapter_list.length > 0) {
        updateChapterList(res.data.chapter_list, results)
      } else if (chapterList.value.length) {
        updateChapterList(chapterList.value, results)
      } else {
        chapterList.value = buildChapterListFromResults(results)
      }
    } catch (e) {
      console.error('加载任务结果失败', e)
    }
  }

  // 恢复已有任务（页面切换回来时调用）
  async function restoreTask(taskId) {
    currentTaskId.value = taskId
    try {
      const res = await generationApi.getTask(taskId)
      const task = res.data
      // 保存任务数据用于表单回显
      currentTaskData.value = task
      if (task.status === 'completed') {
        generating.value = false
        generationResult.value = task
        progress.value = {
          status: 'completed',
          total_chapters: task.total_chapters || 0,
          completed_chapters: task.total_chapters || 0,
          message: '文档生成完成！',
        }
        const results = JSON.parse(task.chapter_results || '{}')
        // 优先使用 API 返回的 chapter_list
        if (task.chapter_list && task.chapter_list.length > 0) {
          updateChapterList(task.chapter_list, results)
        } else if (chapterList.value.length) {
          updateChapterList(chapterList.value, results)
        } else {
          chapterList.value = buildChapterListFromResults(results)
        }
        return
      }
      if (task.status === 'failed') {
        generating.value = false
        progress.value = { status: 'failed', message: task.error_message || '生成失败' }
        return
      }
      // 任务还在进行中（generating/pending），重新连接 WebSocket
      generating.value = true
      // 加载已有的章节结果
      const results = JSON.parse(task.chapter_results || '{}')
      const completedCount = Object.values(results).filter(r => r.status === 'completed').length
      // 优先使用 API 返回的 chapter_list
      if (task.chapter_list && task.chapter_list.length > 0) {
        updateChapterList(task.chapter_list, results)
      } else if (chapterList.value.length) {
        updateChapterList(chapterList.value, results)
      } else if (Object.keys(results).length > 0) {
        chapterList.value = buildChapterListFromResults(results)
      }
      progress.value = {
        status: 'generating',
        total_chapters: task.total_chapters || 0,
        completed_chapters: completedCount,
        message: task.total_chapters > 0
          ? `正在恢复生成... (${completedCount}/${task.total_chapters})`
          : '正在恢复生成...',
      }
      connectWebSocket(taskId, task.total_chapters || 0)
    } catch (e) {
      generating.value = false
      console.error('恢复任务失败', e)
    }
  }

  function reset() {
    generating.value = false
    progress.value = null
    chapterList.value = []
    generationResult.value = null
    currentTaskId.value = null
    currentTaskData.value = null
    if (wsConnection) {
      wsConnection.close()
      wsConnection = null
    }
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  return {
    generating, progress, chapterList, generationResult, currentTaskId, currentTaskData,
    connectWebSocket, restoreTask, reset, loadTaskResult,
  }
})