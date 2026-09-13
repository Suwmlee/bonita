import { ToolsService } from "@/client"
import type {
  ScrapinglibVersion,
  SyncDirection,
  ToolArgsParam,
  TransRecordsPathSyncParam,
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
    scrapinglibChecking: false,
    scrapinglibUpdating: false,
    scrapinglibVersion: null as ScrapinglibVersion | null,
  }),
  actions: {
    async runImportNfo(params: ToolArgsParam = {}) {
      try {
        const toastStore = useToastStore()
        const taskStore = useTaskStore()

        const { data: response } = await ToolsService.runImportNfo({
          toolArgsParam: params,
        })
        // Check status
        if (!response || response.status === "FAILURE") {
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

    async syncEmbyWatchHistory(direction: SyncDirection = "from_server", force = false) {
      this.syncEmbyInProgress = true
      try {
        const toastStore = useToastStore()

        const { data: response } = await ToolsService.syncEmbyWatchHistory({
          embySyncParam: {
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

    async syncRecordPath(params: TransRecordsPathSyncParam) {
      try {
        const toastStore = useToastStore()

        const { data: response } = await ToolsService.syncRecordPath({
          transRecordsPathSyncParam: params,
        })
        if (response.success === false) {
          toastStore.error(
            i18n.global.t("pages.tools.syncRecordPathFailedWithDetail", {
              detail: response.message || i18n.global.t("common.unknown"),
            }) as string,
          )
        } else {
          toastStore.success(i18n.global.t("pages.tools.syncRecordPathSuccess") as string)
        }
        return response
      } catch (error) {
        console.error("Error syncing record path:", error)
        const toastStore = useToastStore()
        toastStore.error(
          error instanceof Error
            ? error.message
            : (i18n.global.t("pages.tools.syncRecordPathFailed") as string),
        )
      }
    },

    async cleanupData(forceDelete = false) {
      this.cleaningInProgress = true
      try {
        const toastStore = useToastStore()

        const { data: response } = await ToolsService.cleanupData({
          toolArgsParam: {
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

    async checkScrapinglibVersion() {
      this.scrapinglibChecking = true
      try {
        const { data } = await ToolsService.getScrapinglibVersion()
        this.scrapinglibVersion = data
        return data
      } catch (error) {
        console.error("Error checking scrapinglib version:", error)
        const toastStore = useToastStore()
        toastStore.error(
          error instanceof Error
            ? error.message
            : (i18n.global.t("pages.tools.scrapinglib.checkFailed") as string),
        )
      } finally {
        this.scrapinglibChecking = false
      }
    },

    async updateScrapinglib() {
      this.scrapinglibUpdating = true
      try {
        const toastStore = useToastStore()
        const { data } = await ToolsService.updateScrapinglib()
        this.scrapinglibVersion = data
        if (data?.success === false) {
          toastStore.error(
            data.message || (i18n.global.t("pages.tools.scrapinglib.updateFailed") as string),
          )
        } else {
          toastStore.success(
            data?.message || (i18n.global.t("pages.tools.scrapinglib.updateSuccess") as string),
          )
        }
        return data
      } catch (error) {
        console.error("Error updating scrapinglib:", error)
        const toastStore = useToastStore()
        toastStore.error(
          error instanceof Error
            ? error.message
            : (i18n.global.t("pages.tools.scrapinglib.updateFailed") as string),
        )
      } finally {
        this.scrapinglibUpdating = false
      }
    },
  },
  getters: {
    isImportNfoInProgress: (state) => state.importNfoInProgress,
    isSyncEmbyInProgress: (state) => state.syncEmbyInProgress,
    isCleaningInProgress: (state) => state.cleaningInProgress,
  },
})
