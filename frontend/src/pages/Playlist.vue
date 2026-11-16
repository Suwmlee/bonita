<script setup lang="ts">
import type {
  PlaylistPublic,
  PlexPlaylistCandidate,
} from "@/stores/playlist.store"
import { usePlaylistStore } from "@/stores/playlist.store"
import { useToastStore } from "@/stores/toast.store"
import { computed, onMounted, ref } from "vue"
import { useI18n } from "vue-i18n"

const { t } = useI18n()
const playlistStore = usePlaylistStore()
const toastStore = useToastStore()

const showAddDialog = ref(false)
const showRebindDialog = ref(false)
const plexSearch = ref("")

const selected = computed(() => playlistStore.detail)

onMounted(async () => {
  await playlistStore.listPlaylists()
})

async function openAddDialog() {
  showAddDialog.value = true
  plexSearch.value = ""
  await playlistStore.searchPlex("")
}

async function openRebindDialog() {
  if (!selected.value) return
  showRebindDialog.value = true
  plexSearch.value = ""
  await playlistStore.searchPlex("")
}

async function searchPlex() {
  await playlistStore.searchPlex(plexSearch.value.trim())
}

async function addCandidate(candidate: PlexPlaylistCandidate) {
  if (candidate.added) {
    const existing = playlistStore.playlists.find(
      (item) => item.external_id === candidate.external_id,
    )
    showAddDialog.value = false
    if (existing) await playlistStore.loadDetail(existing.id)
    return
  }
  const created = await playlistStore.addPlaylist(
    candidate.external_id,
    candidate.rating_key,
    candidate.name,
  )
  if (created) {
    showAddDialog.value = false
    await playlistStore.loadDetail(created.id)
  }
}

function rebindCandidateLabel(candidate: PlexPlaylistCandidate) {
  if (!selected.value) return ""
  if (candidate.external_id === selected.value.external_id) {
    return t("pages.playlist.currentBinding")
  }
  if (candidate.added) return t("pages.playlist.alreadyAdded")
  return ""
}

async function rebindCandidate(candidate: PlexPlaylistCandidate) {
  if (!selected.value) return
  if (candidate.external_id === selected.value.external_id) {
    showRebindDialog.value = false
    return
  }
  if (candidate.added) {
    toastStore.error(t("pages.playlist.rebindConflict") as string)
    return
  }
  const updated = await playlistStore.rebindPlaylist(
    selected.value.id,
    candidate.external_id,
    candidate.rating_key,
    candidate.name,
    true,
  )
  if (updated) showRebindDialog.value = false
}

async function openPlaylist(item: PlaylistPublic) {
  await playlistStore.loadDetail(item.id)
}

function backToList() {
  playlistStore.clearDetail()
}
</script>

