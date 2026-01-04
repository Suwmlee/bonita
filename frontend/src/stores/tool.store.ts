import { ToolsService } from "@/client"
import type {
  CleanupDataResponse,
  RunImportNfoResponse,
  SyncDirection,
  ToolArgsParam,
} from "@/client/types.gen"
import { defineStore } from "pinia"
import { useTaskStore } from "./task.store"
import { useToastStore } from "./toast.store"

export const useToolStore = defineStore("tool-store", {
  state: () => ({
    importNfoInProgress: false,
    syncEmbyInProgress: false,
    cleaningInProgress: false,
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

    async syncEmbyWatchHistory(direction: SyncDirection = "from_emby", force = false) {
      this.syncEmbyInProgress = true
      try {
        const toastStore = useToastStore()

        const response = await ToolsService.syncEmbyWatchHistory({
          requestBody: {
            direction,
            force,
          },
        })
        toastStore.success("Emby观看历史同步成功")
        return response
      } catch (error) {
        console.error("Error syncing Emby watch history:", error)
        const toastStore = useToastStore()
        toastStore.error(
          error instanceof Error
            ? error.message
            : "Emby观看历史同步失败: 未知错误",
        )
      } finally {
        this.syncEmbyInProgress = false
      }
    },

    async cleanupData(forceDelete = false) {
      this.cleaningInProgress = true
      try {
        const toastStore = useToastStore()

        const response: CleanupDataResponse = await ToolsService.cleanupData({
          requestBody: {
            arg1: forceDelete ? "true" : "false",
          },
        })
        toastStore.success("清理数据成功")
        return response
      } catch (error) {
        console.error("Error cleaning data:", error)
        const toastStore = useToastStore()
        toastStore.error(
          error instanceof Error ? error.message : "清理数据失败: 未知错误",
        )
      } finally {
        this.cleaningInProgress = false
      }
    },
  },
  getters: {
    isImportNfoInProgress: (state) => state.importNfoInProgress,
    isSyncEmbyInProgress: (state) => state.syncEmbyInProgress,
    isCleaningInProgress: (state) => state.cleaningInProgress,
  },
})
