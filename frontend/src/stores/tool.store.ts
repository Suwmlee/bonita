import { ToolsService } from "@/client"
import type {
  ScrapinglibVersion,
  SyncDirection,
  ToolArgsParam,
  TransRecordsPathSyncParam,
} from "@/client"
import { i18n } from "@/plugins/i18n"
import { defineStore } from "pinia"
import { useTaskStore } from "./task.store"
import { useToastStore } from "./toast.store"

export const useToolStore = defineStore("tool-store", {
  state: () => ({
    importNfoInProgress: false,
    syncEmbyInProgress: false,
    syncPlexInProgress: false,
    syncActorEmbyPhotosInProgress: false,
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

    async _runWatchSync(options: {
      progressKey: "syncEmbyInProgress" | "syncPlexInProgress"
      failKey: string
      okKey: string
      logLabel: string
      start: () => Promise<{ data: { task_id?: string } | null }>
    }) {
      this[options.progressKey] = true
      try {
        const toastStore = useToastStore()
        const taskStore = useTaskStore()
        const { data: task } = await options.start()
        if (!task?.task_id) {
          toastStore.error(i18n.global.t(options.failKey) as string)
          return task
        }
        const finished = await taskStore.waitForTask(task.task_id)
        if (finished?.status === "FAILURE" || finished?.status === "REVOKED") {
          toastStore.error(
            finished.error_message
              || (i18n.global.t(options.failKey) as string),
          )
          return finished
        }
        toastStore.success(i18n.global.t(options.okKey) as string)
        return finished || task
      } catch (error) {
        console.error(`Error syncing ${options.logLabel} watch history:`, error)
        useToastStore().error(
          error instanceof Error
            ? error.message
            : (i18n.global.t(options.failKey) as string),
        )
      } finally {
        this[options.progressKey] = false
      }
    },

    async syncEmbyWatchHistory(direction: SyncDirection = "from_server", force = false) {
      return this._runWatchSync({
        progressKey: "syncEmbyInProgress",
        failKey: "pages.tools.embyFailed",
        okKey: "pages.tools.embySuccess",
        logLabel: "Emby",
        start: () => ToolsService.syncEmbyWatchHistory({
          watchSyncParam: { direction, force, sources: ["emby"] },
        }),
      })
    },

    async syncPlexWatchHistory(direction: SyncDirection = "from_server", force = false) {
      return this._runWatchSync({
        progressKey: "syncPlexInProgress",
        failKey: "pages.tools.plexFailed",
        okKey: "pages.tools.plexSuccess",
        logLabel: "Plex",
        start: () => ToolsService.syncPlexWatchHistory({
          watchSyncParam: { direction, force },
        }),
      })
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

    async tidyActors() {
      try {
        const toastStore = useToastStore()
        const { data: response } = await ToolsService.tidyActors()
        const detail = response?.data as
          | {
              actors?: number
              credits?: number
              removed?: number
              created?: number
            }
          | undefined
        toastStore.success(
          i18n.global.t("pages.tools.tidyActors.success", {
            actors: detail?.actors ?? 0,
            credits: detail?.credits ?? 0,
            removed: detail?.removed ?? 0,
          }) as string,
        )
        return response
      } catch (error) {
        console.error("Error tidying actors:", error)
        const toastStore = useToastStore()
        toastStore.error(
          error instanceof Error
            ? error.message
            : (i18n.global.t("pages.tools.tidyActors.failed") as string),
        )
      }
    },

    async syncActorEmbyPhotos(force = false) {
      this.syncActorEmbyPhotosInProgress = true
      try {
        const toastStore = useToastStore()
        const taskStore = useTaskStore()
        const { data: task } = await ToolsService.syncActorEmbyPhotos({
          embyActorPhotoSyncParam: { force },
        })
        if (!task?.task_id) {
          toastStore.error(i18n.global.t("pages.tools.syncActorEmbyPhotos.failed") as string)
          return task
        }
        // 下载头像可能很慢，不在工具页空轮询；进度看仪表盘 / 日志
        taskStore.addOrUpdateRunningTask(task)
        toastStore.success(i18n.global.t("pages.tools.syncActorEmbyPhotos.started") as string)
        return task
      } catch (error) {
        console.error("Error syncing actor photos to Emby:", error)
        const toastStore = useToastStore()
        toastStore.error(
          error instanceof Error
            ? error.message
            : (i18n.global.t("pages.tools.syncActorEmbyPhotos.failed") as string),
        )
      } finally {
        this.syncActorEmbyPhotosInProgress = false
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
    isSyncPlexInProgress: (state) => state.syncPlexInProgress,
    isSyncActorEmbyPhotosInProgress: (state) => state.syncActorEmbyPhotosInProgress,
    isCleaningInProgress: (state) => state.cleaningInProgress,
  },
})
