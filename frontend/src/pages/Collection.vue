<script setup lang="ts">
import type { MediaItemWithWatches } from "@/client"
import { OpenAPI } from "@/client"
import type { CollectionPublic, EmbyCollectionCandidate } from "@/client/collection"
import MediaItemDetailDialog from "@/components/mediaitem/MediaItemDetailDialog.vue"
import { useMediaPoster } from "@/composables/useMediaPoster"
import { useCollectionStore } from "@/stores/collection.store"
import { useMediaItemStore } from "@/stores/mediaitem.store"
import { computed, onMounted, ref } from "vue"
import { useI18n } from "vue-i18n"

const { t } = useI18n()
const collectionStore = useCollectionStore()
const mediaItemStore = useMediaItemStore()
const { posterBroken, getDisplayPosterUrl, handlePosterError } = useMediaPoster()

const showAddDialog = ref(false)
const showAddMemberDialog = ref(false)
const embySearch = ref("")
const memberSearch = ref("")

const selected = computed(() => collectionStore.detail)

onMounted(async () => {
  await collectionStore.listCollections()
})

async function openAddDialog() {
  showAddDialog.value = true
  embySearch.value = ""
  await collectionStore.searchEmby("")
}

async function openAddMemberDialog() {
  if (!selected.value) return
  showAddMemberDialog.value = true
  memberSearch.value = ""
  await collectionStore.searchMembers(selected.value.id, "")
}

async function searchEmby() {
  await collectionStore.searchEmby(embySearch.value.trim())
}

async function searchMembers() {
  if (!selected.value) return
  await collectionStore.searchMembers(selected.value.id, memberSearch.value.trim())
}

async function addMemberCandidate(item: MediaItemWithWatches) {
  if (!selected.value) return
  await collectionStore.addMembers(selected.value.id, [item.id], memberSearch.value.trim())
}

async function addCandidate(candidate: EmbyCollectionCandidate) {
  if (candidate.added) {
    const existing = collectionStore.collections.find((item) => item.emby_id === candidate.emby_id)
    showAddDialog.value = false
    if (existing) await collectionStore.loadDetail(existing.id)
    return
  }
  const created = await collectionStore.addCollection(candidate.emby_id, candidate.name)
  if (created) {
    showAddDialog.value = false
    await collectionStore.loadDetail(created.id)
  }
}

async function openCollection(item: CollectionPublic) {
  await collectionStore.loadDetail(item.id)
}

function backToList() {
  collectionStore.clearDetail()
}

function getCollectionPosterUrl(item: { name: string; emby_id: string; image_tag?: string | null }) {
  const params = new URLSearchParams()
  params.append("title", item.name)
  params.append("emby_id", item.emby_id)
  if (item.image_tag) params.append("image_tag", item.image_tag)
  return `${OpenAPI.BASE}/api/v1/resource/poster?${params.toString()}`
}

function getMediaTypeLabel(mediaType: string) {
  if (mediaType === "movie") return t("pages.mediaitem.typeMovie")
  if (mediaType === "tvshow" || mediaType === "episode") return t("pages.mediaitem.typeTvshow")
  return mediaType
}

function formatSeasonEpisode(item: MediaItemWithWatches) {
  const season = item.season_number
  const episode = item.episode_number
  if (season == null || season < 0 || episode == null || episode < 0) return ""
  return `S${String(season).padStart(2, "0")}E${String(episode).padStart(2, "0")}`
}

function getCardTitle(item: MediaItemWithWatches) {
  if (item.media_type !== "episode") return item.title
  return [item.original_title, formatSeasonEpisode(item), item.title]
    .filter((part) => part && String(part).trim())
    .join(" ")
}
</script>

