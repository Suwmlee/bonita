<script setup lang="ts">
import type { ActorPublic, ActorSummary, MetadataPublic } from "@/client"
import MetadataActorEditDialog from "@/components/metadata/MetadataActorEditDialog.vue"
import MetadataActorWall from "@/components/metadata/MetadataActorWall.vue"
import MetadataDetailDialog from "@/components/metadata/MetadataDetailDialog.vue"
import MetadataRefreshDialog from "@/components/metadata/MetadataRefreshDialog.vue"
import { useMetadataStore } from "@/stores/metadata.store"
import { actorGradient, actorInitial } from "@/utils/actorVisual"
import { resourceImageUrl } from "@/utils/resourceImage"
import { computed, onMounted, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

const VIEW_MODE_KEY = "metadata-view-mode"
const ACTOR_SORT_KEY = "metadata-actor-sort"

const metadataStore = useMetadataStore()
const searchQuery = ref("")
const isSearching = ref(false)
const viewMode = ref<"number" | "actor">(
  localStorage.getItem(VIEW_MODE_KEY) === "actor" ? "actor" : "number",
)
type ActorSort = "count_desc" | "count_asc" | "name_asc" | "name_desc"

function loadActorSort(): ActorSort {
  const saved = localStorage.getItem(ACTOR_SORT_KEY)
  if (
    saved === "count_asc"
    || saved === "count_desc"
    || saved === "name_asc"
    || saved === "name_desc"
  ) {
    return saved
  }
  // 兼容早期本地缓存
  if (saved === "name") return "name_asc"
  return "count_desc"
}

const actorSort = ref<ActorSort>(loadActorSort())
const actorSortOpen = ref(false)
const actors = ref<ActorSummary[]>([])
const actorTotal = ref(0)
const actorPage = ref(1)
const selectedActor = ref<ActorSummary | null>(null)
const actorWorks = ref<MetadataPublic[]>([])
const actorWorksTotal = ref(0)
const actorWorksPage = ref(1)
const heroPhotoBroken = ref(false)
const heroCoverBroken = ref<Record<string, boolean>>({})
const showActorEditDialog = ref(false)
const { t } = useI18n()

const viewModeOptions = computed(() => [
  { value: "number" as const, title: t("pages.metadata.viewByNumber") },
  { value: "actor" as const, title: t("pages.metadata.viewByActor") },
])

const actorSortField = computed(() => (actorSort.value.startsWith("count") ? "count" : "name"))
const actorSortDirection = computed(() => (actorSort.value.endsWith("asc") ? "asc" : "desc"))
const actorSortOptions = computed(() => [
  { value: "count" as const, title: t("pages.metadata.sortByCount") },
  { value: "name" as const, title: t("pages.metadata.sortByName") },
])
const actorSortLabel = computed(
  () => actorSortOptions.value.find(option => option.value === actorSortField.value)?.title ?? "",
)

function actorSortIcon() {
  if (actorSortField.value === "name") {
    return actorSortDirection.value === "desc" ? "bx-sort-a-z" : "bx-sort-z-a"
  }
  return actorSortDirection.value === "desc" ? "bx-sort-down" : "bx-sort-up"
}

function handleActorSort(field: "count" | "name") {
  const nextDirection =
    field === actorSortField.value && actorSortDirection.value === "desc"
      ? "asc"
      : "desc"
  actorSort.value = `${field}_${nextDirection}` as ActorSort
  actorSortOpen.value = false
}

function keyword() {
  return typeof searchQuery.value === "string" ? searchQuery.value.trim() : ""
}

async function fetchMetadata(page: number, perPage?: number) {
  isSearching.value = true
  try {
    const result = await metadataStore.getMetadata(keyword(), page, perPage)
    if (result !== null) isSearching.value = false
  } catch {
    isSearching.value = false
  }
}

async function fetchActors(page: number, perPage?: number) {
  isSearching.value = true
  try {
    const result = await metadataStore.getActors(keyword(), page, perPage, actorSort.value)
    if (result === null) return
    actors.value = result.data
    actorTotal.value = result.count
    actorPage.value = page
    isSearching.value = false
  } catch {
    isSearching.value = false
  }
}

async function fetchWorks(page: number, perPage?: number) {
  if (!selectedActor.value) return
  isSearching.value = true
  try {
    const result = await metadataStore.getActorWorks(
      selectedActor.value.name,
      keyword(),
      page,
      perPage,
      selectedActor.value.id,
    )
    if (result === null) return
    actorWorks.value = result.data
    actorWorksTotal.value = result.count
    actorWorksPage.value = page
    selectedActor.value = { ...selectedActor.value, count: result.count }
    isSearching.value = false
  } catch {
    isSearching.value = false
  }
}

async function refreshCurrent(page?: number, perPage?: number) {
  if (viewMode.value === "number") {
    await fetchMetadata(page ?? metadataStore.currentPage, perPage)
    return
  }
  if (selectedActor.value) {
    await fetchWorks(page ?? actorWorksPage.value, perPage)
    if (actorWorksTotal.value === 0) {
      selectedActor.value = null
      await fetchActors(1, perPage)
      return
    }
    if (actorWorks.value.length === 0 && actorWorksPage.value > 1) {
      await fetchWorks(actorWorksPage.value - 1, perPage)
    }
    return
  }
  await fetchActors(page ?? actorPage.value, perPage)
  if (actors.value.length === 0 && actorPage.value > 1 && actorTotal.value > 0) {
    await fetchActors(actorPage.value - 1, perPage)
  }
}

const itemsPerPage = computed({
  get: () => metadataStore.itemsPerPage,
  set: async (value) => {
    await refreshCurrent(1, value)
  },
})
const pagingTotal = computed(() => {
  if (viewMode.value === "number") return metadataStore.totalCount
  if (selectedActor.value) return actorWorksTotal.value
  return actorTotal.value
})
const pagingPage = computed(() => {
  if (viewMode.value === "number") return metadataStore.currentPage
  if (selectedActor.value) return actorWorksPage.value
  return actorPage.value
})
const totalPages = computed(() =>
  Math.max(1, Math.ceil(pagingTotal.value / itemsPerPage.value)),
)
const totalLabel = computed(() => {
  if (viewMode.value === "actor" && !selectedActor.value) {
    return t("pages.metadata.totalActors", { count: actorTotal.value })
  }
  return t("pages.metadata.totalItems", { count: pagingTotal.value })
})
const visibleItems = computed(() =>
  viewMode.value === "actor" ? actorWorks.value : metadataStore.allMetadata,
)
const showItemGrid = computed(() => viewMode.value === "number" || !!selectedActor.value)
const showEmpty = computed(() => {
  if (isSearching.value) return false
  if (viewMode.value === "number") return metadataStore.allMetadata.length === 0
  if (selectedActor.value) return actorWorks.value.length === 0
  return actors.value.length === 0
})
const emptyText = computed(() =>
  viewMode.value === "actor" && !selectedActor.value
    ? t("pages.metadata.noActors")
    : t("pages.metadata.noResults"),
)
const heroCovers = computed(() =>
  (selectedActor.value?.covers ?? []).filter((cover) => cover.path && !heroCoverBroken.value[cover.path]),
)
const showHeroPhoto = computed(() =>
  Boolean(selectedActor.value?.photo) && !heroPhotoBroken.value,
)
const itemsPerPageOptions = [12, 24, 48, 96]

function showEditDialog(item: MetadataPublic) {
  metadataStore.showUpdateMetadata(item)
}

// Function to show the add metadata dialog
function showAddDialog() {
  metadataStore.showAddMetadata()
}

function openActor(actor: ActorSummary) {
  heroPhotoBroken.value = false
  heroCoverBroken.value = {}
  selectedActor.value = actor
  window.scrollTo({ top: 0, behavior: "smooth" })
  fetchWorks(1)
}

function backToActors() {
  selectedActor.value = null
  window.scrollTo({ top: 0, behavior: "smooth" })
}

function markHeroCoverBroken(cover: string) {
  heroCoverBroken.value = { ...heroCoverBroken.value, [cover]: true }
}

function openActorEdit() {
  if (!selectedActor.value?.id) return
  showActorEditDialog.value = true
}

async function onActorSaved(actor: ActorPublic) {
  if (!selectedActor.value) return
  const primary = actor.name.toLowerCase()
  selectedActor.value = {
    ...selectedActor.value,
    id: actor.id,
    name: actor.name,
    photo: actor.photo ?? selectedActor.value.photo,
    aliases: (actor.aliases ?? [])
      .map((item) => item.name)
      .filter((name) => name.trim().toLowerCase() !== primary),
  }
  heroPhotoBroken.value = false
  await fetchWorks(1)
}

async function changePage(page: number) {
  if (viewMode.value === "number") {
    await fetchMetadata(page)
    return
  }
  if (selectedActor.value) {
    await fetchWorks(page)
    return
  }
  await fetchActors(page)
}

async function onDelete(id: number) {
  const removed = await metadataStore.confirmDeleteMetadata(id)
  if (removed) await refreshCurrent()
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

watch(searchQuery, () => {
  selectedActor.value = null
  if (viewMode.value === "actor") fetchActors(1)
  else fetchMetadata(1)
})

watch(viewMode, (mode) => {
  localStorage.setItem(VIEW_MODE_KEY, mode)
  selectedActor.value = null
  if (mode === "actor") fetchActors(1)
  else fetchMetadata(1)
})

watch(actorSort, (sort) => {
  localStorage.setItem(ACTOR_SORT_KEY, sort)
  if (viewMode.value === "actor" && !selectedActor.value) fetchActors(1)
})

watch(
  () => metadataStore.showDialog,
  (open, wasOpen) => {
    if (wasOpen && !open && viewMode.value === "actor") refreshCurrent()
  },
)

watch(
  () => metadataStore.showRefreshDialog,
  (open, wasOpen) => {
    if (wasOpen && !open && viewMode.value === "actor") refreshCurrent()
  },
)

onMounted(() => {
  if (viewMode.value === "actor") fetchActors(1)
  else fetchMetadata(metadataStore.currentPage)
})
</script>

<template>
  <div>
    <p class="text-xl mb-6">
      {{ t('pages.metadata.title') }}
    </p>

    <VRow class="mb-4 align-center">
      <VCol cols="12" md="5" lg="4">
        <VTextField v-model="searchQuery" :placeholder="t('pages.metadata.search')" clearable hide-details
          prepend-inner-icon="bx-search" :loading="isSearching" variant="outlined" density="comfortable" />
      </VCol>
      <VCol cols="12" md="7" lg="8" class="d-flex align-center flex-wrap ga-3">
        <VSelect
          v-model="viewMode"
          :items="viewModeOptions"
          item-title="title"
          item-value="value"
          variant="outlined"
          density="comfortable"
          hide-details
          class="mode-select"
        />
        <VMenu
          v-if="viewMode === 'actor' && !selectedActor"
          v-model="actorSortOpen"
          location="bottom start"
          :offset="4"
        >
          <template #activator="{ props }">
            <VBtn v-bind="props" variant="outlined" density="comfortable" class="mode-btn">
              <VIcon :icon="actorSortIcon()" size="18" class="me-2" />
              <span class="text-truncate">{{ actorSortLabel }}</span>
            </VBtn>
          </template>
          <VCard class="sort-menu-card">
            <VList density="compact">
              <VListItem
                v-for="option in actorSortOptions"
                :key="option.value"
                class="sort-list-item"
                @click="handleActorSort(option.value)"
              >
                <VListItemTitle>
                  {{ option.title }}
                  <VIcon
                    v-if="option.value === actorSortField"
                    size="small"
                    class="ms-2"
                    :icon="actorSortDirection === 'desc' ? 'bx-down-arrow-alt' : 'bx-up-arrow-alt'"
                  />
                </VListItemTitle>
              </VListItem>
            </VList>
          </VCard>
        </VMenu>
        <VSpacer class="d-none d-md-block" />
        <VBtn color="primary" @click="showAddDialog" prepend-icon="bx-plus">
          {{ t('pages.metadata.addNew') }}
        </VBtn>
      </VCol>
    </VRow>

    <div v-if="selectedActor" class="actor-hero mb-6">
      <div class="hero-bg" :style="{ background: actorGradient(selectedActor.name) }">
        <div v-if="heroCovers.length" class="hero-mosaic">
          <img
            v-for="cover in heroCovers"
            :key="cover.path"
            :class="{ 'hero-full': cover.crop === false }"
            :src="resourceImageUrl(cover.path, { number: cover.number })"
            alt=""
            @error="markHeroCoverBroken(cover.path)"
          />
        </div>
      </div>
      <div class="hero-shade" />
      <div class="hero-content">
        <VBtn
          icon
          variant="flat"
          class="hero-back"
          :title="t('pages.metadata.backToActors')"
          @click="backToActors"
        >
          <VIcon icon="bx-chevron-left" size="28" />
        </VBtn>
        <div class="hero-avatar" :style="{ background: actorGradient(selectedActor.name) }">
          <span>{{ actorInitial(selectedActor.name) }}</span>
          <img
            v-if="showHeroPhoto"
            :src="resourceImageUrl(selectedActor.photo || '', { actor: selectedActor.name })"
            :alt="selectedActor.name"
            @error="heroPhotoBroken = true"
          />
        </div>
        <div class="hero-text">
          <div class="hero-name-row">
            <p class="hero-name">{{ selectedActor.name }}</p>
            <VBtn
              v-if="selectedActor.id"
              icon
              variant="text"
              size="small"
              class="hero-edit"
              :title="t('pages.metadata.editActor')"
              @click="openActorEdit"
            >
              <VIcon icon="bx-edit-alt" size="20" />
            </VBtn>
          </div>
          <p
            v-if="(selectedActor.aliases ?? []).length"
            class="hero-aliases"
            :title="(selectedActor.aliases ?? []).join(' / ')"
          >
            {{ (selectedActor.aliases ?? []).join(' / ') }}
          </p>
          <p
            v-if="(selectedActor.homonym_count ?? 1) > 1"
            class="hero-homonym"
          >
            {{ t('pages.metadata.homonymHint') }}
          </p>
          <p class="hero-sub">{{ t('pages.metadata.workCount', { count: selectedActor.count }) }}</p>
        </div>
      </div>
    </div>

    <MetadataActorEditDialog
      v-model="showActorEditDialog"
      :actor="selectedActor"
      @saved="onActorSaved"
    />
    <MetadataActorWall
      v-if="viewMode === 'actor' && !selectedActor"
      :actors="actors"
      @select="openActor"
    />

    <VRow v-if="showItemGrid" align="stretch">
      <VCol v-for="item in visibleItems" :key="item.id" cols="12" sm="6" md="4" lg="3" xl="2" class="d-flex">
        <VCard class="metadata-card" @click="showEditDialog(item)">
          <div class="card-header">
            <span class="card-number text-truncate" :title="item.number">{{ item.number }}</span>
            <div class="card-actions">
              <VBtn icon variant="text" size="small" class="action-btn"
                :title="t('pages.metadata.refresh')"
                @click.stop="metadataStore.showRefreshMetadata(item)">
                <VIcon icon="bx-refresh" size="18" />
              </VBtn>
              <VBtn icon variant="text" size="small" class="action-btn"
                @click.stop="onDelete(item.id)">
                <VIcon icon="bx-trash" size="18" color="error" />
              </VBtn>
            </div>
          </div>

          <div class="cover-wrapper">
            <template v-if="item.cover">
              <img
                class="cover-fill"
                :src="resourceImageUrl(item.cover, { number: item.number })"
                alt=""
                aria-hidden="true"
              />
              <img
                class="cover-image"
                :src="resourceImageUrl(item.cover, { number: item.number })"
                :alt="item.title"
                loading="lazy"
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

    <VRow v-if="showEmpty" class="mt-5">
      <VCol class="text-center">
        <p class="text-medium-emphasis">{{ emptyText }}</p>
      </VCol>
    </VRow>

    <VRow v-if="pagingTotal > 0" class="mt-5">
      <VCol>
        <div class="d-flex align-center justify-end px-4 py-3 w-100">
          <div class="d-flex align-center me-4">
            <span class="text-caption text-grey me-2">{{ t('pages.metadata.itemsPerPage') }}</span>
            <v-select v-model="itemsPerPage" :items="itemsPerPageOptions" density="compact"
              style="width: 80px" hide-details variant="plain" />
            <div class="ms-4 text-caption text-grey">
              {{ totalLabel }}
            </div>
          </div>

          <v-pagination :model-value="pagingPage"
            :length="totalPages"
            @update:model-value="changePage"
            :total-visible="5"
            :show-first-last-page="false" />
        </div>
      </VCol>
    </VRow>

    <MetadataDetailDialog @created="refreshCurrent(1)" />
    <MetadataRefreshDialog
      v-model="metadataStore.showRefreshDialog"
      :metadata="metadataStore.refreshTarget"
    />
  </div>
</template>

<style scoped>
.mode-select,
.mode-btn {
  flex: 0 0 108px;
  width: 108px;
  max-width: 108px;
}

.mode-btn {
  height: 38px;
  justify-content: flex-start;
  border-radius: 6px;
  padding-inline: 10px;
}

.sort-menu-card {
  width: 108px;
}

.sort-list-item {
  padding-inline: 12px;
}

.actor-hero {
  position: relative;
  height: 196px;
  border-radius: 18px;
  overflow: hidden;
  background: #141414;
}

.hero-bg,
.hero-mosaic,
.hero-shade {
  position: absolute;
  inset: 0;
}

.hero-mosaic {
  display: flex;
}

.hero-mosaic img {
  flex: 1;
  width: 0;
  height: 100%;
  object-fit: cover;
  object-position: right center;
  filter: blur(16px) saturate(1.15);
  transform: scale(1.18);
}

.hero-mosaic img.hero-full {
  object-position: center;
}

.hero-shade {
  background: linear-gradient(90deg, rgba(0, 0, 0, 0.62), rgba(0, 0, 0, 0.28));
}

.hero-content {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 28px;
  color: #fff;
}

.hero-back {
  flex-shrink: 0;
  background: rgba(0, 0, 0, 0.35) !important;
  color: #fff !important;
}

.hero-avatar {
  position: relative;
  width: 112px;
  aspect-ratio: 2 / 3;
  flex-shrink: 0;
  border-radius: 14px;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.92);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  font-weight: 600;
  color: #fff;
}

.hero-avatar img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
}