<template>
  <div>
    <template v-if="selected">
      <div class="d-flex align-center mb-6 ga-2 flex-wrap">
        <VBtn variant="text" @click="backToList">
          <VIcon icon="bx-chevron-left" />
        </VBtn>
        <p class="text-xl mb-0 flex-grow-1 text-truncate" :title="selected.name">
          {{ selected.name }}
          <span v-if="selected.is_smart" class="text-medium-emphasis text-sm ms-2">
            {{ t("pages.playlist.smartBadge") }}
          </span>
        </p>
        <VBtn
          variant="outlined"
          :loading="playlistStore.isLoading || playlistStore.isSyncing"
          @click="openRebindDialog"
        >
          {{ t("pages.playlist.rebind") }}
        </VBtn>
        <VBtn
          variant="outlined"
          :loading="playlistStore.isSyncing"
          @click="playlistStore.syncOne(selected.id, 'from_server')"
        >
          {{ t("pages.playlist.pullFromServer") }}
        </VBtn>
        <VBtn
          variant="outlined"
          :loading="playlistStore.isSyncing"
          @click="playlistStore.syncOne(selected.id, 'to_server')"
        >
          {{ t("pages.playlist.pushToServer") }}
        </VBtn>
        <VBtn color="error" variant="outlined" @click="playlistStore.removePlaylist(selected)">
          {{ t("pages.playlist.remove") }}
        </VBtn>
      </div>
      <p class="text-medium-emphasis mb-4">
        {{ t("pages.playlist.memberSummary", { count: selected.item_count }) }}
        <template v-if="selected.is_smart">
          · {{ t("pages.playlist.smartPushHint") }}
        </template>
      </p>

      <VList lines="two" class="track-list">
        <VListItem
          v-for="item in selected.items ?? []"
          :key="item.id"
          :title="item.title || t('pages.playlist.untitledTrack')"
          :subtitle="[item.artist, item.album].filter(Boolean).join(' · ')"
        >
          <template #prepend>
            <VAvatar color="surface-variant" variant="tonal" rounded>
              <VIcon icon="bx-music" />
            </VAvatar>
          </template>
          <template #append>
            <span class="text-caption text-medium-emphasis text-truncate path-hint" :title="item.path || ''">
              {{ item.path || item.external_item_id || "" }}
            </span>
          </template>
        </VListItem>
      </VList>
      <VRow v-if="!playlistStore.isLoading && (selected.items?.length ?? 0) === 0" class="mt-5">
        <VCol class="text-center">
          <p class="text-medium-emphasis">{{ t("pages.playlist.noMembers") }}</p>
        </VCol>
      </VRow>
    </template>

    <template v-else>
      <div class="d-flex align-center mb-6 ga-2 flex-wrap">
        <p class="text-xl mb-0 flex-grow-1">{{ t("pages.playlist.title") }}</p>
        <VBtn
          variant="outlined"
          :loading="playlistStore.isSyncing"
          @click="playlistStore.syncAll('from_server')"
        >
          {{ t("pages.playlist.pullFromServer") }}
        </VBtn>
        <VBtn
          variant="outlined"
          :loading="playlistStore.isSyncing"
          @click="playlistStore.syncAll('to_server')"
        >
          {{ t("pages.playlist.pushToServer") }}
        </VBtn>
        <VBtn color="primary" @click="openAddDialog">
          {{ t("pages.playlist.add") }}
        </VBtn>
      </div>
      <p class="text-medium-emphasis mb-4">{{ t("pages.playlist.subtitle") }}</p>

      <VList lines="two">
        <VListItem
          v-for="item in playlistStore.playlists"
          :key="item.id"
          @click="openPlaylist(item)"
        >
          <VListItemTitle>
            {{ item.name }}
            <span v-if="item.is_smart" class="text-medium-emphasis text-caption ms-2">
              {{ t("pages.playlist.smartBadge") }}
            </span>
          </VListItemTitle>
          <VListItemSubtitle>
            {{ t("pages.playlist.memberSummary", { count: item.item_count }) }}
          </VListItemSubtitle>
          <template #prepend>
            <VAvatar color="primary" variant="tonal" rounded>
              <VIcon :icon="item.is_smart ? 'bx-magic-wand' : 'bx-list-ul'" />
            </VAvatar>
          </template>
          <template #append>
            <VIcon icon="bx-chevron-right" />
          </template>
        </VListItem>
      </VList>
      <VRow v-if="!playlistStore.isLoading && playlistStore.playlists.length === 0" class="mt-5">
        <VCol class="text-center">
          <p class="text-medium-emphasis">{{ t("pages.playlist.empty") }}</p>
        </VCol>
      </VRow>
    </template>

    <VDialog v-model="showAddDialog" max-width="760" scrollable>
      <VCard>
        <VCardTitle>{{ t("pages.playlist.add") }}</VCardTitle>
        <VCardText>
          <VTextField
            v-model="plexSearch"
            :placeholder="t('pages.playlist.searchPlex')"
            prepend-inner-icon="bx-search"
            :loading="playlistStore.isSearching"
            hide-details
            clearable
            @keyup.enter="searchPlex"
            @click:clear="searchPlex"
          />
          <VBtn class="mt-3" variant="tonal" :loading="playlistStore.isSearching" @click="searchPlex">
            {{ t("common.search") }}
          </VBtn>
          <VList class="mt-2 picker-list">
            <VListItem
              v-for="candidate in playlistStore.plexCandidates"
              :key="candidate.external_id"
              class="picker-item"
              @click="addCandidate(candidate)"
            >
              <VListItemTitle>
                {{ candidate.name }}
                <span v-if="candidate.smart" class="text-medium-emphasis text-caption ms-2">
                  {{ t("pages.playlist.smartBadge") }}
                </span>
              </VListItemTitle>
              <VListItemSubtitle>
                {{ t("pages.playlist.plexChildCount", { count: candidate.leaf_count || 0 }) }}
                <span v-if="candidate.added"> · {{ t("pages.playlist.alreadyAdded") }}</span>
              </VListItemSubtitle>
            </VListItem>
          </VList>
          <p
            v-if="!playlistStore.isSearching && playlistStore.plexCandidates.length === 0"
            class="text-medium-emphasis mt-4"
          >
            {{ t("pages.playlist.noPlexResults") }}
          </p>
        </VCardText>
        <VCardActions>
          <VSpacer />
          <VBtn variant="text" @click="showAddDialog = false">{{ t("common.cancel") }}</VBtn>
        </VCardActions>
      </VCard>
    </VDialog>

    <VDialog v-model="showRebindDialog" max-width="760" scrollable>
      <VCard>
        <VCardTitle>{{ t("pages.playlist.rebind") }}</VCardTitle>
        <VCardText>
          <p class="text-medium-emphasis mb-3">{{ t("pages.playlist.rebindHint") }}</p>
          <VTextField
            v-model="plexSearch"
            :placeholder="t('pages.playlist.searchPlex')"
            prepend-inner-icon="bx-search"
            :loading="playlistStore.isSearching"
            hide-details
            clearable
            @keyup.enter="searchPlex"
            @click:clear="searchPlex"
          />
          <VBtn class="mt-3" variant="tonal" :loading="playlistStore.isSearching" @click="searchPlex">
            {{ t("common.search") }}
          </VBtn>
          <VList class="mt-2 picker-list">
            <VListItem
              v-for="candidate in playlistStore.plexCandidates"
              :key="candidate.external_id"
              class="picker-item"
              :disabled="!!candidate.added && candidate.external_id !== selected?.external_id"
              @click="rebindCandidate(candidate)"
            >
              <VListItemTitle>
                {{ candidate.name }}
                <span v-if="candidate.smart" class="text-medium-emphasis text-caption ms-2">
                  {{ t("pages.playlist.smartBadge") }}
                </span>
              </VListItemTitle>
              <VListItemSubtitle>
                {{ t("pages.playlist.plexChildCount", { count: candidate.leaf_count || 0 }) }}
                <span v-if="rebindCandidateLabel(candidate)">
                  · {{ rebindCandidateLabel(candidate) }}
                </span>
              </VListItemSubtitle>
            </VListItem>
          </VList>
          <p
            v-if="!playlistStore.isSearching && playlistStore.plexCandidates.length === 0"
            class="text-medium-emphasis mt-4"
          >
            {{ t("pages.playlist.noPlexResults") }}
          </p>
        </VCardText>
        <VCardActions>
          <VSpacer />
          <VBtn variant="text" @click="showRebindDialog = false">{{ t("common.cancel") }}</VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
  </div>
</template>

<style scoped>
.track-list {
  background: transparent;
}
.path-hint {
  max-inline-size: 280px;
}
.picker-list {
  max-block-size: 420px;
  overflow: auto;
}
.picker-item {
  cursor: pointer;
}
</style>