<template>
  <div>
    <template v-if="selected">
      <div class="d-flex align-center mb-6 ga-2 flex-wrap">
        <VBtn variant="text" @click="backToList">
          <VIcon icon="bx-chevron-left" />
        </VBtn>
        <p class="text-xl mb-0 flex-grow-1 text-truncate" :title="selected.name">{{ selected.name }}</p>
        <VBtn variant="outlined" @click="openAddMemberDialog">
          {{ t('pages.collection.addMember') }}
        </VBtn>
        <VBtn
          variant="outlined"
          :loading="collectionStore.isSyncing"
          @click="collectionStore.syncOne(selected.id, 'from_emby')"
        >
          {{ t('pages.collection.pullFromEmby') }}
        </VBtn>
        <VBtn
          variant="outlined"
          :loading="collectionStore.isSyncing"
          @click="collectionStore.syncOne(selected.id, 'to_emby')"
        >
          {{ t('pages.collection.pushToEmby') }}
        </VBtn>
        <VBtn color="error" variant="outlined" @click="collectionStore.removeCollection(selected)">
          {{ t('pages.collection.remove') }}
        </VBtn>
      </div>
      <p class="text-medium-emphasis mb-4">
        {{ t('pages.collection.memberSummary', { matched: selected.matched_count, total: selected.item_count }) }}
      </p>

      <VContainer fluid class="px-2 py-2">
        <div class="custom-grid">
          <div v-for="item in selected.items" :key="item.id" class="grid-item">
            <VCard class="media-card d-flex flex-column" @click="mediaItemStore.showUpdateMediaItem(item)">
              <div class="poster-wrapper" :class="{ 'show-full': !item.crop }">
                <img
                  v-if="!item.crop && !posterBroken[item.id]"
                  class="poster-fill"
                  :src="getDisplayPosterUrl(item)"
                  alt=""
                  aria-hidden="true"
                  loading="lazy"
                  decoding="async"
                  referrerpolicy="no-referrer"
                  @error="handlePosterError(item, $event)"
                />
                <img
                  v-show="!posterBroken[item.id]"
                  class="poster-image"
                  :src="getDisplayPosterUrl(item)"
                  :alt="item.title"
                  loading="lazy"
                  decoding="async"
                  referrerpolicy="no-referrer"
                  @error="handlePosterError(item, $event)"
                />
                <div class="content-overlay">
                  <div class="watched-badge">
                    <VBtn
                      class="remove-member-btn"
                      icon
                      size="x-small"
                      variant="text"
                      @click.stop="collectionStore.removeMember(selected, item)"
                    >
                      <VIcon icon="bx-x" size="20" color="white" />
                    </VBtn>
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
                        <div v-else class="media-number">
                          <VIcon icon="bx-category" size="small" class="media-number-icon" />
                          <span class="text-truncate">{{ getMediaTypeLabel(item.media_type) }}</span>
                        </div>
                      </div>
                      <div class="media-info-right">
                        <VIcon
                          :icon="item.userdata?.favorite ? 'bx-heart' : 'bx-heart-circle'"
                          size="23"
                          :color="item.userdata?.favorite ? 'error' : 'grey'"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="card-title">
                <span class="text-truncate">{{ getCardTitle(item) }}</span>
              </div>
            </VCard>
          </div>
        </div>
      </VContainer>
      <VRow v-if="!collectionStore.isLoading && selected.items.length === 0" class="mt-5">
        <VCol class="text-center">
          <p class="text-medium-emphasis">{{ t('pages.collection.noMembers') }}</p>
        </VCol>
      </VRow>
    </template>

    <template v-else>
      <div class="d-flex align-center mb-6 ga-2 flex-wrap">
        <p class="text-xl mb-0 flex-grow-1">{{ t('pages.collection.title') }}</p>
        <VBtn variant="outlined" :loading="collectionStore.isSyncing" @click="collectionStore.syncAll('from_emby')">
          {{ t('pages.collection.pullFromEmby') }}
        </VBtn>
        <VBtn variant="outlined" :loading="collectionStore.isSyncing" @click="collectionStore.syncAll('to_emby')">
          {{ t('pages.collection.pushToEmby') }}
        </VBtn>
        <VBtn color="primary" @click="openAddDialog">
          {{ t('pages.collection.add') }}
        </VBtn>
      </div>
      <p class="text-medium-emphasis mb-4">{{ t('pages.collection.subtitle') }}</p>

      <VContainer fluid class="px-2 py-2">
        <div class="collection-grid">
          <div v-for="item in collectionStore.collections" :key="item.id" class="grid-item">
            <VCard class="media-card d-flex flex-column" @click="openCollection(item)">
              <div class="poster-wrapper collection-poster">
                <img class="poster-image collection-cover" :src="getCollectionPosterUrl(item)" :alt="item.name" loading="lazy" />
                <div class="content-overlay">
                  <div class="collection-card-name" :title="item.name">{{ item.name }}</div>
                  <div class="media-info">
                    <div class="media-info-row">
                      <div class="media-info-left">
                        <div class="media-number">
                          <VIcon icon="bx-collection" size="small" class="media-number-icon" />
                          <span class="text-truncate">
                            {{ t('pages.collection.memberSummary', { matched: item.matched_count, total: item.item_count }) }}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </VCard>
          </div>
        </div>
      </VContainer>
      <VRow v-if="!collectionStore.isLoading && collectionStore.collections.length === 0" class="mt-5">
        <VCol class="text-center">
          <p class="text-medium-emphasis">{{ t('pages.collection.empty') }}</p>
        </VCol>
      </VRow>
    </template>

    <VDialog v-model="showAddDialog" max-width="760" scrollable>
      <VCard>
        <VCardTitle>{{ t('pages.collection.add') }}</VCardTitle>
        <VCardText>
          <VTextField
            v-model="embySearch"
            :placeholder="t('pages.collection.searchEmby')"
            prepend-inner-icon="bx-search"
            :loading="collectionStore.isSearching"
            hide-details
            clearable
            @keyup.enter="searchEmby"
            @click:clear="searchEmby"
          />
          <VBtn class="mt-3" variant="tonal" :loading="collectionStore.isSearching" @click="searchEmby">
            {{ t('common.search') }}
          </VBtn>
          <VList class="mt-2 picker-list">
            <VListItem
              v-for="candidate in collectionStore.embyCandidates"
              :key="candidate.emby_id"
              class="picker-item"
              @click="addCandidate(candidate)"
            >
              <template #prepend>
                <div class="picker-poster">
                  <img :src="getCollectionPosterUrl(candidate)" :alt="candidate.name" loading="lazy" />
                </div>
              </template>
              <VListItemTitle>{{ candidate.name }}</VListItemTitle>
              <VListItemSubtitle>
                {{ t('pages.collection.embyChildCount', { count: candidate.child_count || 0 }) }}
                <span v-if="candidate.added"> · {{ t('pages.collection.alreadyAdded') }}</span>
              </VListItemSubtitle>
            </VListItem>
          </VList>
          <p v-if="!collectionStore.isSearching && collectionStore.embyCandidates.length === 0" class="text-medium-emphasis mt-4">
            {{ t('pages.collection.noEmbyResults') }}
          </p>
        </VCardText>
        <VCardActions>
          <VSpacer />
          <VBtn variant="text" @click="showAddDialog = false">{{ t('common.cancel') }}</VBtn>
        </VCardActions>
      </VCard>
    </VDialog>

    <VDialog v-model="showAddMemberDialog" max-width="760" scrollable>
      <VCard>
        <VCardTitle>{{ t('pages.collection.addMember') }}</VCardTitle>
        <VCardText>
          <VTextField
            v-model="memberSearch"
            :placeholder="t('pages.collection.searchMembers')"
            prepend-inner-icon="bx-search"
            :loading="collectionStore.isSearchingMembers"
            hide-details
            clearable
            @keyup.enter="searchMembers"
            @click:clear="searchMembers"
          />
          <VBtn class="mt-3" variant="tonal" :loading="collectionStore.isSearchingMembers" @click="searchMembers">
            {{ t('common.search') }}
          </VBtn>
          <VList class="mt-2 picker-list">
            <VListItem
              v-for="item in collectionStore.memberCandidates"
              :key="item.id"
              class="picker-item"
              @click="addMemberCandidate(item)"
            >
              <template #prepend>
                <div class="picker-poster" :class="{ 'show-full': !item.crop }">
                  <img
                    v-if="!item.crop && !posterBroken[item.id]"
                    class="poster-fill"
                    :src="getDisplayPosterUrl(item)"
                    alt=""
                    aria-hidden="true"
                    loading="lazy"
                    decoding="async"
                    referrerpolicy="no-referrer"
                    @error="handlePosterError(item, $event)"
                  />
                  <img
                    v-show="!posterBroken[item.id]"
                    class="poster-image"
                    :src="getDisplayPosterUrl(item)"
                    :alt="item.title"
                    loading="lazy"
                    decoding="async"
                    referrerpolicy="no-referrer"
                    @error="handlePosterError(item, $event)"
                  />
                </div>
              </template>
              <VListItemTitle>{{ getCardTitle(item) }}</VListItemTitle>
              <VListItemSubtitle>
                <span v-if="item.number">{{ item.number }}</span>
                <span v-else-if="item.media_type === 'episode' && formatSeasonEpisode(item)">{{ formatSeasonEpisode(item) }}</span>
                <span v-else>{{ getMediaTypeLabel(item.media_type) }}</span>
              </VListItemSubtitle>
            </VListItem>
          </VList>
          <p v-if="!collectionStore.isSearchingMembers && collectionStore.memberCandidates.length === 0" class="text-medium-emphasis mt-4">
            {{ t('pages.collection.noMemberResults') }}
          </p>
        </VCardText>
        <VCardActions>
          <VSpacer />
          <VBtn variant="text" @click="showAddMemberDialog = false">{{ t('common.cancel') }}</VBtn>
        </VCardActions>
      </VCard>
    </VDialog>

    <MediaItemDetailDialog />
  </div>
