<template>
  <div class="logs-page">
    <div class="d-flex align-center justify-space-between flex-wrap gap-2 mb-4">
      <p class="text-xl mb-0">
        {{ t('pages.logs.title') }}
      </p>
      <VChip :color="connectionColor" size="small" variant="tonal">
        <VIcon start size="16">{{ connectionIcon }}</VIcon>
        {{ connectionLabel }}
      </VChip>
    </div>

    <VCard class="logs-card" elevation="10">
      <div class="logs-toolbar">
        <div class="logs-filters">
          <VTextField
            v-model="searchQuery"
            :placeholder="t('pages.logs.search')"
            prepend-inner-icon="mdi-magnify"
            clearable
            hide-details
            density="comfortable"
            class="search-input"
          />
          <VSelect
            v-model="levelFilter"
            :items="levelOptions"
            item-title="title"
            item-value="value"
            hide-details
            density="comfortable"
            class="filter-select"
          />
          <VSelect
            v-model="moduleFilter"
            :items="moduleOptions"
            item-title="title"
            item-value="value"
            hide-details
            density="comfortable"
            class="module-input"
          />
        </div>

        <div class="logs-actions">
          <VSwitch
            v-model="autoScroll"
            :label="t('pages.logs.autoScroll')"
            hide-details
            color="primary"
            density="compact"
            class="auto-scroll-switch"
          />

          <VTooltip :text="isPaused ? t('pages.logs.resume') : t('pages.logs.pause')">
            <template #activator="{ props }">
              <VBtn
                v-bind="props"
                icon
                variant="text"
                size="small"
                :color="isPaused ? 'warning' : undefined"
                @click="togglePause"
              >
                <VIcon>{{ isPaused ? 'mdi-play' : 'mdi-pause' }}</VIcon>
              </VBtn>
            </template>
          </VTooltip>

          <VTooltip :text="t('pages.logs.reconnect')">
            <template #activator="{ props }">
              <VBtn
                v-bind="props"
                icon
                variant="text"
                size="small"
                :loading="wsStatus === 'CONNECTING'"
                :disabled="wsStatus === 'CONNECTING'"
                @click="reconnectWebSocket"
              >
                <VIcon>mdi-refresh</VIcon>
              </VBtn>
            </template>
          </VTooltip>

          <VTooltip :text="t('pages.logs.copy')">
            <template #activator="{ props }">
              <VBtn
                v-bind="props"
                icon
                variant="text"
                size="small"
                :disabled="!filteredLogs.length"
                @click="copyLogs"
              >
                <VIcon>mdi-content-copy</VIcon>
              </VBtn>
            </template>
          </VTooltip>

          <VTooltip :text="t('pages.logs.download')">
            <template #activator="{ props }">
              <VBtn
                v-bind="props"
                icon
                variant="text"
                size="small"
                :disabled="!filteredLogs.length"
                @click="downloadLogs"
              >
                <VIcon>mdi-download</VIcon>
              </VBtn>
            </template>
          </VTooltip>

          <VTooltip :text="t('pages.logs.clear')">
            <template #activator="{ props }">
              <VBtn
                v-bind="props"
                icon
                variant="text"
                size="small"
                color="error"
                :disabled="!logStore.logs.length"
                @click="clearLogs"
              >
                <VIcon>mdi-delete</VIcon>
              </VBtn>
            </template>
          </VTooltip>
        </div>
      </div>

      <VAlert
        v-if="wsStatus !== 'OPEN'"
        :color="wsStatus === 'CONNECTING' ? 'info' : 'warning'"
        :icon="wsStatus === 'CONNECTING' ? 'mdi-information' : 'mdi-alert'"
        variant="tonal"
        density="compact"
        class="mx-4 mb-3"
      >
        {{ wsStatus === 'CONNECTING' ? t('pages.logs.connecting') : t('pages.logs.disconnected') }}
      </VAlert>

      <VAlert
        v-if="logStore.liveOnly"
        color="info"
        icon="mdi-filter-minus"
        variant="tonal"
        density="compact"
        class="mx-4 mb-3"
      >
        <div class="d-flex align-center flex-wrap justify-space-between gap-2">
          <span>{{ t('pages.logs.clearedHint') }}</span>
          <VBtn
            size="small"
            variant="text"
            prepend-icon="mdi-history"
            @click="loadHistory"
          >
            {{ t('pages.logs.loadHistory') }}
          </VBtn>
        </div>
      </VAlert>

      <div
        ref="logsContainer"
        class="logs-container"
        @scroll="onLogsScroll"
      >
        <div v-if="!sourceLogs.length" class="no-logs-message">
          {{ t('pages.logs.noLogs') }}
        </div>
        <div v-else-if="!filteredLogs.length" class="no-logs-message">
          {{ t('pages.logs.noMatchingLogs') }}
        </div>
        <div v-else class="logs-text-view">
          <div
            v-for="log in filteredLogs"
            :key="log.id"
            class="log-entry"
            :class="getLogClass(log.level)"
          >
            <span class="log-timestamp">{{ log.timestamp || '-' }}</span>
            <span class="log-level" :class="getLevelClass(log.level)">
              {{ log.level ? log.level.toUpperCase() : 'UNKNOWN' }}
            </span>
            <span class="log-module">[{{ log.module || 'unknown' }}]</span>
            <div class="log-message">{{ log.message || t('common.unknown') }}</div>
          </div>
        </div>
      </div>

      <div class="logs-footer">
        <span class="text-caption text-medium-emphasis">
          {{
            hasActiveFilters
              ? t('pages.logs.filteredCount', { shown: filteredLogs.length, total: sourceLogs.length })
              : t('pages.logs.totalItems', { count: sourceLogs.length })
          }}
        </span>
        <div class="d-flex align-center gap-2">
          <VChip v-if="isPaused" color="warning" size="x-small" variant="tonal">
            {{ t('pages.logs.paused') }}{{ newLogCount ? ` · ${t('pages.logs.newLogs', { count: newLogCount })}` : '' }}
          </VChip>
          <VBtn
            v-if="!isNearBottom || isPaused"
            variant="text"
            size="small"
            prepend-icon="mdi-arrow-down"
            @click="jumpToLatest"
          >
            {{ t('pages.logs.jumpToLatest') }}
          </VBtn>
        </div>
      </div>
    </VCard>
  </div>
