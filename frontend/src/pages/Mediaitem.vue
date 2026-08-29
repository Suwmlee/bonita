<script setup lang="ts">
import type { MediaItemWithWatches } from "@/client"
import { OpenAPI, ResourceService } from "@/client"
import MediaItemDetailDialog from "@/components/mediaitem/MediaItemDetailDialog.vue"
import { useMediaItemStore } from "@/stores/mediaitem.store"
import { computed, nextTick, onMounted, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

const VIEW_STATE_KEY = "mediaitem-view-state"
const MEDIA_TYPE_VALUES = ["movie", "tvshow", "number"] as const

type MediaTypeFilter = (typeof MEDIA_TYPE_VALUES)[number] | null
type BooleanFilter = boolean | null

type ViewState = {
  mediaType: MediaTypeFilter
  watched: BooleanFilter
  favorite: BooleanFilter
  sortField: string
  sortDirection: "asc" | "desc"
}

function isBooleanFilter(value: unknown): value is BooleanFilter {
  return value === null || value === true || value === false
}

function isMediaTypeFilter(value: unknown): value is MediaTypeFilter {
  return value === null || MEDIA_TYPE_VALUES.includes(value as (typeof MEDIA_TYPE_VALUES)[number])
}

function loadViewState(): Partial<ViewState> {
  try {
    const raw = localStorage.getItem(VIEW_STATE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as Partial<ViewState>
    const state: Partial<ViewState> = {}
    if (isMediaTypeFilter(parsed.mediaType)) state.mediaType = parsed.mediaType
    if (isBooleanFilter(parsed.watched)) state.watched = parsed.watched
    if (isBooleanFilter(parsed.favorite)) state.favorite = parsed.favorite
    if (
      parsed.sortField === "updatetime" ||
      parsed.sortField === "createtime" ||
      parsed.sortField === "title"
    ) {
      state.sortField = parsed.sortField
    }
    if (parsed.sortDirection === "asc" || parsed.sortDirection === "desc") {
      state.sortDirection = parsed.sortDirection
    }
    return state
  } catch {
    return {}
  }
}

const mediaItemStore = useMediaItemStore()
const searchQuery = ref("")
const isSearching = ref(false)
const viewReady = ref(false)
const { t } = useI18n()

const savedViewState = loadViewState()

// Sort dropdown state
const sortDropdownOpen = ref(false)

// Media type filter with hasNumber options
const selectedMediaType = ref<string | null>(savedViewState.mediaType ?? "number")
const mediaTypeOptions = [
  { value: null, title: t("pages.mediaitem.mediaType") },
  { value: "movie", title: t("pages.mediaitem.movie") },
  { value: "tvshow", title: t("pages.mediaitem.tvshow") },
  { value: "number", title: t("pages.mediaitem.hasNumber") },
]

// Watched filter
const watchedFilter = ref<boolean | null>(savedViewState.watched ?? null)
const watchedOptions = [
  { value: null, title: t("pages.mediaitem.watchedStatus") },
  { value: true, title: t("pages.mediaitem.watched") },
  { value: false, title: t("pages.mediaitem.unwatched") },
]

// Favorite filter
const favoriteFilter = ref<boolean | null>(savedViewState.favorite ?? null)
const favoriteOptions = [
  { value: null, title: t("pages.mediaitem.favoriteStatus") },
  { value: true, title: t("pages.mediaitem.favorite") },
  { value: false, title: t("pages.mediaitem.notFavorite") },
]

// Sort options
const sortField = ref<string>(savedViewState.sortField ?? "updatetime")
const sortDirection = ref<"asc" | "desc">(savedViewState.sortDirection ?? "desc")

const sortOptions = [
  {
    value: "updatetime",
    title: t("pages.mediaitem.sortUpdatetime"),
    icon: "bx-sort",
  },
  {
    value: "createtime",
    title: t("pages.mediaitem.sortCreatetime"),
    icon: "bx-sort",
  },
  {
    value: "title",
    title: t("pages.mediaitem.sortTitle"),
    icon: "bx-sort",
  },
]

// Handle sort selection
function handleSortChange(value: string) {
  // If selecting the same field, toggle direction
  if (value === sortField.value) {
    sortDirection.value = sortDirection.value === "desc" ? "asc" : "desc"
  } else {
    // If selecting a new field, set it with default desc direction
    sortField.value = value
    sortDirection.value = "desc"
  }

  // Close the dropdown
  sortDropdownOpen.value = false

  // Trigger search with new sort params
  fetchMediaItems(1)
}

// Get sort icon based on field and current direction
function getSortIcon(value: string): string {
  if (value !== sortField.value) return "bx-sort"

  if (value === "title") {
    return sortDirection.value === "desc" ? "bx-sort-a-z" : "bx-sort-z-a"
  }

  return sortDirection.value === "desc" ? "bx-sort-down" : "bx-sort-up"
}

// Pagination
const currentPage = computed(() => mediaItemStore.currentPage)
const totalItems = computed(() => mediaItemStore.totalCount)
const itemsPerPage = computed({
  get: () => mediaItemStore.itemsPerPage,
  set: async (value) => {
    await fetchMediaItems(1, value)
  },
})
const totalPages = computed(() =>
  Math.ceil(totalItems.value / itemsPerPage.value),
)
const itemsPerPageOptions = [20, 30, 40, 80]

// Function to extract media type, hasNumber from combined selection
function getMediaTypeValue(): string | undefined {
  if (!selectedMediaType.value) return undefined
  if (selectedMediaType.value === "number") return undefined
  return selectedMediaType.value
}

// Function to extract hasNumber value from combined selection
function getHasNumberValue(): boolean | undefined {
  if (selectedMediaType.value === "number") return true
  if (
    selectedMediaType.value === "movie" ||
    selectedMediaType.value === "tvshow"
  )
    return false
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

function persistViewState() {
  const state: ViewState = {
    mediaType: selectedMediaType.value as MediaTypeFilter,
    watched: watchedFilter.value,
    favorite: favoriteFilter.value,
    sortField: sortField.value,
    sortDirection: sortDirection.value,
  }
  localStorage.setItem(VIEW_STATE_KEY, JSON.stringify(state))
}

// Function to search media items with filters
async function fetchMediaItems(page: number, perPage?: number) {
  isSearching.value = true
  try {
    await mediaItemStore.getMediaItems(
      searchQuery.value,
      page,
      perPage,
      getMediaTypeValue(),
      sortField.value || undefined,
      sortDirection.value === "desc",
      getHasNumberValue(),
      watchedFilter.value === null ? undefined : watchedFilter.value,
      favoriteFilter.value === null ? undefined : favoriteFilter.value,
    )
    persistViewState()
  } finally {
    isSearching.value = false
  }
}

// Change page function
async function changePage(page: number) {
  await fetchMediaItems(page)
}

// Function to clean media items (remove duplicates)
async function cleanMediaItems() {
  await mediaItemStore.cleanMediaItems()
}

const formatDateTime = (dateStr: string | null | undefined) => {
  if (!dateStr) return ""
  return new Date(dateStr).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  })
}

// 获取媒体类型的显示文本
const getMediaTypeLabel = (mediaType: string) => {
  if (mediaType === "movie") {
    return t("pages.mediaitem.typeMovie")
  }
  if (mediaType === "tvshow" || mediaType === "episode") {
    return t("pages.mediaitem.typeTvshow")
  }
  return mediaType
}

const formatSeasonEpisode = (item: MediaItemWithWatches) => {
  const season = item.season_number
  const episode = item.episode_number
  if (season == null || season < 0 || episode == null || episode < 0) {
    return ""
  }
  return `S${String(season).padStart(2, "0")}E${String(episode).padStart(2, "0")}`
}

const getCardTitle = (item: MediaItemWithWatches) => {
  if (item.media_type !== "episode") {
    return item.title
  }
  const parts = [item.original_title, formatSeasonEpisode(item), item.title].filter(
    (part) => part && String(part).trim(),
  )
  return parts.join(" ")
}

// 处理海报URL的函数
const getPosterUrl = (item: MediaItemWithWatches): string => {
  const baseUrl = `${OpenAPI.BASE}/api/v1/resource/poster?`
  const params = new URLSearchParams()
  const isEpisode = item.media_type === "episode"

  params.append(
    "title",
    isEpisode ? item.original_title || item.title : item.title,
  )

  const imdbId = isEpisode ? item.series_imdb_id : item.imdb_id
  if (imdbId) {
    params.append("imdb_id", imdbId)
  }

  const tmdbId = isEpisode ? item.series_tmdb_id : item.tmdb_id
  if (tmdbId) {
    params.append("tmdb_id", tmdbId.toString())
  }

  if (item.number) {
    params.append("number", item.number)
  }

  if (item.updatetime) {
    params.append("t", item.updatetime)
  }

  return baseUrl + params.toString()
}

// Watch for changes in filters
watch(
  [searchQuery, selectedMediaType, watchedFilter, favoriteFilter],
  async () => {
    if (!viewReady.value) return
    await fetchMediaItems(1)
  },
)

onMounted(async () => {
  await fetchMediaItems(1)
  await nextTick()
  viewReady.value = true
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

      <VCol cols="12" sm="6" md="2" lg="2" xl="1">
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

      <VCol cols="12" sm="6" md="2" lg="2" xl="1">
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

      <VCol cols="12" sm="6" md="2" lg="2" xl="1">
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

      <VCol cols="12" sm="6" md="2" lg="2" xl="1">
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
    </VRow>

    <VContainer fluid class="px-2 py-2">
      <div class="custom-grid">
        <div v-for="item in mediaItemStore.allMediaItems" :key="item.id" class="grid-item">
          <VCard class="media-card d-flex flex-column" @click="showEditDialog(item)">
            <div class="poster-wrapper" :class="{ 'show-full': !item.crop }">
              <img
                v-if="!item.crop"
                class="poster-fill"
                :src="getPosterUrl(item)"
                alt=""
                aria-hidden="true"
                loading="lazy"
                decoding="async"
              />
              <img
                class="poster-image"
                :src="getPosterUrl(item)"
                :alt="item.title"
                loading="lazy"
                decoding="async"
              />
              <div class="content-overlay">
                <div class="watched-badge">
                  <VIcon
                    :icon="item.userdata?.watched ? 'bx-check-circle' : 'bx-time'"
                    size="23"
                    :color="item.userdata?.watched ? 'success' : 'warning'"
                  />
                </div>
                <div class="media-info">
                  <div class="media-info-row">
                    <div class="media-info-left">
                      <div v-if="item.number" class="media-number">
                        <VIcon icon="bx-hash" size="small" class="media-number-icon" />
                        <span class="text-truncate" :title="item.number">{{ item.number }}</span>
                      </div>
                      <div v-else-if="item.media_type === 'episode' && formatSeasonEpisode(item)" class="media-number">
                        <VIcon icon="bx-tv" size="small" class="media-number-icon" />
                        <span class="text-truncate">{{ formatSeasonEpisode(item) }}</span>
                      </div>
                      <div v-else-if="item.media_type === 'episode'" class="media-number">
                        <VIcon icon="bx-tv" size="small" class="media-number-icon" />
                        <span class="text-truncate">{{ t('pages.mediaitem.typeSpecial') }}</span>
                      </div>
                      <div v-else class="media-number">
                        <VIcon icon="bx-category" size="small" class="media-number-icon" />
                        <span class="text-truncate">{{ getMediaTypeLabel(item.media_type) }}</span>
                      </div>
                    </div>
                    <div class="media-info-right">
                      <VIcon :icon="item.userdata?.favorite ? 'bx-heart' : 'bx-heart-circle'" size="23"
                        :color="item.userdata?.favorite ? 'error' : 'grey'" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="card-title">
              <VTooltip location="top" open-delay="300">
                <template #activator="{ props }">
                    <span class="text-truncate" v-bind="props">{{ getCardTitle(item) }}</span>
                </template>
                <span>{{ getCardTitle(item) }}</span>
              </VTooltip>
            </div>
          </VCard>
        </div>
      </div>
    </VContainer>

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

/* Custom Grid Layout */
.custom-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  width: 100%;
}

@media (min-width: 600px) {
  .custom-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (min-width: 900px) {
  .custom-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}

@media (min-width: 1200px) {
  .custom-grid {
    grid-template-columns: repeat(7, minmax(0, 1fr));
  }
}

@media (min-width: 1600px) {
  .custom-grid {
    grid-template-columns: repeat(10, minmax(0, 1fr));
  }
}

.grid-item {
  width: 100%;
  min-width: 0;
}

/* Media Card Styling */
.media-card {
  transition: transform 0.2s;
  cursor: pointer;
  overflow: hidden;
  position: relative;
}

.media-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

/* Poster: 2/3 card. Only crop when metadata.crop is true; otherwise show full. */
.poster-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 2/3;
  overflow: hidden;
  background-color: #1a1a1a;
}

.poster-fill,
.poster-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  user-select: none;
}

.poster-fill {
  object-fit: cover;
  object-position: center;
  filter: blur(20px) saturate(1.1) brightness(0.65);
  transform: scale(1.2);
}

.poster-image {
  object-fit: cover;
  object-position: right center;
  z-index: 1;
}

.poster-wrapper.show-full .poster-image {
  object-fit: contain;
  object-position: center;
}

.content-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 10px;
  overflow: hidden;
  background: linear-gradient(to bottom, transparent 0%, transparent 70%, rgba(0, 0, 0, 0.85) 100%);
}

