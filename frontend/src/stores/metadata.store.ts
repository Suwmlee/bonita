import {
  type MetadataCreate,
  type MetadataPublic,
  MetadataService,
} from "@/client"
import { defineStore } from "pinia"
import { useConfirmationStore } from "./confirmation.store"

export const useMetadataStore = defineStore("metadata-store", {
  state: () => ({
    allMetadata: [] as MetadataPublic[],
    showDialog: false,
    editMetadata: undefined as MetadataPublic | undefined,
  }),
  actions: {
    // Combined method for getting all metadata and searching with filter
    async getMetadata(filter?: string) {
      const response = await MetadataService.getMetadata({
        filter: filter,
      })
      this.allMetadata = response.data
      return this.allMetadata
    },
    showUpdateMetadata(data: MetadataPublic) {
      this.editMetadata = data
      this.showDialog = true
    },
    // Method to show dialog for adding new metadata
    showAddMetadata() {
      this.editMetadata = undefined
      this.showDialog = true
    },
    async updateMetadata(data: MetadataPublic) {
      const metadata = await MetadataService.updateMetadata({
        id: data.id,
        requestBody: data,
      })
      if (this.showDialog) {
        this.updateMetadataById(data.id, metadata)
        this.showDialog = false
      }
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
          actor: data.actor,
          actor_photo: data.actor_photo,
          cover: data.cover,
          cover_small: data.cover_small,
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

        const response = await MetadataService.createMetadata({
          requestBody: metadataCreate,
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
        "Delete Metadata",
        "Are you sure you want to delete this metadata? This action cannot be undone.",
      )

      if (confirmed) {
        await this.deleteMetadata(id)
      }
    },
    async deleteMetadata(idToRemove: number) {
      const response = await MetadataService.deleteMetadata({
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
