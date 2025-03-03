import { type MetadataPublic, MetadataService } from "@/client"
import { defineStore } from "pinia"
import { useConfirmationStore } from "./confirmation.store"

export const useMetadataStore = defineStore("metadata-store", {
  state: () => ({
    allMetadata: [] as MetadataPublic[],
    showDialog: false,
    editMetadata: undefined as MetadataPublic | undefined,
  }),
  actions: {
    async getAllMetadata() {
      const all = await MetadataService.getMetadata()
      this.allMetadata = all.data
      return this.allMetadata
    },
    showUpdateMetadata(data: MetadataPublic) {
      this.editMetadata = data
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
        'Delete Metadata',
        'Are you sure you want to delete this metadata? This action cannot be undone.'
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
