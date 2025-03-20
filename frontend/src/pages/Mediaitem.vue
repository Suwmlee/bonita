<script setup lang="ts">
import type { MediaItemWithWatches } from "@/client"
import { OpenAPI, ResourceService } from "@/client"
import MediaItemDetailDialog from "@/components/mediaitem/MediaItemDetailDialog.vue"
import { useMediaItemStore } from "@/stores/mediaitem.store"
import { computed, onMounted, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

const mediaItemStore = useMediaItemStore()
const searchQuery = ref("")
const isSearching = ref(false)
const { t } = useI18n()

// Sort dropdown state
const sortDropdownOpen = ref(false)

// Media type filter with hasNumber options
const selectedMediaType = ref<string | null>(null)
const mediaTypeOptions = [
  { value: null, title: t("pages.mediaitem.mediaType") },
  { value: "movie", title: t("pages.mediaitem.movie") },
  { value: "tvshow", title: t("pages.mediaitem.tvshow") },
  { value: "number", title: t("pages.mediaitem.hasNumber") },
]

// Watched filter
const watchedFilter = ref<boolean | null>(null)
const watchedOptions = [
  { value: null, title: t("pages.mediaitem.watchedStatus") },
  { value: true, title: t("pages.mediaitem.watched") },
  { value: false, title: t("pages.mediaitem.unwatched") },
]

// Favorite filter
const favoriteFilter = ref<boolean | null>(null)
const favoriteOptions = [
  { value: null, title: t("pages.mediaitem.favoriteStatus") },
  { value: true, title: t("pages.mediaitem.favorite") },
  { value: false, title: t("pages.mediaitem.notFavorite") },
]

// Sort options
const sortField = ref<string>("updatetime")
const sortDirection = ref<'asc' | 'desc'>('desc')

const sortOptions = [
  { 
    value: "updatetime", 
    title: t("pages.mediaitem.updatetime"), 
    icon: "bx-sort"
  },
  { 
    value: "createtime", 
    title: t("pages.mediaitem.createtime"), 
    icon: "bx-sort"
  },
  { 
    value: "title", 
    title: t("pages.mediaitem.title"), 
    icon: "bx-sort"
  },
]

// Handle sort selection
function handleSortChange(value: string) {
  // If selecting the same field, toggle direction
  if (value === sortField.value) {
    sortDirection.value = sortDirection.value === 'desc' ? 'asc' : 'desc'
  } else {
    // If selecting a new field, set it with default desc direction
    sortField.value = value
    sortDirection.value = 'desc'
  }
  
  // Close the dropdown
  sortDropdownOpen.value = false
  
  // Trigger search with new sort params
  searchMediaItems()
}

// Get sort icon based on field and current direction
function getSortIcon(value: string): string {
  if (value !== sortField.value) return "bx-sort"
  
  if (value === "title") {
    return sortDirection.value === 'desc' ? "bx-sort-a-z" : "bx-sort-z-a"
  }
  
  return sortDirection.value === 'desc' ? "bx-sort-down" : "bx-sort-up"
}

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
      getMediaTypeValue(),
      sortField.value || undefined,
      sortDirection.value === 'desc',
      getHasNumberValue(),
      watchedFilter.value === null ? undefined : watchedFilter.value,
      favoriteFilter.value === null ? undefined : favoriteFilter.value,
    )
  },
})
const totalPages = computed(() =>
  Math.ceil(totalItems.value / itemsPerPage.value),
)
const itemsPerPageOptions = [24, 48, 96]

// Function to extract media type, hasNumber from combined selection
function getMediaTypeValue(): string | undefined {
  if (!selectedMediaType.value) return undefined
  if (selectedMediaType.value === "number") return undefined
  return selectedMediaType.value
}

// Function to extract hasNumber value from combined selection
function getHasNumberValue(): boolean | undefined {
  if (selectedMediaType.value === "number") return true
  if (selectedMediaType.value === "movie" || selectedMediaType.value === "tvshow") return false
  return undefined
}

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
      getMediaTypeValue(),
      sortField.value || undefined,
      sortDirection.value === 'desc',
      getHasNumberValue(),
      watchedFilter.value === null ? undefined : watchedFilter.value,
      favoriteFilter.value === null ? undefined : favoriteFilter.value,
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
    getMediaTypeValue(),
    sortField.value || undefined,
    sortDirection.value === 'desc',
    getHasNumberValue(),
    watchedFilter.value === null ? undefined : watchedFilter.value,
    favoriteFilter.value === null ? undefined : favoriteFilter.value,
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