</template>

<script setup lang="ts">
import { useConfirmationStore } from "@/stores/confirmation.store"
import type { LogEntry } from "@/stores/log.store"
import { useLogStore } from "@/stores/log.store"
import { useToastStore } from "@/stores/toast.store"
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

type WsStatus = "CONNECTING" | "OPEN" | "CLOSED"

const { t } = useI18n()
const logStore = useLogStore()
const toastStore = useToastStore()
const confirmationStore = useConfirmationStore()

const logsContainer = ref<HTMLElement | null>(null)
const autoScroll = ref(true)
const isNearBottom = ref(true)
const searchQuery = ref("")
const levelFilter = ref("")
const moduleFilter = ref("")
const pausedSnapshot = ref<LogEntry[] | null>(null)
const pingTimer = ref<number | null>(null)

const isPaused = computed(() => pausedSnapshot.value !== null)

const sourceLogs = computed(() => pausedSnapshot.value ?? logStore.logs)

const hasActiveFilters = computed(() =>
  Boolean(searchQuery.value.trim() || levelFilter.value || moduleFilter.value),
)

const newLogCount = computed(() => {
  const snapshot = pausedSnapshot.value
  if (!snapshot?.length) {
    return snapshot ? logStore.logs.length : 0
  }
  const lastId = snapshot[snapshot.length - 1].id
  return logStore.logs.reduce(
    (count, log) => (log.id > lastId ? count + 1 : count),
    0,
  )
})

const levelOptions = computed(() => [
  { title: t("pages.logs.levelAll"), value: "" },
  { title: "DEBUG", value: "debug" },
  { title: "INFO", value: "info" },
  { title: "WARNING", value: "warning" },
  { title: "ERROR", value: "error" },
  { title: "CRITICAL", value: "critical" },
])

const moduleOptions = computed(() => {
  const names = new Set(logStore.modules)
  if (moduleFilter.value) names.add(moduleFilter.value)
  return [
    { title: t("pages.logs.moduleAll"), value: "" },
    ...[...names]
      .sort((a, b) => a.localeCompare(b))
      .map((name) => ({
        title: name,
        value: name,
      })),
  ]
})

const filteredLogs = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  const level = levelFilter.value
  const moduleName = moduleFilter.value

  return sourceLogs.value.filter((log) => {
    if (level && log.level !== level) return false
    if (moduleName && log.module !== moduleName) return false
    if (keyword) {
      const haystack =
        `${log.message} ${log.module} ${log.timestamp}`.toLowerCase()
      if (!haystack.includes(keyword)) return false
    }
    return true
  })
})

function getLogsWebSocketUrl(): string | undefined {
  const token = localStorage.getItem("access_token")
  if (!token) return undefined

  try {
    const base = import.meta.env.VITE_API_URL || window.location.origin
    const url = new URL(base, window.location.origin)
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:"
    url.pathname = "/api/v1/ws/logs"
    url.searchParams.set("token", token)
    url.searchParams.set("history", logStore.liveOnly ? "false" : "true")
    if (levelFilter.value) {
      url.searchParams.set("level", levelFilter.value)
    }
    return url.toString()
  } catch (error) {
    console.error("构建WebSocket地址失败", error)
    return undefined
  }
}