</template>

<style scoped>
.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.custom-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
}

@media (min-width: 600px) {
  .custom-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}

@media (min-width: 900px) {
  .custom-grid {
    grid-template-columns: repeat(7, minmax(0, 1fr));
  }
}

@media (min-width: 1200px) {
  .custom-grid {
    grid-template-columns: repeat(8, minmax(0, 1fr));
  }
}

@media (min-width: 1600px) {
  .custom-grid {
    grid-template-columns: repeat(10, minmax(0, 1fr));
  }
}

.collection-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
}

@media (min-width: 600px) {
  .collection-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (min-width: 900px) {
  .collection-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}

@media (min-width: 1200px) {
  .collection-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}

@media (min-width: 1600px) {
  .collection-grid {
    grid-template-columns: repeat(8, minmax(0, 1fr));
  }
}

.grid-item {
  width: 100%;
  min-width: 0;
}

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

.poster-wrapper.collection-poster {
  aspect-ratio: 2 / 3;
}

.poster-image.collection-cover {
  object-fit: cover;
  object-position: center;
}

.poster-wrapper.show-full .poster-image {
  object-fit: contain;
  object-position: center;
}

.collection-card-name {
  color: #fff;
  font-weight: 600;
  font-size: 0.95rem;
  line-height: 1.3;
  text-shadow: 1px 1px 4px rgba(0, 0, 0, 0.85);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
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
}

.media-info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.media-info-left {
  min-width: 0;
  flex: 1;
}

.media-number {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8rem;
}

.media-number-icon {
  flex-shrink: 0;
}

.watched-badge {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 4px;
}

.remove-member-btn {
  opacity: 0;
  background-color: rgba(0, 0, 0, 0.45) !important;
}

.media-card:hover .remove-member-btn {
  opacity: 1;
}

.picker-list {
  background: transparent;
}

.picker-item {
  min-height: 0 !important;
  padding-top: 8px;
  padding-bottom: 8px;
  align-items: center;
}

.picker-item :deep(.v-list-item__prepend) {
  align-self: center;
  width: auto;
  max-width: none;
  margin-inline-end: 16px;
}

.picker-poster {
  position: relative;
  flex-shrink: 0;
  width: 84px;
  aspect-ratio: 2 / 3;
  overflow: hidden;
  border-radius: 6px;
  background-color: #1a1a1a;
}

.picker-poster img {
  display: block;
  width: 100%;
  height: 100%;
}

.picker-poster > img:not(.poster-fill):not(.poster-image) {
  object-fit: cover;
  object-position: center;
}

.picker-poster.show-full .poster-image {
  object-fit: contain;
  object-position: center;
}
</style>