.hero-name-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.hero-name {
  margin: 0;
  font-size: 1.7rem;
  font-weight: 650;
  line-height: 1.2;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.4);
}

.hero-edit {
  color: rgba(255, 255, 255, 0.78);
}

.hero-edit:hover {
  color: #fff;
}

.hero-aliases {
  margin: 6px 0 0;
  max-width: 100%;
  font-size: 0.85rem;
  line-height: 1.35;
  color: rgba(255, 255, 255, 0.42);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.hero-homonym {
  margin: 6px 0 0;
  font-size: 0.82rem;
  color: rgba(255, 220, 160, 0.9);
}

.hero-sub {
  margin: 8px 0 0;
  font-size: 0.95rem;
  letter-spacing: 0.04em;
  color: rgba(255, 255, 255, 0.84);
}

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

.card-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.action-btn {
  opacity: 0.55;
}

.metadata-card:hover .action-btn {
  opacity: 1;
}

.cover-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 2;
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
  object-fit: contain;
  object-position: center;
  z-index: 1;
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
  .actor-hero {
    height: 180px;
  }

  .hero-content {
    padding: 0 16px;
    gap: 12px;
  }

  .hero-avatar {
    width: 84px;
    font-size: 28px;
  }

  .hero-name {
    font-size: 1.25rem;
  }

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
