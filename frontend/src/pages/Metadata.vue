<script setup lang="ts">
import type { MetadataPublic } from "@/client"
import { OpenAPI } from "@/client"
import MetadataDetailDialog from "@/components/metadata/MetadataDetailDialog.vue"
import { useMetadataStore } from "@/stores/metadata.store"
import { computed, onMounted, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

const metadataStore = useMetadataStore()
const searchQuery = ref("")
const isSearching = ref(false)
const { t } = useI18n() // 导入国际化工具函数

// Pagination
const currentPage = computed(() => metadataStore.currentPage)
const totalItems = computed(() => metadataStore.totalCount)
const itemsPerPage = computed({
  get: () => metadataStore.itemsPerPage,
  set: async (value) => {
    await metadataStore.getMetadata(searchQuery.value, 1, value) // Reset to page 1 when changing items per page
  },
})
const totalPages = computed(() =>
  Math.ceil(totalItems.value / itemsPerPage.value),
)
const itemsPerPageOptions = [24, 48, 96]

function showEditDialog(item: MetadataPublic) {
  metadataStore.showUpdateMetadata(item)
}

// Function to show the add metadata dialog
function showAddDialog() {
  metadataStore.showAddMetadata()
}

// Function to get image URL using ResourceService
function getImageUrl(path: string) {
  // Add timestamp parameter to prevent browser caching
  const timestamp = new Date().getTime()
  return `${OpenAPI.BASE}/api/v1/resource/image?path=${encodeURIComponent(path)}&t=${timestamp}`
}

// Function to search metadata with filter
async function searchMetadata() {
  isSearching.value = true
  try {
    await metadataStore.getMetadata(searchQuery.value)
  } finally {
    isSearching.value = false
  }
}

// Change page function
async function changePage(page: number) {
  await metadataStore.getMetadata(searchQuery.value, page)
}

const formatDateTime = (dateStr: string | null | undefined) => {
  if (!dateStr) return ""
  return new Date(dateStr).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  })
}

// Watch for changes in search query
watch(searchQuery, async (newValue) => {
  if (newValue === "") {
    await metadataStore.getMetadata() // Reset to all metadata when search is cleared
  } else {
    await searchMetadata()
  }
})

onMounted(() => {
  metadataStore.getMetadata()
})
</script>

<template>
  <div>
    <p class="text-xl mb-6">
      {{ t('pages.metadata.title') }}
    </p>

    <!-- Search input and Add button -->
    <VRow class="mb-4">
      <VCol cols="12" sm="10" md="8" lg="6" xl="4" class="d-flex align-center">
        <VTextField v-model="searchQuery" :placeholder="t('pages.metadata.search')" clearable hide-details
          prepend-inner-icon="bx-search" :loading="isSearching" variant="outlined" density="comfortable" class="mr-2" />
        <VBtn color="primary" @click="showAddDialog" prepend-icon="bx-plus">
          {{ t('pages.metadata.addNew') }}
        </VBtn>
      </VCol>
    </VRow>

    <VRow>
      <VCol v-for="item in metadataStore.allMetadata" :key="item.id" cols="12" sm="6" md="4" lg="3" xl="2">
        <VCard class="d-flex flex-column" @click="showEditDialog(item)">
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

          <VCardText class="flex-grow-1" style="padding-bottom: 10px;">
            <p class="mb-2 text-truncate">
              {{ item.title }}
            </p>
            <p class="mb-2 text-truncate">
              <strong>{{ t('pages.metadata.actor') }}:</strong> {{ item.actor }}
            </p>
            <p class="mb-2 text-truncate">
              <strong>{{ t('pages.metadata.tag') }}:</strong> {{ item.tag }}
            </p>
            <p class="mb-0 text-truncate">
              <strong>{{ t('pages.metadata.update') }}:</strong> {{ formatDateTime(item.updatetime) }}
            </p>
          </VCardText>

          <VCardText v-if="item.cover" class="d-flex justify-center">
            <VImg :src="getImageUrl(item.cover)" height="200" contain />
          </VCardText>
        </VCard>
      </VCol>
    </VRow>

    <!-- No results message -->
    <VRow v-if="metadataStore.allMetadata.length === 0" class="mt-5">
      <VCol class="text-center">
        <p class="text-medium-emphasis">{{ t('pages.metadata.noResults') }}</p>
      </VCol>
    </VRow>

    <!-- Pagination -->
    <VRow v-if="totalItems > 0" class="mt-5">
      <VCol>
        <div class="d-flex align-center justify-end px-4 py-3 w-100">
          <div class="d-flex align-center me-4">
            <span class="text-caption text-grey me-2">{{ t('pages.metadata.itemsPerPage') }}</span>
            <v-select v-model="itemsPerPage" :items="itemsPerPageOptions" density="compact"
              style="width: 80px" hide-details variant="plain" />
            <div class="ms-4 text-caption text-grey">
              {{ t('pages.metadata.totalItems', { count: totalItems }) }}
            </div>
          </div>

          <v-pagination v-model="metadataStore.currentPage"
            :length="totalPages"
            @update:model-value="changePage" 
            :total-visible="5" 
            :show-first-last-page="false" />
        </div>
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

/* 分页样式 */
:deep(.v-pagination__list) {
  max-width: 100%;
  overflow-x: auto;
}

:deep(.v-pagination__item) {
  min-width: 34px;
}

@media (max-width: 768px) {
  .d-flex.align-center.justify-end {
    flex-direction: column;
    align-items: flex-start !important;
    gap: 16px;
  }
  
  .d-flex.align-center.me-4 {
    margin-right: 0 !important;
    width: 100%;
    justify-content: space-between;
  }
}
</style>
