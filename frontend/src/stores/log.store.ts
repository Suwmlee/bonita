import { defineStore } from "pinia"

// 定义日志条目类型，不再从客户端导入
interface LogEntry {
  timestamp: string
  level: string
  module: string
  message: string
}

export const useLogStore = defineStore("log-store", {
  state: () => ({
    logs: [] as LogEntry[],
  }),
  actions: {
    clearLogs() {
      // 直接清空日志，不再调用API
      this.logs = []
      return { success: true }
    },

    // 处理WebSocket接收到的日志
    handleWebSocketLogs(data: any) {
      // 检查是否为批量日志格式 (服务端返回 {logs: [...]} 格式)
      if (data.logs && Array.isArray(data.logs)) {
        // 批量添加日志
        this.logs = [...this.logs, ...data.logs]
        console.log(`批量添加了 ${data.logs.length} 条日志`)
      }
      // 单条日志处理
      else {
        this.logs = [...this.logs, data]
      }

      // 限制日志数量，避免过多导致性能问题
      if (this.logs.length > 1000) {
        this.logs = this.logs.slice(-1000)
      }
    },
  },
})