// 处理海报URL的函数
const getPosterUrl = (item: MediaItemWithWatches): string => {
  const baseUrl = `${OpenAPI.BASE}/api/v1/resource/poster?`
  const params = new URLSearchParams()

  params.append("title", item.title)

  if (item.imdb_id) {
    params.append("imdb_id", item.imdb_id)
  }

  if (item.tmdb_id) {
    params.append("tmdb_id", item.tmdb_id.toString())
  }

  if (item.number) {
    params.append("number", item.number)
  }

  // 添加时间戳防止缓存
  // params.append('t', Date.now().toString())

  return baseUrl + params.toString()
}

// Watch for changes in filters
watch(
  [
    searchQuery,
    selectedMediaType,
    watchedFilter,
    favoriteFilter,
  ],
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
        <VTextField v-model="searchQuery" :placeholder="t('pages.mediaitem.search')" clearable hide-details
          prepend-inner-icon="bx-search" :loading="isSearching" variant="outlined" density="comfortable" />
      </VCol>

      <VCol cols="12" sm="6" md="2" lg="1" xl="1">
        <VSelect 
          v-model="selectedMediaType" 
          :items="mediaTypeOptions" 
          item-title="title" 
          item-value="value"
          variant="outlined" 
          density="comfortable" 
          hide-details
          class="filter-dropdown"
        />
      </VCol>

      <VCol cols="12" sm="6" md="2" lg="1" xl="1">
        <VSelect 
          v-model="watchedFilter" 
          :items="watchedOptions" 
          item-title="title" 
          item-value="value"
          variant="outlined" 
          density="comfortable" 
          hide-details
          class="filter-dropdown"
        />
      </VCol>

      <VCol cols="12" sm="6" md="2" lg="1" xl="1">
        <VSelect 
          v-model="favoriteFilter" 
          :items="favoriteOptions" 
          item-title="title" 
          item-value="value"
          variant="outlined" 
          density="comfortable" 
          hide-details
          class="filter-dropdown"
        />
      </VCol>

      <VCol cols="12" sm="6" md="1" lg="1" xl="1">
        <VBtn
          variant="outlined"
          class="sort-btn"
          @click="sortDropdownOpen = !sortDropdownOpen"
          density="comfortable"
        >
          <div class="d-flex align-center w-100">
            <VIcon :icon="getSortIcon(sortField)" size="small" class="me-2" />
            <span class="text-truncate">{{ sortOptions.find(opt => opt.value === sortField)?.title }}</span>
          </div>
        </VBtn>
        <VMenu
          v-model="sortDropdownOpen"
          location="bottom end"
          :offset="[0, 5]"
          :width="'auto'"
          min-width="100%"
        >
          <template v-slot:activator="{ props }">
            <div v-bind="props"></div>
          </template>
          <VCard class="sort-menu-card">
            <VList>
              <VListItem
                v-for="option in sortOptions"
                :key="option.value"
                @click="handleSortChange(option.value)"
                class="sort-list-item"
              >
                <VListItemTitle>
                  {{ option.title }}
                  <VIcon
                    v-if="option.value === sortField"
                    size="small" 
                    class="ms-2"
                    :icon="sortDirection === 'desc' ? 'bx-down-arrow-alt' : 'bx-up-arrow-alt'"
                  />
                </VListItemTitle>
              </VListItem>
            </VList>
          </VCard>
        </VMenu>
      </VCol>

      <!-- <VCol cols="12" sm="12" md="2" lg="3" xl="3" class="d-flex align-center">
        <VBtn color="primary" @click="showAddDialog" prepend-icon="bx-plus" class="me-2">
          {{ t('pages.mediaitem.addNew') }}
        </VBtn>
        <VBtn color="secondary" @click="cleanMediaItems" prepend-icon="bx-trash">
          {{ t('pages.mediaitem.clean') }}
        </VBtn>
      </VCol> -->
    </VRow>

    <VRow>
      <VCol v-for="item in mediaItemStore.allMediaItems" :key="item.id" cols="12" sm="6" md="4" lg="3" xl="2">
        <VCard class="media-card d-flex flex-column" @click="showEditDialog(item)">
          <!-- Card with poster as background -->
          <div class="poster-background" :style="{ backgroundImage: `url(${getPosterUrl(item)})` }">
            <!-- Content overlay with gradient -->
            <div class="content-overlay">
              <!-- Title at the top -->
              <div class="media-title">
                <span>{{ item.title }}</span>
              </div>

              <!-- Info at the bottom -->
              <div class="media-info">
                <div v-if="item.number" class="mb-2 d-flex align-center">
                  <VIcon icon="bx-hash" size="small" class="me-1" />
                  <span class="text-truncate">{{ item.number }}</span>
                </div>

                <div class="mb-2 d-flex align-center">
                  <VIcon icon="bx-film" size="small" class="me-1" />
                  <span>{{ item.media_type === 'movie' ? t('pages.mediaitem.movie') : t('pages.mediaitem.tvshow')
                  }}</span>
                </div>

                <div class="mb-2 d-flex align-center">
                  <VIcon icon="bx-calendar" size="small" class="me-1" />
                  <span>{{ formatDateTime(item.updatetime) }}</span>
                </div>

                <div class="d-flex align-center">
                  <VIcon :icon="item.userdata?.watched ? 'bx-check-circle' : 'bx-time'" size="small" class="me-1"
                    :color="item.userdata?.watched ? 'success' : 'warning'" />
                  <span>{{ item.userdata?.watched ? t('pages.mediaitem.watched') : t('pages.mediaitem.unwatched')
                  }}</span>
                </div>

                <div class="d-flex align-center mt-1">
                  <VIcon :icon="item.userdata?.favorite ? 'bx-heart' : 'bx-heart-circle'" size="small" class="me-1"
                    :color="item.userdata?.favorite ? 'error' : 'grey'" />
                  <span>{{ item.userdata?.favorite ? t('pages.mediaitem.favorite') : t('pages.mediaitem.notFavorite')
                  }}</span>
                </div>
              </div>
            </div>
          </div>
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
            <v-select v-model="itemsPerPage" :items="itemsPerPageOptions" density="compact" style="width: 80px"
              hide-details variant="plain" />
            <div class="ms-4 text-caption text-grey">
              {{ t('pages.mediaitem.totalItems', { count: totalItems }) }}
            </div>
          </div>

          <v-pagination v-model="mediaItemStore.currentPage" :length="totalPages" @update:model-value="changePage"
            :total-visible="5" :show-first-last-page="false" />
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

/* Media Card Styling */
.media-card {
  aspect-ratio: 2/3;
  transition: transform 0.2s;
  cursor: pointer;
  overflow: hidden;
  position: relative;
}

.media-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

/* Poster Background Styling */
.poster-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.05);
  background-size: cover;
  background-position: right center;
  display: flex;
  flex-direction: column;
}

