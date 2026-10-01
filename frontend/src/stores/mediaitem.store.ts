import {
  type MediaItemCreate,
  type MediaItemWithWatches,
  MediaitemService,
} from "@/client"
import { client } from "@/client/client.gen"
import { i18n } from "@/plugins/i18n"
import { defineStore } from "pinia"
import { useCollectionStore } from "./collection.store"
import { useConfirmationStore } from "./confirmation.store"
import { useToastStore } from "./toast.store"

const ITEMS_PER_PAGE_KEY = "mediaitem-items-per-page"
const ITEMS_PER_PAGE_OPTIONS = [20, 30, 40, 80]
const DEFAULT_ITEMS_PER_PAGE = 40

function loadItemsPerPage(): number {
  const parsed = Number.parseInt(
    localStorage.getItem(ITEMS_PER_PAGE_KEY) ?? "",
    10,
  )
  return ITEMS_PER_PAGE_OPTIONS.includes(parsed)
    ? parsed
    : DEFAULT_ITEMS_PER_PAGE
}

export const useMediaItemStore = defineStore("mediaitem-store", {
  state: () => ({
    allMediaItems: [] as MediaItemWithWatches[],
    showDialog: false,
    editMediaItem: undefined as MediaItemWithWatches | undefined,
    addDraft: undefined as Partial<MediaItemWithWatches> | undefined,
    dialogHistory: [] as MediaItemWithWatches[],
    totalCount: 0,
    currentPage: 1,
    itemsPerPage: loadItemsPerPage(),
    isLoading: false,
  }),
  actions: {
    // Get media items with optional filtering
    async getMediaItems(
      search?: string,
      page?: number,
      itemsPerPage?: number,
      mediaType?: string,
      sortBy?: string,
      sortDesc?: boolean,
      hasNumber?: boolean,
      watched?: boolean,
      favorite?: boolean,
    ) {
      this.isLoading = true
      try {
        const skip =
          page !== undefined
            ? (page - 1) * (itemsPerPage || this.itemsPerPage)
            : (this.currentPage - 1) * this.itemsPerPage
        const limit =
          itemsPerPage !== undefined ? itemsPerPage : this.itemsPerPage

        const { data: response } = await MediaitemService.getMediaItems({
          search,
          skip,
          limit,
          media_type: mediaType,
          sort_by: sortBy,
          sort_desc: sortDesc,
          has_number: hasNumber,
          watched,
          favorite,
        })

        this.allMediaItems = response.data

        // Update total count
        this.totalCount = response.count

        // Update currentPage if page parameter was provided
        if (page !== undefined) {
          this.currentPage = page
        }

        // Update itemsPerPage if it was provided
        if (itemsPerPage !== undefined) {
          this.itemsPerPage = itemsPerPage
          if (ITEMS_PER_PAGE_OPTIONS.includes(itemsPerPage)) {
            localStorage.setItem(ITEMS_PER_PAGE_KEY, String(itemsPerPage))
          }
        }

        return this.allMediaItems
      } finally {
        this.isLoading = false
      }
    },

    async searchSeries(search?: string) {
      const { data: response } = await MediaitemService.getMediaItems({
        search: search || undefined,
        skip: 0,
        limit: 20,
        media_type: "series",
        sort_by: "title",
        sort_desc: false,
      })
      return response.data
    },

    // Show dialog for updating media item
    showUpdateMediaItem(data: MediaItemWithWatches) {
      this.dialogHistory = []
      this.editMediaItem = data
      this.addDraft = undefined
      this.showDialog = true
    },

    // Show dialog for adding new media item
    showAddMediaItem(draft?: Partial<MediaItemWithWatches>) {
      this.dialogHistory = []
      this.editMediaItem = undefined
      this.addDraft = draft
      this.showDialog = true
    },

    showAddEpisode(series: MediaItemWithWatches) {
      this.dialogHistory = [series]
      this.editMediaItem = undefined
      this.addDraft = {
        media_type: "episode",
        series_id: series.id,
        original_title: series.title || series.original_title || "",
        series_imdb_id: series.imdb_id,
        series_tmdb_id: series.tmdb_id,
        series_tvdb_id: series.tvdb_id,
        season_number: 1,
        episode_number: 1,
      }
      this.showDialog = true
    },

    closeDialog() {
      this.showDialog = false
      this.editMediaItem = undefined
      this.addDraft = undefined
      this.dialogHistory = []
    },

    goBackInDialog() {
      const previous = this.dialogHistory.pop()
      this.addDraft = undefined
      if (previous) {
        this.editMediaItem = previous
      }
    },

    async openParentMediaItem(seriesId: number) {
      this.isLoading = true
      try {
        const { data } = await MediaitemService.getMediaItem({
          media_id: seriesId,
        })
        if (!data) {
          const toastStore = useToastStore()
          toastStore.error(i18n.global.t("pages.mediaitem.viewParentFailed") as string)
          return
        }
        if (this.editMediaItem) {
          this.dialogHistory.push(this.editMediaItem)
        }
        this.editMediaItem = data
      } catch (error) {
        console.error("Error opening parent media item:", error)
        const toastStore = useToastStore()
        toastStore.error(i18n.global.t("pages.mediaitem.viewParentFailed") as string)
      } finally {
        this.isLoading = false
      }
    },

    // Update existing media item
    async updateMediaItem(data: MediaItemWithWatches) {
      this.isLoading = true
      try {
        const { data: mediaItem } = await MediaitemService.updateMediaItem({
          media_id: data.id,
          mediaItemUpdate: {
            media_type: data.media_type,
            title: data.title,
            original_title: data.original_title,
            number: data.number,
            imdb_id: data.imdb_id,
            tmdb_id: data.tmdb_id,
            tvdb_id: data.tvdb_id,
            season_number: data.season_number,
            episode_number: data.episode_number,
            series_id: data.series_id,
            // 观看数据字段（从 userdata 中提取）
            watched: data.userdata?.watched,
            favorite: data.userdata?.favorite,
            play_progress: data.userdata?.play_progress,
            duration: data.userdata?.duration,
            has_rating: data.userdata?.has_rating,
            user_rating: data.userdata?.user_rating,
          },
        })

        if (this.showDialog) {
          this.updateMediaItemById(data.id, mediaItem)
          this.closeDialog()

          const toastStore = useToastStore()
          toastStore.success(i18n.global.t("pages.mediaitem.updateSuccess") as string)
        }
      } catch (error) {
        console.error("Error updating media item:", error)
        const toastStore = useToastStore()
        toastStore.error(i18n.global.t("pages.mediaitem.updateFailed") as string)
      } finally {
        this.isLoading = false
      }
    },

    // Add new media item
    async addMediaItem(data: Partial<MediaItemWithWatches>) {
      this.isLoading = true
      try {
        // Create a valid MediaItemCreate object
        const mediaItemCreate: MediaItemCreate = {
          media_type: data.media_type || "movie",
          title: data.title || "",
          original_title: data.original_title,
          number: data.number,
          imdb_id: data.imdb_id,
          tmdb_id: data.tmdb_id,
          tvdb_id: data.tvdb_id,
          season_number: data.season_number,
          episode_number: data.episode_number,
          series_id: data.series_id,
        }

        const { data: response } = await MediaitemService.createMediaItem({
          mediaItemCreate,
        })

        if (response) {
          this.allMediaItems.unshift({
            ...response,
            userdata: {
              watched: false,
            },
          })
          this.totalCount += 1
          this.closeDialog()

          const toastStore = useToastStore()
          toastStore.success(i18n.global.t("pages.mediaitem.createSuccess") as string)
        }
      } catch (error) {
        console.error("Error creating media item:", error)
        const toastStore = useToastStore()
        toastStore.error(i18n.global.t("pages.mediaitem.createFailed") as string)
      } finally {
        this.isLoading = false
      }
    },

    // Update media item by ID
    updateMediaItemById(id: number, newValue: Partial<MediaItemWithWatches>) {
      const index = this.allMediaItems.findIndex(
        (mediaItem) => mediaItem.id === id,
      )

      if (index !== -1) {
        this.allMediaItems[index] = {
          ...this.allMediaItems[index],
          ...newValue,
        }
      } else {
        console.error(`Media item with id ${id} not found.`)
      }
    },

    // Confirm delete media item
    async confirmDeleteMediaItem(id: number) {
      const confirmationStore = useConfirmationStore()
      const confirmed = await confirmationStore.confirmDelete(
        i18n.global.t("pages.mediaitem.confirmDeleteTitle") as string,
        i18n.global.t("pages.mediaitem.confirmDeleteMessage") as string,
      )

      if (confirmed) {
        await this.deleteMediaItem(id)
      }
    },

    async deleteMediaItems(ids: number[]): Promise<number[]> {
      if (ids.length === 0) return []
      this.isLoading = true
      const toastStore = useToastStore()
      const collectionStore = useCollectionStore()
      try {
        const { data } = await client.post<{ ids: number[] }>({
          responseType: "json",
          security: [{ scheme: "bearer", type: "http" }],
          url: "/api/v1/mediaitems/batch-delete",
          body: { ids },
          headers: { "Content-Type": "application/json" },
        })
        const deletedIds = data?.ids ?? []
        for (const id of deletedIds) {
          collectionStore.onMediaDeleted(id)
        }
        const failed = ids.length - deletedIds.length
        if (deletedIds.length === ids.length) {
          toastStore.success(
            i18n.global.t("pages.mediaitem.deleteManySuccess", {
              count: deletedIds.length,
            }) as string,
          )
        } else if (deletedIds.length > 0) {
          toastStore.error(
            i18n.global.t("pages.mediaitem.deleteManyPartial", {
              deleted: deletedIds.length,
              failed,
            }) as string,
          )
        } else {
          toastStore.error(i18n.global.t("pages.mediaitem.deleteManyFailed") as string)
        }
        return deletedIds
      } catch (error) {
        console.error("Error deleting media items:", error)
        toastStore.error(i18n.global.t("pages.mediaitem.deleteManyFailed") as string)
        return []
      } finally {
        this.isLoading = false
      }
    },

    // Delete media item
    async deleteMediaItem(idToRemove: number) {
      this.isLoading = true
      try {
        const { data: response } = await MediaitemService.deleteMediaItem({
          media_id: idToRemove,
        })

        if (response) {
          this.allMediaItems = this.allMediaItems.filter(
            (mediaItem) => mediaItem.id !== idToRemove,
          )
          this.totalCount = Math.max(0, this.totalCount - 1)
          useCollectionStore().onMediaDeleted(idToRemove)

          const toastStore = useToastStore()
          toastStore.success(i18n.global.t("pages.mediaitem.deleteSuccess") as string)
        }
      } catch (error) {
        console.error("Error deleting media item:", error)
        const toastStore = useToastStore()
        toastStore.error(i18n.global.t("pages.mediaitem.deleteFailed") as string)
      } finally {
        this.isLoading = false
      }
    },

    async confirmCleanMediaItems() {
      const confirmationStore = useConfirmationStore()
      const confirmed = await confirmationStore.openConfirmation({
        title: i18n.global.t("pages.mediaitem.confirmCleanTitle") as string,
        message: i18n.global.t("pages.mediaitem.confirmCleanMessage") as string,
        type: "warning",
      })
      if (!confirmed) {
        return false
      }
      return await this.cleanMediaItems()
    },

    async cleanMediaItems() {
      this.isLoading = true
      try {
        const response = await MediaitemService.cleanMediaItem()

        if (response) {
          const collectionStore = useCollectionStore()
          if (collectionStore.detail) {
            await collectionStore.loadDetail(collectionStore.detail.id)
          }

          const payload = (response.data ?? {}) as {
            duplicate_number_deleted?: number
            missing_id_deleted?: number
          }
          const toastStore = useToastStore()
          toastStore.success(
            i18n.global.t("pages.mediaitem.cleanSuccessDetail", {
              duplicates: payload.duplicate_number_deleted ?? 0,
              missing: payload.missing_id_deleted ?? 0,
            }) as string,
          )
          return true
        }
        return false
      } catch (error) {
        console.error("Error cleaning media items:", error)
        const toastStore = useToastStore()
        toastStore.error(i18n.global.t("pages.mediaitem.cleanFailed") as string)
        return false
      } finally {
        this.isLoading = false
      }
    },
  },
})
