<script setup lang="ts">
import type { MetadataPublic } from "@/client"
import { OpenAPI } from "@/client"
import MetadataDetailDialog from "@/components/metadata/MetadataDetailDialog.vue"
import { useMetadataStore } from "@/stores/metadata.store"

const metadataStore = useMetadataStore()

function showEditDialog(item: MetadataPublic) {
  metadataStore.showUpdateMetadata(item)
}

// Function to get image URL using ResourceService
function getImageUrl(path: string) {
  return `${OpenAPI.BASE}/api/v1/resource/image?path=${encodeURIComponent(path)}`
}

onMounted(() => {
  metadataStore.getAllMetadata()
})
</script>

<template>
  <div>
    <p class="text-xl mb-6">
      Metadata
    </p>
    <VRow>
      <VCol v-for="item in metadataStore.allMetadata" :key="item.id" cols="12" sm="6" md="4" lg="3" xl="2">
        <VCard height="400" max-width="320px" class="d-flex flex-column" @click="showEditDialog(item)">
          <VCardItem>
            <VCardTitle class="d-flex justify-space-between align-center">
              <span>{{ item.number }}</span>
              <div class="d-flex justify-end">
                <VBtn variant="text" @click.stop="metadataStore.confirmDeleteMetadata(item.id)">
                  <VIcon style="color: firebrick;" icon="bx-trash" size="22" />
                </VBtn>
              </div>
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
    
    <!-- Metadata edit dialog -->
    <MetadataDetailDialog />
  </div>
</template>

<style scoped>
.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
