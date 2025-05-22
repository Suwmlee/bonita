<template>
  <p class="text-xl mb-6">
    {{ t('pages.logs.title') }}
  </p>
  <v-card class="logs-card" elevation="10">
    <v-card-title class="d-flex justify-space-between align-center">
      <div></div>
      <div class="d-flex refresh-controls">
        <v-switch v-model="autoScroll" :label="t('pages.logs.autoScroll')" hide-details color="primary" />
        <v-btn variant="outlined" color="primary" class="action-btn mx-2"
          @click="reconnectWebSocket">
          <v-icon start>mdi-refresh</v-icon>
          {{ t('pages.logs.reconnect') }}
        </v-btn>
        <v-btn v-if="isAdmin" variant="outlined" color="error" class="action-btn"
          @click="clearLogs">
          <v-icon start>mdi-delete</v-icon>{{ t('pages.logs.clear') }}
        </v-btn>
      </div>
    </v-card-title>

    <v-card-text>
      <v-alert color="info" icon="mdi-information" variant="tonal" class="mb-3"
        v-if="wsConnectionStatus !== 'connected'">
        {{ wsConnectionStatus === 'connecting' ? t('pages.logs.connecting') : t('pages.logs.disconnected') }}
      </v-alert>

      <!-- 文本形式的日志查看器 -->
      <div ref="logsContainer" class="logs-container">
        <div v-if="logStore.logs.length === 0" class="no-logs-message">
          {{ t('pages.logs.noLogs') }}
        </div>
        <div v-else class="logs-text-view">
          <div v-for="(log, index) in logStore.logs" :key="index" class="log-entry" :class="getLogClass(log.level)">
            <span class="log-timestamp">{{ formatTimestamp(log.timestamp) }}</span>
            <span class="log-level" :class="getLevelClass(log.level)">{{ log.level ? log.level.toUpperCase()
              : 'UNKNOWN' }}</span>
            <span class="log-module">[{{ log.module || 'unknown' }}]</span>
            <div class="log-message">{{ log.message || t('common.unknown') }}</div>
          </div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { useLogStore } from "@/stores/log.store"
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

const { t, locale } = useI18n()
const isAdmin = true
const logStore = useLogStore() // 使用日志存储

// WebSocket连接
const wsConnection = ref<WebSocket | null>(null)
const wsConnectionStatus = ref("disconnected") // 'disconnected', 'connecting', 'connected'
const logsContainer = ref<HTMLElement | null>(null)
const autoScroll = ref(true)

// 解析特殊格式的时间戳
const parseTimestamp = (timestamp: string): Date | null => {
  if (!timestamp) return null

  try {
    // 处理特殊格式：2025-05-22 11:19:05,302
    // 将逗号替换为点，使其成为标准的 ISO 格式
    let processedTimestamp = timestamp
    if (timestamp.includes(",")) {
      processedTimestamp = timestamp.replace(",", ".")
    }

    // 如果时间戳不是 ISO 格式，进行转换
    if (!processedTimestamp.includes("T") && processedTimestamp.includes(" ")) {
      // 假设格式为 "YYYY-MM-DD HH:MM:SS.sss"
      processedTimestamp = processedTimestamp.replace(" ", "T")
    }

    const date = new Date(processedTimestamp)

    // 检查转换后的日期是否有效
    if (Number.isNaN(date.getTime())) {
      return null
    }

    return date
  } catch (error) {
    console.error("时间戳解析错误:", error, "timestamp:", timestamp)
    return null
  }
}

