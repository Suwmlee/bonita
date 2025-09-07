import {
  type MediaItemCreate,
  type MediaItemInDB,
  type MediaItemWithWatches,
  MediaitemService,
} from "@/client"
import { defineStore } from "pinia"
import { useConfirmationStore } from "./confirmation.store"
import { useToastStore } from "./toast.store"

export const useMediaItemStore = defineStore("mediaitem-store", {
  state: () => ({
    allMediaItems: [] as MediaItemWithWatches[],
    showDialog: false,
    editMediaItem: undefined as MediaItemWithWatches | undefined,
    totalCount: 0,
    currentPage: 1,
    itemsPerPage: 40,
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

        // 使用类型断言来处理 favorite 参数
        const params: any = {
          search: search,
          skip: skip,
          limit: limit,
          mediaType: mediaType,
          sortBy: sortBy,
          sortDesc: sortDesc,
          hasNumber: hasNumber,
          watched: watched,
        }

        // 只有当 favorite 有值时才添加到参数中
        if (favorite !== undefined) {
          params.favorite = favorite
        }

        const response = await MediaitemService.getMediaItems(params)

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
        }

        return this.allMediaItems
      } finally {
        this.isLoading = false
      }
    },

    // Show dialog for updating media item
    showUpdateMediaItem(data: MediaItemWithWatches) {
      this.editMediaItem = data
      this.showDialog = true
    },

    // Show dialog for adding new media item
    showAddMediaItem() {
      this.editMediaItem = undefined
      this.showDialog = true
    },

    // Update existing media item
    async updateMediaItem(data: MediaItemWithWatches) {
      this.isLoading = true
      try {
        const mediaItem = await MediaitemService.updateMediaItem({
          mediaId: data.id,
          requestBody: {
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
          },
        })

        if (this.showDialog) {
          this.updateMediaItemById(data.id, mediaItem)
          this.showDialog = false

          const toastStore = useToastStore()
          toastStore.success("Media item updated successfully")
        }
      } catch (error) {
        console.error("Error updating media item:", error)
        const toastStore = useToastStore()
        toastStore.error("Failed to update media item")
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

        const response = await MediaitemService.createMediaItem({
          requestBody: mediaItemCreate,
        })

        if (response) {
          // Add the new media item to the list
          this.allMediaItems.push({
            ...response,
            userdata: {
              watched: false,
            },
          })
          this.showDialog = false

          // Refresh the list to ensure sorting and other data is updated
          await this.getMediaItems()

          const toastStore = useToastStore()
          toastStore.success("Media item created successfully")
        }
      } catch (error) {
        console.error("Error creating media item:", error)
        const toastStore = useToastStore()
        toastStore.error("Failed to create media item")
      } finally {
        this.isLoading = false
      }
    },

    // Update media item by ID
    updateMediaItemById(id: number, newValue: Partial<MediaItemInDB>) {
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
        "Delete Media Item",
        "Are you sure you want to delete this media item? This action cannot be undone.",
      )

      if (confirmed) {
        await this.deleteMediaItem(id)
      }
    },

    // Delete media item
    async deleteMediaItem(idToRemove: number) {
      this.isLoading = true
      try {
        const response = await MediaitemService.deleteMediaItem({
          mediaId: idToRemove,
        })

        if (response) {
          this.allMediaItems = this.allMediaItems.filter(
            (mediaItem) => mediaItem.id !== idToRemove,
          )

          const toastStore = useToastStore()
          toastStore.success("Media item deleted successfully")
        }
      } catch (error) {
        console.error("Error deleting media item:", error)
        const toastStore = useToastStore()
        toastStore.error("Failed to delete media item")
      } finally {
        this.isLoading = false
      }
    },

    // Clean media items (remove duplicates)
    async cleanMediaItems() {
      this.isLoading = true
      try {
        const response = await MediaitemService.cleanMediaItem()

        if (response) {
          // Refresh the list after cleaning
          await this.getMediaItems()

          const toastStore = useToastStore()
          toastStore.success("Media items cleaned successfully")
        }
      } catch (error) {
        console.error("Error cleaning media items:", error)
        const toastStore = useToastStore()
        toastStore.error("Failed to clean media items")
      } finally {
        this.isLoading = false
      }
    },
  },
})
