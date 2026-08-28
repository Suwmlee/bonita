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
    await metadataStore.getMetadata(searchQuery.value, 1, value)
  },
})
const totalPages = computed(() =>
  Math.ceil(totalItems.value / itemsPerPage.value),
)
const itemsPerPageOptions = [12, 24, 48, 96]

function showEditDialog(item: MetadataPublic) {
  metadataStore.showUpdateMetadata(item)
}

// Function to show the add metadata dialog
function showAddDialog() {
  metadataStore.showAddMetadata()
}

const imageUrlCache = new Map<string, string>()

function getImageUrl(path: string) {
  const cached = imageUrlCache.get(path)
  if (cached) return cached
  const url = `${OpenAPI.BASE}/api/v1/resource/image?path=${encodeURIComponent(path)}&t=${Date.now()}`
  imageUrlCache.set(path, url)
  return url
}

const COVER_RATIO = 16 / 10
const COVER_RATIO_TOLERANCE = 0.12
const coverLetterbox = ref<Record<number, boolean>>({})

function onCoverLoad(event: Event, id: number) {
  const img = event.target as HTMLImageElement
  if (!img.naturalWidth || !img.naturalHeight) return
  const ratio = img.naturalWidth / img.naturalHeight
  const mismatch = Math.abs(ratio - COVER_RATIO) / COVER_RATIO
  coverLetterbox.value[id] = mismatch >= COVER_RATIO_TOLERANCE
}

// Function to search metadata with filter
async function searchMetadata() {
  isSearching.value = true
  try {
    await metadataStore.getMetadata(searchQuery.value, 1)
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
    hour12: false,
  })
}

const tagColorMap = {
  中文字幕: "#FF0000",
  破解: "#FFA500",
} as const

const tagColorPalette = [
  "primary",
  "success",
  "info",
  "warning",
  "error",
  "secondary",
]

function parseTags(tag: string | null | undefined): string[] {
  if (!tag) return []
  return tag
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
}

function getTagColor(tag: string): string {
  const trimmed = tag.trim()
  if (trimmed in tagColorMap) {
    return tagColorMap[trimmed as keyof typeof tagColorMap]
  }

  let hash = 0
  for (let i = 0; i < trimmed.length; i++) {
    hash = (hash << 5) - hash + trimmed.charCodeAt(i)
    hash |= 0
  }
  return tagColorPalette[Math.abs(hash) % tagColorPalette.length]
}

// Watch for changes in search query
watch(searchQuery, async (newValue) => {
  if (newValue === "") {
    await metadataStore.getMetadata("", 1)
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

    <VRow align="stretch">
      <VCol v-for="item in metadataStore.allMetadata" :key="item.id" cols="12" sm="6" md="4" lg="3" xl="2" class="d-flex">
        <VCard class="metadata-card" @click="showEditDialog(item)">
          <div class="card-header">
            <span class="card-number text-truncate" :title="item.number">{{ item.number }}</span>
            <VBtn icon variant="text" size="small" class="delete-btn"
              @click.stop="metadataStore.confirmDeleteMetadata(item.id)">
              <VIcon icon="bx-trash" size="18" color="error" />
            </VBtn>
          </div>

          <div class="cover-wrapper" :class="{ 'show-full': coverLetterbox[item.id] }">
            <template v-if="item.cover">
              <img
                v-if="coverLetterbox[item.id]"
                class="cover-fill"
                :src="getImageUrl(item.cover)"
                alt=""
                aria-hidden="true"
              />
              <img
                class="cover-image"
                :src="getImageUrl(item.cover)"
                :alt="item.title"
                loading="lazy"
                @load="onCoverLoad($event, item.id)"
              />
            </template>
            <div v-else class="cover-placeholder">
              <VIcon icon="bx-image" size="36" />
            </div>
          </div>

          <div class="card-body">
            <p class="card-title" :title="item.title">{{ item.title }}</p>
            <div class="card-meta">
              <span v-if="item.actor" class="card-actor" :title="item.actor">{{ item.actor }}</span>
              <div v-if="parseTags(item.tag).length" class="tag-list">
                <VChip
                  v-for="tag in parseTags(item.tag)"
                  :key="tag"
                  :color="getTagColor(tag)"
                  variant="flat"
                  size="small"
                  class="tag-chip"
                >
                  {{ tag }}
                </VChip>
              </div>
            </div>
            <p class="card-time">{{ formatDateTime(item.updatetime) }}</p>
          </div>
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

    <!-- Metadata add/edit dialog -->
    <MetadataDetailDialog />
  </div>
</template>

<style scoped>
.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.metadata-card {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
}

.metadata-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.12);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  min-height: 44px;
  padding: 4px 4px 4px 12px;
  flex-shrink: 0;
}

.card-number {
  font-weight: 600;
  font-size: 1.1rem;
  line-height: 1.3;
  letter-spacing: 0.03em;
}

.delete-btn {
  opacity: 0.55;
}

.metadata-card:hover .delete-btn {
  opacity: 1;
}

.cover-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background-color: #1a1a1a;
  flex-shrink: 0;
}

.cover-fill,
.cover-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.cover-fill {
  object-fit: cover;
  object-position: center;
  filter: blur(20px) saturate(1.1) brightness(0.65);
  transform: scale(1.2);
}

.cover-image {
  object-fit: cover;
  object-position: center;
  z-index: 1;
}

.cover-wrapper.show-full .cover-image {
  object-fit: contain;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.35);
}

.card-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 156px;
  padding: 12px;
}

.card-title {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.7em;
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.35;
  color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
}

.card-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 70px;
  margin-top: 10px;
}

.card-actor {
  max-width: 100%;
  font-size: 0.8125rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  min-height: 44px;
  max-height: 44px;
  overflow: hidden;
}

.tag-chip {
  font-size: 12px;
  height: 20px;
  flex: 0 0 auto;
}

.v-chip.tag-chip :deep(.v-chip__content) {
  padding: 0 4px;
  line-height: 20px;
}

.card-time {
  margin: auto 0 0;
  padding-top: 8px;
  font-size: 0.75rem;
  color: rgba(var(--v-theme-on-surface), 0.38);
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
