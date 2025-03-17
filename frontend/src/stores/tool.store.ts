import { ToolsService } from "@/client"
import type { RunImportNfoResponse, ToolArgsParam } from "@/client/types.gen"
import { defineStore } from "pinia"
import { useTaskStore } from "./task.store"
import { useToastStore } from "./toast.store"

export const useToolStore = defineStore("tool-store", {
  state: () => ({
    importNfoInProgress: false,
    syncEmbyInProgress: false,
  }),
  actions: {
    async runImportNfo(params: ToolArgsParam = {}) {
      try {
        const toastStore = useToastStore()
        const taskStore = useTaskStore()

        const response: RunImportNfoResponse = await ToolsService.runImportNfo({
          requestBody: params,
        })
        // Check status
        if (!response || response.status === "FAILED") {
          toastStore.error(`NFO导入失败: ${response.detail || "未知错误"}`)
        } else {
          toastStore.success("开始导入NFO信息")
          taskStore.addOrUpdateRunningTask(response)
        }
        return response
      } catch (error) {
        console.error("Error importing NFO:", error)
        const toastStore = useToastStore()
        toastStore.error(
          error instanceof Error ? error.message : "NFO导入失败: 未知错误",
        )
      }
    },
    
    async syncEmbyWatchHistory() {
      this.syncEmbyInProgress = true
      try {
        const toastStore = useToastStore()
        
        const response = await ToolsService.syncEmbyWatchHistory()
        toastStore.success("Emby观看历史同步成功")
        return response
      } catch (error) {
        console.error("Error syncing Emby watch history:", error)
        const toastStore = useToastStore()
        toastStore.error(
          error instanceof Error ? error.message : "Emby观看历史同步失败: 未知错误",
        )
      } finally {
        this.syncEmbyInProgress = false
      }
    },
  },
  getters: {
    isImportNfoInProgress: (state) => state.importNfoInProgress,
    isSyncEmbyInProgress: (state) => state.syncEmbyInProgress,
  },
})
