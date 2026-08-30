import {
  type MetadataCreate,
  type MetadataPublic,
  MetadataService,
} from "@/client"
import { i18n } from "@/plugins/i18n"
import { defineStore } from "pinia"
import { useConfirmationStore } from "./confirmation.store"

const ITEMS_PER_PAGE_KEY = "metadata-items-per-page"
const ITEMS_PER_PAGE_OPTIONS = [12, 24, 48, 96]
const DEFAULT_ITEMS_PER_PAGE = 24

function loadItemsPerPage(): number {
  const parsed = Number.parseInt(
    localStorage.getItem(ITEMS_PER_PAGE_KEY) ?? "",
    10,
  )
  return ITEMS_PER_PAGE_OPTIONS.includes(parsed)
    ? parsed
    : DEFAULT_ITEMS_PER_PAGE
}

export const useMetadataStore = defineStore("metadata-store", {
  state: () => ({
    allMetadata: [] as MetadataPublic[],
    showDialog: false,
    showImportDialog: false,
    showRefreshDialog: false,
    editMetadata: undefined as MetadataPublic | undefined,
    refreshTarget: undefined as MetadataPublic | undefined,
    totalCount: 0,
    currentPage: 1,
    itemsPerPage: loadItemsPerPage(),
  }),
  actions: {
    // Combined method for getting all metadata and searching with filter
    async getMetadata(
      filter?: string,
      page?: number,
      itemsPerPage?: number,
      sortBy?: string,
      sortDesc?: boolean,
    ) {
      const skip =
        page !== undefined
          ? (page - 1) * (itemsPerPage || this.itemsPerPage)
          : (this.currentPage - 1) * this.itemsPerPage
      const limit =
        itemsPerPage !== undefined ? itemsPerPage : this.itemsPerPage

      const { data: response } = await MetadataService.getMetadata({
        filter: filter,
        skip: skip,
        limit: limit,
        sort_by: sortBy,
        sort_desc: sortDesc,
      })

      this.allMetadata = response.data

      // MetadataCollection has count property instead of meta.total
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

      return this.allMetadata
    },
    showUpdateMetadata(data: MetadataPublic) {
      this.editMetadata = data
      this.showDialog = true
    },
    showRefreshMetadata(data: MetadataPublic) {
      this.showDialog = false
      this.refreshTarget = data
      this.showRefreshDialog = true
    },
    // Method to show dialog for adding new metadata
    showAddMetadata() {
      this.editMetadata = undefined
      this.showDialog = true
    },
    async updateMetadata(data: MetadataPublic) {
      const { data: metadata } = await MetadataService.updateMetadata({
        id: data.id,
        metadataBase: data,
      })
      this.updateMetadataById(data.id, metadata)
      if (this.showDialog) {
        this.showDialog = false
      }
      return metadata
    },
    // Method to import metadata from JSON (single object or array)
    async importFromJson(
      jsonData: Partial<MetadataCreate> | Partial<MetadataCreate>[],
    ): Promise<{ success: number; failed: number }> {
      const items = Array.isArray(jsonData) ? jsonData : [jsonData]
      let success = 0
      let failed = 0

      for (const item of items) {
        try {
          const metadataCreate: MetadataCreate = {
            number: item.number || "",
            title: item.title || "",
            studio: item.studio,
            release: item.release,
            year: item.year,
            runtime: item.runtime,
            genre: item.genre,
            rating: item.rating,
            language: item.language,
            country: item.country,
            outline: item.outline,
            director: item.director,
            actor: item.actor || "",
            actor_photo: item.actor_photo,
            cover: item.cover || "",
            cover_small: item.cover_small,
            crop: item.crop ?? true,
            extrafanart: item.extrafanart,
            trailer: item.trailer,
            tag: item.tag,
            label: item.label,
            series: item.series,
            userrating: item.userrating,
            uservotes: item.uservotes,
            detailurl: item.detailurl,
            site: item.site,
          }
          await MetadataService.createMetadata({ metadataCreate })
          success++
        } catch {
          failed++
        }
      }

      if (success > 0) {
        await this.getMetadata()
        this.showImportDialog = false
      }

      return { success, failed }
    },
    // Method to add new metadata
    async addMetadata(data: Partial<MetadataPublic>) {
      try {
        // Ensure required fields have valid values
        const metadataCreate: MetadataCreate = {
          number: data.number || "", // Required field
          title: data.title || "", // Required field
          studio: data.studio,
          release: data.release,
          year: data.year,
          runtime: data.runtime,
          genre: data.genre,
          rating: data.rating,
          language: data.language,
          country: data.country,
          outline: data.outline,
          director: data.director,
          actor: data.actor || "",
          actor_photo: data.actor_photo,
          cover: data.cover || "",
          cover_small: data.cover_small,
          crop: data.crop ?? true,
          extrafanart: data.extrafanart,
          trailer: data.trailer,
          tag: data.tag,
          label: data.label,
          series: data.series,
          userrating: data.userrating,
          uservotes: data.uservotes,
          detailurl: data.detailurl,
          site: data.site,
        }

        const { data: response } = await MetadataService.createMetadata({
          metadataCreate,
        })

        if (response) {
          // Add the new metadata to the list
          this.allMetadata.push(response)
          this.showDialog = false

          // Refresh the list to ensure sorting and other data is updated
          await this.getMetadata()
        }
      } catch (error) {
        console.error("Error creating metadata:", error)
        alert(
          "Failed to create metadata. Please check the console for details.",
        )
      }
    },
    updateMetadataById(id: number, newValue: Partial<MetadataPublic>) {
      const index = this.allMetadata.findIndex((metadata) => metadata.id === id)

      if (index !== -1) {
        this.allMetadata[index] = {
          ...this.allMetadata[index],
          ...newValue,
        }
      } else {
        console.error(`metadata with id ${id} not found.`)
      }
    },
    // Use confirmation store for delete confirmation
    async confirmDeleteMetadata(id: number) {
      const confirmationStore = useConfirmationStore()
      const confirmed = await confirmationStore.confirmDelete(
        i18n.global.t("pages.metadata.confirmDeleteTitle") as string,
        i18n.global.t("pages.metadata.confirmDeleteMessage") as string,
      )

      if (confirmed) {
        await this.deleteMetadata(id)
      }
    },
    async deleteMetadata(idToRemove: number) {
      const { data: response } = await MetadataService.deleteMetadata({
        id: idToRemove,
      })
      if (response.success) {
        this.allMetadata = this.allMetadata.filter(
          (metadata) => metadata.id !== idToRemove,
        )
      }
    },
  },
})