/* Content Overlay Styling */
.content-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 16px;
  overflow: hidden;
  background: linear-gradient(to bottom, rgba(0, 0, 0, 0.7) 0%, transparent 30%, transparent 70%, rgba(0, 0, 0, 0.8) 100%);
}

.media-title {
  font-weight: bold;
  font-size: 1.1rem;
  margin-bottom: 8px;
  line-height: 1.3;
  max-height: 30%;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  color: #ffffff;
  text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.8);
}

.media-info {
  margin-top: auto;
  overflow: hidden;
  color: #ffffff;
  text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(2px);
  padding: 8px;
  border-radius: 4px;
  background-color: rgba(0, 0, 0, 0.4);
}

/* 分页样式 */
:deep(.v-pagination__list) {
  max-width: 100%;
  overflow-x: auto;
}

:deep(.v-pagination__item) {
  min-width: 34px;
}

/* Sort dropdown styles */
.sort-dropdown {
  width: 100%;
}

.sort-btn {
  width: 100%;
  justify-content: flex-start;
  text-align: left;
  height: 38px;
  border-radius: 4px;
  padding: 0 16px;
}

.sort-menu-card {
  width: 100%;
}

.sort-list-item {
  padding-left: 16px;
  padding-right: 16px;
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

.filter-dropdown {
  width: 100%;
  min-width: 0;
}
</style>
