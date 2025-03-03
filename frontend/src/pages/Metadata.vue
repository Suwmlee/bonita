<script setup lang="ts">
import type { MetadataPublic } from "@/client"
import { OpenAPI } from "@/client"
import MetadataDetailDialog from "@/components/metadata/MetadataDetailDialog.vue"
import { useMetadataStore } from "@/stores/metadata.store"

const metadataStore = useMetadataStore()
const { metadata } = storeToRefs(metadataStore)
const showDialog = ref(false)
const selectedItem = ref<MetadataPublic | null>(null)

function showEditDialog(item: MetadataPublic) {
  selectedItem.value = item
  showDialog.value = true
}

// Fetch metadata when component is mounted
metadataStore.fetchMetadata()
// Function to get image URL using ResourceService
function getImageUrl(path: string) {
  return `${OpenAPI.BASE}/api/v1/resource/image?path=${encodeURIComponent(path)}`
}
</script>

<template>
  <div>
    <VRow>
      <VCol v-for="item in metadata" :key="item.id" cols="12" md="6" lg="4">
        <VCard height="400" class="d-flex flex-column" @click="showEditDialog(item)">
          <VCardItem>
            <VCardTitle>
              {{ item.number }}
            </VCardTitle>
          </VCardItem>

          <VCardText class="flex-grow-1">
            <p class="mb-2 text-truncate">
              <strong>Title:</strong> {{ item.title }}
            </p>
            <p class="mb-2">
              <strong>Actor:</strong> {{ item.actor }}
            </p>
            <p class="mb-2">
              <strong>Site:</strong> {{ item.site }}
            </p>
            <p class="mb-0 text-truncate">
              <strong>URL:</strong> {{ item.detailurl }}
            </p>
          </VCardText>

          <VCardText v-if="item.cover" class="d-flex justify-center" style="max-height: 200px;">
            <VImg :src="getImageUrl(item.cover)" height="180" contain />
          </VCardText>
        </VCard>
      </VCol>
    </VRow>

    <MetadataDetailDialog v-model="showDialog" :metadata="selectedItem" />
  </div>
</template>

<style scoped>
.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
