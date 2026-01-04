import { ToolsService } from "@/client"
import type {
  CleanupDataResponse,
  RunImportNfoResponse,
  SyncDirection,
  ToolArgsParam,
} from "@/client/types.gen"
import { i18n } from "@/plugins/i18n"
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
          toastStore.error(
            i18n.global.t("pages.tools.nfoImportFailedWithDetail", {
              detail: response.detail || i18n.global.t("common.unknown"),
            }) as string,
          )
        } else {
          toastStore.success(i18n.global.t("pages.tools.nfoImportSuccess") as string)
          taskStore.addOrUpdateRunningTask(response)
        }
        return response
      } catch (error) {
        console.error("Error importing NFO:", error)
        const toastStore = useToastStore()
        toastStore.error(
          error instanceof Error
            ? error.message
            : (i18n.global.t("pages.tools.nfoImportFailedUnknown") as string),
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
        toastStore.success(i18n.global.t("pages.tools.embySuccess") as string)
        return response
      } catch (error) {
        console.error("Error syncing Emby watch history:", error)
        const toastStore = useToastStore()
        toastStore.error(
          error instanceof Error
            ? error.message
            : (i18n.global.t("pages.tools.embyFailed") as string),
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
        toastStore.success(i18n.global.t("pages.tools.cleanupSuccess") as string)
        return response
      } catch (error) {
        console.error("Error cleaning data:", error)
        const toastStore = useToastStore()
        toastStore.error(
          error instanceof Error
            ? error.message
            : (i18n.global.t("pages.tools.cleanupFailed") as string),
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