// 格式化时间戳
const formatTimestamp = (timestamp: string) => {
  try {
    // 使用解析函数
    const date = parseTimestamp(timestamp)

    // 如果解析失败，直接返回原始时间戳
    if (!date) {
      return timestamp
    }

    // 使用当前语言环境
    const currentLocale = locale.value || "zh-CN"
    return new Intl.DateTimeFormat(currentLocale, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(date)
  } catch (error) {
    console.error("时间格式化错误:", error, "timestamp:", timestamp)
    return timestamp // 发生错误时返回原始时间戳字符串
  }
}

// 获取日志级别对应的颜色类名
const getLevelClass = (level: string) => {
  const levelClasses: Record<string, string> = {
    debug: "level-debug",
    info: "level-info",
    warning: "level-warning",
    error: "level-error",
    critical: "level-critical",
  }
  return levelClasses[level?.toLowerCase()] || "level-unknown"
}

// 获取整行日志的类名
const getLogClass = (level: string) => {
  const logClasses: Record<string, string> = {
    error: "log-error",
    critical: "log-critical",
  }
  return logClasses[level?.toLowerCase()] || ""
}

// 清空日志
const clearLogs = () => {
  logStore.clearLogs()
}

// 处理WebSocket消息
const handleWebSocketMessage = (event: MessageEvent) => {
  try {
    const data = JSON.parse(event.data)

    // 使用store方法处理日志
    logStore.handleWebSocketLogs(data)

    // 下一个tick后滚动到底部
    if (autoScroll.value) {
      nextTick(() => {
        scrollToBottom()
      })
    }
  } catch (error) {
    console.error("解析WebSocket消息失败", error)
  }
}

// 滚动到底部
const scrollToBottom = () => {
  if (logsContainer.value) {
    logsContainer.value.scrollTop = logsContainer.value.scrollHeight
  }
}

// 创建WebSocket连接
const createWebSocketConnection = () => {
  // 关闭已有连接
  closeWebSocketConnection()

  // 获取token
  const token = localStorage.getItem("access_token")
  if (!token) {
    console.error("创建WebSocket连接失败：未找到认证token")
    return
  }

  wsConnectionStatus.value = "connecting"

  // 构建WebSocket地址
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
  const host = import.meta.env.VITE_API_URL
    ? new URL(import.meta.env.VITE_API_URL).host
    : window.location.host

  // 构建WebSocket URL (不再添加过滤参数)
  const wsUrl = `${protocol}//${host}/api/v1/ws/logs?token=${token}`

  // 创建WebSocket连接
  try {
    wsConnection.value = new WebSocket(wsUrl)

    // 设置事件处理器
    wsConnection.value.onmessage = handleWebSocketMessage
    wsConnection.value.onopen = () => {
      console.log("WebSocket连接已建立")
      wsConnectionStatus.value = "connected"
      // 清空现有日志，只显示实时日志
      logStore.logs = []
    }
    wsConnection.value.onerror = (error) => {
      console.error("WebSocket错误", error)
      wsConnectionStatus.value = "disconnected"
    }
    wsConnection.value.onclose = () => {
      console.log("WebSocket连接已关闭")
      wsConnectionStatus.value = "disconnected"
    }
  } catch (error) {
    console.error("创建WebSocket连接失败", error)
    wsConnectionStatus.value = "disconnected"
  }
}

// 关闭WebSocket连接
const closeWebSocketConnection = () => {
  if (
    wsConnection.value &&
    wsConnection.value.readyState !== WebSocket.CLOSED
  ) {
    wsConnection.value.close()
    wsConnection.value = null
  }
  wsConnectionStatus.value = "disconnected"
}

// 重新连接WebSocket
const reconnectWebSocket = () => {
  logStore.logs = [] // 清空现有日志
  createWebSocketConnection()
}

// 生命周期钩子
onMounted(() => {
  createWebSocketConnection()
})

onBeforeUnmount(() => {
  // 组件卸载前关闭WebSocket连接
  closeWebSocketConnection()
})

// 监听自动滚动切换
watch(autoScroll, (newValue) => {
  if (newValue) {
    nextTick(() => {
      scrollToBottom()
    })
  }
})
</script>

<style scoped>
.logs-card {
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.logs-container {
  height: calc(100vh - 200px);
  overflow-y: auto;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 4px;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 14px;
}

/* 调整卡片内容区域的内边距 */
:deep(.v-card-text) {
  padding-bottom: 8px;
}

/* 文本形式的日志样式 */
.logs-text-view {
  padding: 4px;
  padding-bottom: 0;
}

.log-entry {
  padding: 4px 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  white-space: pre-wrap;
  word-break: break-word;
  cursor: default;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.log-entry:hover {
  background-color: rgba(0, 0, 0, 0.03);
}

.log-timestamp {
  color: #555;
  margin-right: 8px;
  white-space: nowrap;
}

.log-level {
  font-weight: bold;
  padding: 1px 4px;
  border-radius: 3px;
  margin-right: 8px;
  white-space: nowrap;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  height: 20px;
}

.level-debug {
  color: #607d8b;
}

.level-info {
  color: #0288d1;
}

.level-warning {
  color: #ef6c00;
}

.level-error {
  color: #d32f2f;
}

.level-critical {
  color: #6a1b9a;
}

.level-unknown {
  color: #616161;
}

.log-module {
  color: #2e7d32;
  margin-right: 8px;
  white-space: nowrap;
}

.log-message {
  flex: 1;
  min-width: 50%;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 2px 0;
}

/* 无日志时的提示 */
.no-logs-message {
  padding: 16px;
  text-align: center;
  color: #757575;
}

/* 搜索和筛选控件样式 */
.search-input {
  max-width: 350px;
  min-width: 250px;
}

.filter-select {
  max-width: 200px;
  min-width: 150px;
}

.module-input {
  max-width: 200px;
  min-width: 150px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .logs-card {
    height: auto;
    min-height: calc(100vh - 150px);
  }

  .logs-container {
    height: 60vh;
  }

  .search-input,
  .filter-select,
  .module-input {
    min-width: 0;
    width: 100%;
  }

  .action-btn {
    margin-top: 8px;
    width: 100%;
  }

  .refresh-controls {
    flex-wrap: wrap;
  }

  .log-entry {
    flex-direction: column;
  }

  .log-timestamp,
  .log-level,
  .log-module {
    margin-bottom: 4px;
  }
}

/* 刷新控件样式 */
.refresh-controls {
  white-space: nowrap;
  gap: 8px;
  display: flex;
}

/* 按钮样式通用调整 */
.action-btn {
  white-space: nowrap;
  min-width: 100px;
}
</style>