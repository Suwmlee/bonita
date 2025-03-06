import { ToolsService } from "@/client"
import type { RunImportNfoResponse, ToolArgsParam } from "@/client/types.gen"
import { defineStore } from "pinia"
import { useToastStore } from "./toast.store"
import { useTaskStore } from "./task.store"

export const useToolStore = defineStore("tool-store", {
  state: () => ({
    importNfoInProgress: false,
  }),
  actions: {
    async runImportNfo(params: ToolArgsParam = {}) {
      try {
        const toastStore = useToastStore()
        const taskStore = useTaskStore()

        const response: RunImportNfoResponse = await ToolsService.runImportNfo({
          requestBody: params
        })
        // Check status
        if (!response || response.status === 'FAILED') {
          toastStore.error(`NFO导入失败: ${response.detail || '未知错误'}`)
        } else {
          toastStore.success("开始导入NFO信息")
          taskStore.addOrUpdateRunningTask(response)
        }
        return response
      } catch (error) {
        console.error("Error importing NFO:", error)
        const toastStore = useToastStore()
        toastStore.error(error instanceof Error ? error.message : "NFO导入失败: 未知错误")
      }
    },
  },
  getters: {
    isImportNfoInProgress: (state) => state.importNfoInProgress,
  }
})
