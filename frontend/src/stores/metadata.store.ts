import { type MetadataPublic, MetadataService } from "@/client"
import { defineStore } from "pinia"
import { ref } from "vue"

export const useMetadataStore = defineStore("metadata", () => {
  const metadata = ref<MetadataPublic[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchMetadata() {
    try {
      loading.value = true
      error.value = null
      const response = await MetadataService.getMetadata()
      metadata.value = response.data
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to fetch metadata"
      console.error("Error fetching metadata:", e)
    } finally {
      loading.value = false
    }
  }

  return {
    metadata,
    loading,
    error,
    fetchMetadata,
  }
})
