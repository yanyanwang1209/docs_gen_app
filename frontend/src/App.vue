<template>
  <div id="app">
    <el-container style="min-height: 100vh">
      <!-- 侧边栏 -->
      <el-aside width="220px" style="background: #304156">
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
          style="border-right: none"
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
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-container>
        <el-main style="background: #f0f2f5; padding: 24px; min-height: 100vh">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const currentRoute = computed(() => route.hash ? route.hash.slice(1) : route.path)
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