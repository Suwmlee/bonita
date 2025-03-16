<script setup lang="ts">
import type { MediaItemWithWatches } from "@/client"
import MediaItemDetailDialog from "@/components/mediaitem/MediaItemDetailDialog.vue"
import { useMediaItemStore } from "@/stores/mediaitem.store"
import { computed, onMounted, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

const mediaItemStore = useMediaItemStore()
const searchQuery = ref("")
const isSearching = ref(false)
const { t } = useI18n()

// Media type filter
const selectedMediaType = ref<string | null>(null)
const mediaTypeOptions = [
  { value: null, title: t("pages.mediaitem.allTypes") },
  { value: "movie", title: t("pages.mediaitem.movie") },
  { value: "tvshow", title: t("pages.mediaitem.tvshow") },
]

// Watched filter
const watchedFilter = ref<boolean | null>(null)
const watchedOptions = [
  { value: null, title: t("pages.mediaitem.allWatched") },
  { value: true, title: t("pages.mediaitem.watched") },
  { value: false, title: t("pages.mediaitem.unwatched") },
]

// Has number filter
const hasNumberFilter = ref<boolean | null>(null)
const hasNumberOptions = [
  { value: null, title: t("pages.mediaitem.allItems") },
  { value: true, title: t("pages.mediaitem.hasNumber") },
  { value: false, title: t("pages.mediaitem.noNumber") },
]

// Pagination
const currentPage = computed(() => mediaItemStore.currentPage)
const totalItems = computed(() => mediaItemStore.totalCount)
const itemsPerPage = computed({
  get: () => mediaItemStore.itemsPerPage,
  set: async (value) => {
    await mediaItemStore.getMediaItems(
      searchQuery.value,
      1,
      value,
      selectedMediaType.value || undefined,
      undefined,
      undefined,
      hasNumberFilter.value === null ? undefined : hasNumberFilter.value,
      watchedFilter.value === null ? undefined : watchedFilter.value,
    )
  },
})
const totalPages = computed(() =>
  Math.ceil(totalItems.value / itemsPerPage.value),
)
const itemsPerPageOptions = [24, 48, 96]

// Function to show the edit dialog
function showEditDialog(item: MediaItemWithWatches) {
  mediaItemStore.showUpdateMediaItem(item)
}

// Function to show the add media item dialog
function showAddDialog() {
  mediaItemStore.showAddMediaItem()
}

// Function to search media items with filters
async function searchMediaItems() {
  isSearching.value = true
  try {
    await mediaItemStore.getMediaItems(
      searchQuery.value,
      undefined,
      undefined,
      selectedMediaType.value || undefined,
      undefined,
      undefined,
      hasNumberFilter.value === null ? undefined : hasNumberFilter.value,
      watchedFilter.value === null ? undefined : watchedFilter.value,
    )
  } finally {
    isSearching.value = false
  }
}

// Change page function
async function changePage(page: number) {
  await mediaItemStore.getMediaItems(
    searchQuery.value,
    page,
    undefined,
    selectedMediaType.value || undefined,
    undefined,
    undefined,
    hasNumberFilter.value === null ? undefined : hasNumberFilter.value,
    watchedFilter.value === null ? undefined : watchedFilter.value,
  )
}

// Function to clean media items (remove duplicates)
async function cleanMediaItems() {
  await mediaItemStore.cleanMediaItems()
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

// Watch for changes in filters
watch(
  [searchQuery, selectedMediaType, watchedFilter, hasNumberFilter],
  async () => {
    await searchMediaItems()
  },
)

onMounted(() => {
  mediaItemStore.getMediaItems()
})
</script>

<template>
  <div>
    <p class="text-xl mb-6">
      {{ t('pages.mediaitem.title') }}
    </p>

    <!-- Search input and filters -->
    <VRow class="mb-4">
      <VCol cols="12" sm="6" md="4" lg="3" xl="3">
        <VTextField 
          v-model="searchQuery" 
          :placeholder="t('pages.mediaitem.search')" 
          clearable 
          hide-details
          prepend-inner-icon="bx-search" 
          :loading="isSearching" 
          variant="outlined" 
          density="comfortable" 
        />
      </VCol>
      
      <VCol cols="12" sm="6" md="2" lg="2" xl="2">
        <VSelect
          v-model="selectedMediaType"
          :items="mediaTypeOptions"
          item-title="title"
          item-value="value"
          :label="t('pages.mediaitem.mediaType')"
          variant="outlined"
          density="comfortable"
          hide-details
        />
      </VCol>
      
      <VCol cols="12" sm="6" md="2" lg="2" xl="2">
        <VSelect
          v-model="watchedFilter"
          :items="watchedOptions"
          item-title="title"
          item-value="value"
          :label="t('pages.mediaitem.watchedStatus')"
          variant="outlined"
          density="comfortable"
          hide-details
        />
      </VCol>
      
      <VCol cols="12" sm="6" md="2" lg="2" xl="2">
        <VSelect
          v-model="hasNumberFilter"
          :items="hasNumberOptions"
          item-title="title"
          item-value="value"
          :label="t('pages.mediaitem.numberStatus')"
          variant="outlined"
          density="comfortable"
          hide-details
        />
      </VCol>
      
      <VCol cols="12" sm="12" md="2" lg="3" xl="3" class="d-flex align-center">
        <VBtn color="primary" @click="showAddDialog" prepend-icon="bx-plus" class="me-2">
          {{ t('pages.mediaitem.addNew') }}
        </VBtn>
        <VBtn color="secondary" @click="cleanMediaItems" prepend-icon="bx-trash">
          {{ t('pages.mediaitem.clean') }}
        </VBtn>
      </VCol>
    </VRow>

    <VRow>
      <VCol v-for="item in mediaItemStore.allMediaItems" :key="item.id" cols="12" sm="6" md="4" lg="3" xl="2">
        <VCard class="d-flex flex-column h-100" @click="showEditDialog(item)">
          <!-- Card Header -->
          <VCardItem>
            <VCardTitle class="d-flex justify-space-between align-center">
              <span class="text-truncate">{{ item.title }}</span>
              <div class="d-flex justify-end">
                <VBtn variant="text" @click.stop="mediaItemStore.confirmDeleteMediaItem(item.id)">
                  <VIcon style="color: firebrick;" icon="bx-trash" size="22" />
                </VBtn>
              </div>
            </VCardTitle>
          </VCardItem>

          <!-- Card Content -->
          <VCardText class="flex-grow-1">
            <div v-if="item.number" class="mb-2 d-flex align-center">
              <VIcon icon="bx-hash" size="small" class="me-1" />
              <span class="text-truncate">{{ item.number }}</span>
            </div>
            
            <div class="mb-2 d-flex align-center">
              <VIcon icon="bx-film" size="small" class="me-1" />
              <span>{{ item.media_type === 'movie' ? t('pages.mediaitem.movie') : t('pages.mediaitem.tvshow') }}</span>
            </div>
            
            <div class="mb-2 d-flex align-center">
              <VIcon icon="bx-calendar" size="small" class="me-1" />
              <span>{{ formatDateTime(item.updatetime) }}</span>
            </div>
            
            <div class="d-flex align-center">
              <VIcon 
                :icon="item.userdata?.watched ? 'bx-check-circle' : 'bx-time'" 
                size="small" 
                class="me-1"
                :color="item.userdata?.watched ? 'success' : 'warning'"
              />
              <span>{{ item.userdata?.watched ? t('pages.mediaitem.watched') : t('pages.mediaitem.unwatched') }}</span>
            </div>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>

    <!-- No results message -->
    <VRow v-if="mediaItemStore.allMediaItems.length === 0" class="mt-5">
      <VCol class="text-center">
        <p class="text-medium-emphasis">{{ t('pages.mediaitem.noResults') }}</p>
      </VCol>
    </VRow>

    <!-- Pagination -->
    <VRow v-if="totalItems > 0" class="mt-5">
      <VCol>
        <div class="d-flex align-center justify-end px-4 py-3 w-100">
          <div class="d-flex align-center me-4">
            <span class="text-caption text-grey me-2">{{ t('pages.mediaitem.itemsPerPage') }}</span>
            <v-select v-model="itemsPerPage" :items="itemsPerPageOptions" density="compact"
              style="width: 80px" hide-details variant="plain" />
            <div class="ms-4 text-caption text-grey">
              {{ t('pages.mediaitem.totalItems', { count: totalItems }) }}
            </div>
          </div>

          <v-pagination v-model="mediaItemStore.currentPage"
            :length="totalPages"
            @update:model-value="changePage" 
            :total-visible="5" 
            :show-first-last-page="false" />
        </div>
      </VCol>
    </VRow>

    <!-- Media item edit dialog -->
    <MediaItemDetailDialog />
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