const wsStatus = ref<WsStatus>("CLOSED")
const wsConnection = ref<WebSocket | null>(null)
let connectionId = 0
let reconnectTimer: number | null = null
let pageActive = true

const clearReconnectTimer = () => {
  if (reconnectTimer !== null) {
    window.clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
}

const disposeSocket = () => {
  const ws = wsConnection.value
  if (!ws) return
  ws.onopen = null
  ws.onclose = null
  ws.onerror = null
  ws.onmessage = null
  if (
    ws.readyState === WebSocket.CONNECTING ||
    ws.readyState === WebSocket.OPEN
  ) {
    ws.close()
  }
  wsConnection.value = null
}

const connectionColor = computed(() => {
  if (wsStatus.value === "OPEN") return "success"
  if (wsStatus.value === "CONNECTING") return "info"
  return "warning"
})

const connectionIcon = computed(() => {
  if (wsStatus.value === "OPEN") return "mdi-lan-connect"
  if (wsStatus.value === "CONNECTING") return "mdi-lan-pending"
  return "mdi-lan-disconnect"
})

const connectionLabel = computed(() => {
  if (wsStatus.value === "OPEN") return t("pages.logs.connected")
  if (wsStatus.value === "CONNECTING") return t("pages.logs.connecting")
  return t("pages.logs.disconnected")
})

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

const getLogClass = (level: string) => {
  const logClasses: Record<string, string> = {
    warning: "log-warning",
    error: "log-error",
    critical: "log-critical",
  }
  return logClasses[level?.toLowerCase()] || ""
}

const formatLogLine = (log: LogEntry) => {
  const level = log.level ? log.level.toUpperCase() : "UNKNOWN"
  const moduleName = log.module || "unknown"
  return `${log.timestamp || "-"} ${level} [${moduleName}] ${log.message}`
}

const shouldAutoScroll = () => {
  return autoScroll.value && isNearBottom.value && !isPaused.value
}

const scrollToBottom = () => {
  const el = logsContainer.value
  if (!el) return
  el.scrollTop = el.scrollHeight
  isNearBottom.value = true
}

const onLogsScroll = () => {
  const el = logsContainer.value
  if (!el) return
  const threshold = 80
  isNearBottom.value =
    el.scrollHeight - el.scrollTop - el.clientHeight <= threshold
}

const handleWebSocketMessage = (event: MessageEvent | { data: unknown }) => {
  try {
    const raw = typeof event.data === "string" ? event.data : ""
    if (!raw || raw === "ping" || raw === "pong") return
    const data = JSON.parse(raw)
    const isSnapshot = data && Array.isArray(data.logs)
    if (!isSnapshot && levelFilter.value) {
      let incomingLevel = String(data.level || "").toLowerCase()
      if (incomingLevel === "warn") incomingLevel = "warning"
      if (incomingLevel !== levelFilter.value) return
    }
    logStore.handleWebSocketLogs(data)
    if (shouldAutoScroll()) {
      nextTick(() => {
        scrollToBottom()
      })
    }
  } catch (error) {
    console.error("解析WebSocket消息失败", error)
  }
}

const togglePause = () => {
  if (pausedSnapshot.value) {
    pausedSnapshot.value = null
    nextTick(() => {
      if (autoScroll.value) scrollToBottom()
    })
    return
  }
  pausedSnapshot.value = logStore.logs.slice()
}

const jumpToLatest = () => {
  pausedSnapshot.value = null
  autoScroll.value = true
  nextTick(() => {
    scrollToBottom()
  })
}

const stopPing = () => {
  if (pingTimer.value !== null) {
    window.clearInterval(pingTimer.value)
    pingTimer.value = null
  }
}

const scheduleReconnect = () => {
  if (!pageActive) return
  clearReconnectTimer()
  reconnectTimer = window.setTimeout(() => {
    createWebSocketConnection()
  }, 3000)
}

const createWebSocketConnection = () => {
  if (!pageActive) return

  const url = getLogsWebSocketUrl()
  if (!url) {
    wsStatus.value = "CLOSED"
    return
  }

  const currentId = ++connectionId
  stopPing()
  disposeSocket()
  clearReconnectTimer()
  wsStatus.value = "CONNECTING"

  try {
    const ws = new WebSocket(url)
    wsConnection.value = ws

    ws.onopen = () => {
      if (currentId !== connectionId) return
      wsStatus.value = "OPEN"
    }
    ws.onmessage = (event) => {
      if (currentId !== connectionId) return
      handleWebSocketMessage(event)
    }
    ws.onerror = () => {
      if (currentId !== connectionId) return
      wsStatus.value = "CLOSED"
    }
    ws.onclose = () => {
      if (currentId !== connectionId) return
      wsConnection.value = null
      wsStatus.value = "CLOSED"
      stopPing()
      scheduleReconnect()
    }
  } catch (error) {
    console.error("创建WebSocket连接失败", error)
    wsStatus.value = "CLOSED"
    scheduleReconnect()
  }
}

const reconnectWebSocket = () => {
  pausedSnapshot.value = null
  createWebSocketConnection()
}

const loadHistory = () => {
  pausedSnapshot.value = null
  logStore.prepareHistoryReload()
  createWebSocketConnection()
}

const clearLogs = async () => {
  const confirmed = await confirmationStore.openConfirmation({
    title: t("pages.logs.confirmClearTitle"),
    message: t("pages.logs.confirmClearMessage"),
    confirmText: t("pages.logs.clear"),
    confirmColor: "error",
    type: "warning",
  })
  if (!confirmed) return
  pausedSnapshot.value = null
  logStore.clearLogs()
}

const copyLogs = async () => {
  const text = filteredLogs.value.map(formatLogLine).join("\n")
  try {
    await navigator.clipboard.writeText(text)
    toastStore.success(t("pages.logs.copied"))
  } catch {
    toastStore.error(t("pages.logs.copyFailed"))
  }
}

const downloadLogs = () => {
  const text = filteredLogs.value.map(formatLogLine).join("\n")
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = `bonita-logs-${stamp}.txt`
  anchor.click()
  URL.revokeObjectURL(url)
}

watch(wsStatus, (status) => {
  stopPing()
  if (status !== "OPEN") return
  pingTimer.value = window.setInterval(() => {
    if (wsConnection.value?.readyState === WebSocket.OPEN) {
      wsConnection.value.send("ping")
    }
  }, 30000)
})

watch(autoScroll, (enabled) => {
  if (enabled) {
    nextTick(() => {
      scrollToBottom()
    })
  }
})

watch(levelFilter, () => {
  if (logStore.liveOnly) return
  pausedSnapshot.value = null
  logStore.prepareHistoryReload()
  createWebSocketConnection()
})

onMounted(() => {
  createWebSocketConnection()
})

onBeforeUnmount(() => {
  pageActive = false
  connectionId += 1
  clearReconnectTimer()
  stopPing()
  disposeSocket()
})
</script>

<style scoped>
.logs-page {
  display: flex;
  flex-direction: column;
  /* 100dvh minus navbar 64px, floating offset 1rem, page padding 3rem */
  height: calc(100dvh - 64px - 1rem - 3rem);
  overflow: hidden;
}

.logs-card {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.logs-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
}

.logs-filters {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.logs-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.auto-scroll-switch {
  margin-inline-end: 8px;
}

.logs-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  margin-inline: 16px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  background: rgba(var(--v-theme-on-surface), 0.03);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, 'Courier New', monospace;
  font-size: 13px;
}

.logs-text-view {
  padding: 4px;
}

.log-entry {
  display: grid;
  grid-template-columns: 11.5rem 5.5rem minmax(7rem, 12rem) 1fr;
  gap: 8px;
  align-items: start;
  padding: 4px 8px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  white-space: pre-wrap;
  word-break: break-word;
}

.log-entry:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.04);
}

.log-timestamp {
  color: rgba(var(--v-theme-on-surface), 0.55);
  white-space: nowrap;
}

.log-level {
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
  white-space: nowrap;
  font-size: 12px;
  line-height: 20px;
  text-align: center;
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
  color: rgb(var(--v-theme-success));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-message {
  min-width: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.log-warning {
  background-color: rgba(var(--v-theme-warning), 0.08);
}

.log-error {
  background-color: rgba(var(--v-theme-error), 0.08);
}

.log-critical {
  background-color: rgba(106, 27, 154, 0.12);
}

.no-logs-message {
  padding: 24px 16px;
  text-align: center;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.logs-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 16px 12px;
}

.search-input {
  max-width: 350px;
  min-width: 220px;
  flex: 1;
}

.filter-select,
.module-input {
  max-width: 200px;
  min-width: 140px;
}

@media (max-width: 768px) {
  .search-input,
  .filter-select,
  .module-input {
    min-width: 0;
    max-width: none;
    width: 100%;
  }

  .log-entry {
    grid-template-columns: 1fr;
    gap: 2px;
  }

  .log-timestamp,
  .log-level,
  .log-module {
    white-space: normal;
  }
}
</style>
