import { defineStore } from "pinia"

export interface LogEntry {
  id: number
  timestamp: string
  level: string
  module: string
  message: string
}

const MAX_LOG_ENTRIES = 1000

let nextLogId = 1

function normalizeLog(raw: unknown): LogEntry | null {
  if (!raw || typeof raw !== "object") return null

  const entry = raw as Record<string, unknown>
  if (entry.message == null && entry.timestamp == null && entry.level == null) {
    return null
  }

  return {
    id: nextLogId++,
    timestamp: entry.timestamp == null ? "" : String(entry.timestamp),
    level: String(entry.level ?? "unknown").toLowerCase(),
    module: String(entry.module ?? "unknown"),
    message: entry.message == null ? "" : String(entry.message),
  }
}

export const useLogStore = defineStore("log-store", {
  state: () => ({
    logs: [] as LogEntry[],
    /** 清空视图后只接收新日志，忽略服务端历史快照 */
    liveOnly: false,
  }),
  getters: {
    modules: (state) => {
      const names = new Set<string>()
      for (const log of state.logs) {
        if (log.module) names.add(log.module)
      }
      return [...names].sort((a, b) => a.localeCompare(b))
    },
  },
  actions: {
    clearLogs() {
      this.logs = []
      this.liveOnly = true
    },

    prepareHistoryReload() {
      this.logs = []
      this.liveOnly = false
    },

    handleWebSocketLogs(data: unknown) {
      const isSnapshot =
        data &&
        typeof data === "object" &&
        Array.isArray((data as { logs?: unknown }).logs)

      if (isSnapshot) {
        if (this.liveOnly) return

        const incoming: LogEntry[] = []
        for (const item of (data as { logs: unknown[] }).logs) {
          const normalized = normalizeLog(item)
          if (normalized) incoming.push(normalized)
        }
        if (!incoming.length) return
        this.logs =
          incoming.length > MAX_LOG_ENTRIES
            ? incoming.slice(-MAX_LOG_ENTRIES)
            : incoming
        return
      }

      const normalized = normalizeLog(data)
      if (!normalized) return

      if (this.logs.length >= MAX_LOG_ENTRIES) {
        this.logs.splice(0, this.logs.length - MAX_LOG_ENTRIES + 1)
      }
      this.logs.push(normalized)
    },
  },
})