.card-title {
  padding: 6px 8px 8px;
  font-weight: 600;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.media-info {
  margin-top: auto;
  overflow: hidden;
  min-width: 0;
  width: 100%;
  box-sizing: border-box;
  color: #ffffff;
  text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(2px);
  padding: 6px;
  border-radius: 4px;
  background-color: rgba(0, 0, 0, 0.4);
  font-size: 0.75rem;
}

.status-row {
  gap: 8px;
}

/* Bottom info left-right layout */
.media-info-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  min-width: 0;
  width: 100%;
}

.media-info-left {
  min-width: 0;
  overflow: hidden;
}

.media-number {
  display: flex;
  align-items: center;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.media-number-icon {
  flex-shrink: 0;
  margin-right: 4px;
}

.media-number .text-truncate {
  min-width: 0;
  flex: 1;
}

.media-info-right {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 27px;
  height: 27px;
  border-radius: 999px;
  background-color: rgba(0, 0, 0, 0.45);
}

/* Watched badge at top-right of poster */
.watched-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 27px;
  height: 27px;
  border-radius: 999px;
  background-color: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(2px);
  pointer-events: none;
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
  
  .media-info {
    font-size: 0.65rem;
  }
}

.filter-dropdown {
  width: 100%;
  min-width: 0;
}

</style>
