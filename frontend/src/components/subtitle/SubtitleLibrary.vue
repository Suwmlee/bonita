<script setup lang="ts">
import {
  type MediaItemWithWatches,
  MediaitemService,
  type SubtitleDeliverResult,
  type SubtitlePublic,
  SubtitleService,
} from "@/client"
import type { SubtitleGroupPublic } from "@/client/types.gen"
import PosterFrame from "@/components/common/PosterFrame.vue"
import SubtitleRowActions from "@/components/subtitle/SubtitleRowActions.vue"
import { getPosterUrl } from "@/composables/useMediaPoster"
import { useConfirmationStore } from "@/stores/confirmation.store"
import { useToastStore } from "@/stores/toast.store"
import { watchDebounced } from "@vueuse/core"
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

type MediaOption = {
  id: number
  label: string
  kind: string
  media_type: string
}

const props = defineProps<{
  fixedMediaId?: number
  compact?: boolean
}>()

const emit = defineEmits<{
  count: [value: number]
}>()

const SUBTITLE_EXTENSIONS = new Set([
  ".ass",
  ".srt",
  ".ssa",
  ".vtt",
  ".sub",
  ".idx",
  ".sup",
  ".ttml",
])

const { t } = useI18n()
const toastStore = useToastStore()
const confirmationStore = useConfirmationStore()

const items = ref<SubtitlePublic[]>([])
const groups = ref<SubtitleGroupPublic[]>([])
const posterBroken = ref<Record<string, boolean>>({})
const total = ref(0)
const page = ref(1)
const itemsPerPage = 12
const loading = ref(false)
const uploading = ref(false)
const searchQuery = ref("")
let editOptionsRequestId = 0
let subtitleLoadId = 0
const editMediaId = ref<number | null>(null)
const editSearch = ref("")
const editItems = ref<MediaOption[]>([])
const editMediaLoading = ref(false)
const editMediaField = ref<{ $el?: HTMLElement } | null>(null)
const mediaMenuWidth = ref(488)
const mediaMenuProps = computed(() => ({
  contentClass: "subtitle-media-menu",
  minWidth: mediaMenuWidth.value,
  maxWidth: mediaMenuWidth.value,
}))

async function syncMediaMenuWidth() {
  await nextTick()
  const width = editMediaField.value?.$el?.getBoundingClientRect().width
  if (width && width > 0) mediaMenuWidth.value = Math.round(width)
}

function onMediaMenu(open: boolean) {
  if (open) syncMediaMenuWidth()
}
const unmatchedOnly = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const dragDepth = ref(0)
const dragOver = computed(() => dragDepth.value > 0)
const editOpen = ref(false)
const saving = ref(false)
const editing = ref<SubtitlePublic | null>(null)
const editKey = ref("")
const editLanguage = ref("zh-Hans")
const editPart = ref(0)

const pinned = computed(() => !!props.fixedMediaId)

const languages = computed(() => [
  { title: t("pages.subtitles.lang.zhHans"), value: "zh-Hans" },
  { title: t("pages.subtitles.lang.zhHant"), value: "zh-Hant" },
  { title: t("pages.subtitles.lang.en"), value: "en" },
])

const pageCount = computed(() =>
  Math.max(1, Math.ceil(total.value / itemsPerPage)),
)

watch(total, (value) => emit("count", value))

function languageLabel(language?: string) {
  return (
    languages.value.find((item) => item.value === language)?.title ||
    language ||
    ""
  )
}

function formatPart(part?: number) {
  if (!part) return t("pages.subtitles.noPart")
  return `EP${String(part).padStart(2, "0")}`
}

function formatSize(size?: number | null) {
  if (size == null) return ""
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function formatTime(value?: string | null) {
  if (!value) return ""
  const normalized = value.includes("T") ? value : value.replace(" ", "T")
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return ""
  return date.toLocaleString()
}

function episodeCode(item: {
  season_number?: number | null
  episode_number?: number | null
}) {
  const season = item.season_number
  const episode = item.episode_number
  if (season == null || episode == null || season < 0 || episode < 0) return ""
  return `S${String(season).padStart(2, "0")}E${String(episode).padStart(2, "0")}`
}

function mediaKind(mediaType?: string) {
  if (mediaType === "tvshow") return t("pages.mediaitem.tvshow")
  if (mediaType === "episode") return t("pages.mediaitem.episode")
  if (mediaType === "number") return t("pages.mediaitem.hasNumber")
  if (mediaType === "video") return t("pages.mediaitem.video")
  return t("pages.mediaitem.movie")
}

function mediaOptionLabel(item: {
  media_type?: string
  title?: string | null
  original_title?: string | null
  number?: string | null
  imdb_id?: string | null
  season_number?: number | null
  episode_number?: number | null
}) {
  if (item.media_type === "episode") {
    const show = item.original_title || item.title || ""
    return [episodeCode(item), show].filter(Boolean).join(" ")
  }
  if (item.media_type === "tvshow") return item.title || ""
  if (item.number) {
    const title = item.title && item.title !== item.number ? item.title : ""
    return [item.number, title].filter(Boolean).join(" · ")
  }
  return [item.title || "", item.imdb_id || ""].filter(Boolean).join(" · ")
}

function toOption(item: MediaItemWithWatches): MediaOption {
  return {
    id: item.id,
    media_type: item.media_type,
    label: mediaOptionLabel(item),
    kind: mediaKind(item.media_type),
  }
}

function optionFromSubtitle(item: SubtitlePublic): MediaOption {
  const mediaType = item.media_type || (item.number ? "number" : "movie")
  return {
    id: item.media_item_id || 0,
    media_type: mediaType,
    label: mediaOptionLabel({
      media_type: mediaType,
      title: item.title,
      original_title: item.series_title,
      number: item.number,
      season_number: item.season_number,
      episode_number: item.episode_number,
    }),
    kind: mediaKind(mediaType),
  }
}

function mergeSelected(
  current: MediaOption[],
  incoming: MediaOption[],
  selectedId: number | null,
) {
  const selected = selectedId
    ? current.find((item) => item.id === selectedId)
    : undefined
  const seen = new Set<number>()
  const merged: MediaOption[] = []
  for (const item of selected ? [selected, ...incoming] : incoming) {
    if (seen.has(item.id)) continue
    seen.add(item.id)
    merged.push(item)
  }
  return merged
}

function groupHeading(group: SubtitleGroupPublic) {
  if (!group.media_item_id) return t("pages.subtitles.unmatched")
  if (group.number) return group.number
  return group.title || group.imdb_id || ""
}

function groupSubheading(group: SubtitleGroupPublic) {
  if (!group.media_item_id || !group.number || !group.title) return ""
  if (group.title === group.number) return ""
  return group.title
}

function hasEpisodes(group: SubtitleGroupPublic) {
  return (group.subtitles || []).some((item) => item.media_type === "episode")
}

function apiErrorMessage(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail
  if (typeof detail === "string" && detail.trim()) return detail
  return fallback
}

function deliverSummary(result: SubtitleDeliverResult) {
  const failed = result.failed || 0
  const hasCount = result.copied || result.skipped || result.missing || failed
  const base = hasCount
    ? t("pages.subtitles.deliverResult", { ...result, failed })
    : t("pages.subtitles.deliverNone")
  const details = (result.details || []).filter(Boolean)
  if (!hasCount && details.length) return details.join("；")
  if (details.length) return `${base}。${details.join("；")}`
  return base
}

function searchKeyword() {
  return typeof searchQuery.value === "string" ? searchQuery.value.trim() : ""
}

function groupPosterUrl(group: SubtitleGroupPublic) {
  if (!group.media_item_id) return ""
  const mediaType = group.media_type || (group.number ? "number" : "movie")
  return getPosterUrl({
    media_type: mediaType,
    number: mediaType === "number" ? group.number || "" : "",
    title: group.title || group.number || "",
    imdb_id: group.imdb_id || "",
    tmdb_id: group.tmdb_id || "",
  })
}

async function loadEditOptions(term: string) {
  const requestId = ++editOptionsRequestId
  editMediaLoading.value = true
  try {
    const query = term.trim()
    const { data: response } = await MediaitemService.getMediaItems({
      search: query || undefined,
      limit: 20,
      sort_by: "updatetime",
      sort_desc: true,
      match_external_ids: true,
    })
    if (requestId !== editOptionsRequestId) return
    editItems.value = mergeSelected(
      editItems.value,
      (response.data || []).map(toOption),
      editMediaId.value,
    )
  } catch (error) {
    if (requestId !== editOptionsRequestId) return
    console.error("搜索媒体项失败:", error)
  } finally {
    if (requestId === editOptionsRequestId) editMediaLoading.value = false
  }
}

function markPosterBroken(key: string) {
  posterBroken.value = { ...posterBroken.value, [key]: true }
}

async function load() {
  const requestId = ++subtitleLoadId
  loading.value = true
  try {
    const keyword = searchKeyword()
    if (props.compact || pinned.value) {
      const { data: response } = await SubtitleService.listSubtitles({
        skip: (page.value - 1) * itemsPerPage,
        limit: props.compact ? 50 : itemsPerPage,
        filter: pinned.value ? undefined : keyword || undefined,
        media_item_id: props.fixedMediaId || undefined,
        unmatched: pinned.value ? false : unmatchedOnly.value,
      })
      if (requestId !== subtitleLoadId) return
      items.value = response.data || []
      total.value = response.count || 0
      return
    }
    const { data: response } = await SubtitleService.listSubtitleGroups({
      skip: (page.value - 1) * itemsPerPage,
      limit: itemsPerPage,
      filter: keyword || undefined,
      unmatched: unmatchedOnly.value,
    })
    if (requestId !== subtitleLoadId) return
    groups.value = response.data || []
    total.value = response.count || 0
  } catch (error) {
    if (requestId !== subtitleLoadId) return
    toastStore.error(apiErrorMessage(error, t("pages.subtitles.loadFailed")))
  } finally {
    if (requestId === subtitleLoadId) loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function clearSearch() {
  searchQuery.value = ""
  search()
}

function changePage(value: number) {
  page.value = value
  load()
}

const suppressClick = ref(false)

function chooseFiles() {
  if (suppressClick.value) {
    suppressClick.value = false
    return
  }
  if (uploading.value) return
  fileInput.value?.click()
}

function acceptedSubtitles(files: File[]) {
  return files.filter((file) => {
    const dot = file.name.lastIndexOf(".")
    const extension = dot >= 0 ? file.name.slice(dot).toLowerCase() : ""
    return SUBTITLE_EXTENSIONS.has(extension)
  })
}

function hasDraggedFiles(event: DragEvent) {
  return Array.from(event.dataTransfer?.types || []).includes("Files")
}

function clearDrag() {
  dragDepth.value = 0
  window.removeEventListener("dragend", clearDrag)
  window.removeEventListener("drop", clearDrag)
}

onUnmounted(clearDrag)

function onDragEnter(event: DragEvent) {
  if (!hasDraggedFiles(event)) return
  if (dragDepth.value === 0) {
    window.addEventListener("dragend", clearDrag)
    window.addEventListener("drop", clearDrag)
  }
  dragDepth.value += 1
}

function onDragOver(event: DragEvent) {
  if (event.dataTransfer) event.dataTransfer.dropEffect = "copy"
}

function onDragLeave() {
  dragDepth.value = Math.max(0, dragDepth.value - 1)
}

function onDrop(event: DragEvent) {
  suppressClick.value = true
  clearDrag()
  uploadFiles(Array.from(event.dataTransfer?.files || []))
}

async function onFiles(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ""
  uploadFiles(files)
}

async function uploadFiles(files: File[]) {
  const accepted = acceptedSubtitles(files)
  if (!accepted.length) {
    if (files.length) toastStore.error(t("pages.subtitles.dropEmpty"))
    return
  }
  uploading.value = true
  try {
    const mediaId = props.fixedMediaId || null
    const { data: result } = await SubtitleService.uploadSubtitles({
      bodySubtitleUploadSubtitles: {
        files: accepted,
        number: null,
        media_item_id: mediaId,
      },
    })
    const failed = result.failed?.length || 0
    const saved = result.data?.length || 0
    const replaced = result.replaced || 0
    toastStore.success(
      t("pages.subtitles.uploadResult", {
        created: Math.max(saved - replaced, 0),
        unmatched: result.unmatched || 0,
        replaced,
        failed,
      }),
    )
    page.value = 1
    await load()
  } catch (error) {
    toastStore.error(apiErrorMessage(error, t("pages.subtitles.uploadFailed")))
  } finally {
    uploading.value = false
  }
}

function openEdit(item: SubtitlePublic) {
  editing.value = item
  editKey.value = item.number || ""
  editLanguage.value = item.language || "zh-Hans"
  editPart.value = item.part_number || 0
  editMediaId.value = props.fixedMediaId || item.media_item_id || null
  editSearch.value = ""
  editItems.value =
    !pinned.value && item.media_item_id ? [optionFromSubtitle(item)] : []
  editOpen.value = true
  if (!pinned.value) loadEditOptions("")
}

async function saveEdit() {
  if (!editing.value) return
  saving.value = true
  try {
    await SubtitleService.updateSubtitle({
      subtitle_id: editing.value.id,
      subtitleUpdate: {
        media_item_id: props.fixedMediaId || editMediaId.value,
        number: props.fixedMediaId || editMediaId.value ? "" : editKey.value,
        language: editLanguage.value,
        part_number: Number(editPart.value) || 0,
      },
    })
    editOpen.value = false
    toastStore.success(t("pages.subtitles.saved"))
    await load()
  } catch (error) {
    toastStore.error(apiErrorMessage(error, t("pages.subtitles.saveFailed")))
  } finally {
    saving.value = false
  }
}

async function remove(item: SubtitlePublic) {
  const confirmed = await confirmationStore.openConfirmation({
    title: t("pages.subtitles.deleteTitle"),
    message: t(
      item.preferred
        ? "pages.subtitles.deleteMessageInUse"
        : "pages.subtitles.deleteMessage",
      {
        name: item.original_name,
      },
    ),
    type: "delete",
  })
  if (!confirmed) return
  try {
    await SubtitleService.deleteSubtitle({ subtitle_id: item.id })
    toastStore.success(t("pages.subtitles.deleted"))
    await load()
  } catch (error) {
    toastStore.error(apiErrorMessage(error, t("pages.subtitles.deleteFailed")))
  }
}

async function retransfer(item: SubtitlePublic) {
  try {
    const { data: result } = await SubtitleService.retransferSubtitle({
      subtitle_id: item.id,
    })
    if (result?.started) {
      toastStore.success(t("pages.subtitles.retransferStarted", { count: result.started }))
      return true
    }
    toastStore.info(t("pages.subtitles.retransferNone"))
    return false
  } catch (error) {
    toastStore.error(apiErrorMessage(error, t("pages.subtitles.retransferFailed")))
    return null
  }
}

async function useThis(item: SubtitlePublic) {
  let delivered: SubtitleDeliverResult | undefined
  try {
    const { data: result } = await SubtitleService.preferSubtitle({
      subtitle_id: item.id,
    })
    delivered = result
    await load()
  } catch (error) {
    toastStore.error(apiErrorMessage(error, t("pages.subtitles.deliverFailed")))
    return
  }
  const started = await retransfer(item)
  if (started === false && delivered) {
    toastStore.success(deliverSummary(delivered))
  }
}

watch(
  () => props.fixedMediaId,
  () => {
    page.value = 1
    load()
  },
)

watchDebounced(
  editSearch,
  (term) => {
    if (!editOpen.value || pinned.value) return
    loadEditOptions(term || "")
  },
  { debounce: 300 },
)

onMounted(() => {
  load()
})
</script>

<template>
  <div>
    <div v-if="!compact" class="d-flex align-center justify-space-between mb-4 flex-wrap gap-3">
      <div>
        <h1 class="text-h5">{{ t("pages.subtitles.title") }}</h1>
        <p class="text-body-2 text-medium-emphasis mb-0 mt-1">{{ t("pages.subtitles.hint") }}</p>
      </div>
    </div>

    <div v-if="!compact" class="d-flex align-center flex-wrap gap-3 mb-3">
      <VTextField
        v-if="!compact && !pinned"
        v-model="searchQuery"
        :placeholder="t('pages.subtitles.search')"
        density="compact"
        hide-details
        clearable
        prepend-inner-icon="bx-search"
        style="max-width: 280px"
        @keyup.enter="search"
        @click:clear="clearSearch"
      />
      <VBtn color="primary" prepend-icon="bx-upload" :loading="uploading" @click="chooseFiles">
        {{ t("pages.subtitles.upload") }}
      </VBtn>
      <VBtn v-if="!compact" variant="tonal" prepend-icon="bx-refresh" :loading="loading" @click="load">
        {{ t("common.refresh") }}
      </VBtn>
      <VCheckbox
        v-if="!pinned"
        v-model="unmatchedOnly"
        :label="t('pages.subtitles.unmatchedOnly')"
        density="compact"
        hide-details
        @update:model-value="search"
      />
      <input
        ref="fileInput"
        class="d-none"
        type="file"
        multiple
        accept=".ass,.srt,.ssa,.vtt,.sub,.idx,.sup,.ttml"
        @change="onFiles"
      />
    </div>

    <div v-if="!compact && !pinned" class="subtitle-groups">
      <div v-if="loading && groups.length === 0" class="d-flex justify-center pa-8">
        <VProgressCircular indeterminate color="primary" />
      </div>
      <div v-else-if="groups.length === 0" class="text-medium-emphasis text-center pa-8">
        {{ t("pages.subtitles.empty") }}
      </div>
      <article
        v-for="group in groups"
        :key="group.key"
        class="subtitle-group"
        :class="{ 'with-episode': hasEpisodes(group) }"
      >
        <aside class="subtitle-group-poster">
          <PosterFrame
            v-if="group.media_item_id"
            class="subtitle-poster"
            :src="groupPosterUrl(group)"
            :alt="groupHeading(group)"
            :crop="group.crop"
            :broken="!!posterBroken[group.key]"
            @error="markPosterBroken(group.key)"
          >
            <template #empty>
              <VIcon icon="bx-image" size="small" />
            </template>
          </PosterFrame>
        </aside>
        <div class="subtitle-group-main">
          <div class="subtitle-group-meta">
            <div class="subtitle-group-number">
              {{ groupHeading(group) }}
            </div>
            <div v-if="groupSubheading(group)" class="subtitle-group-title">
              {{ groupSubheading(group) }}
            </div>
            <div class="subtitle-group-count text-caption text-medium-emphasis">
              {{ t("pages.subtitles.groupCount", { count: group.count || group.subtitles?.length || 0 }) }}
            </div>
          </div>
          <div
            v-for="item in group.subtitles || []"
            :key="item.id"
            class="subtitle-group-row"
          >
            <span v-if="hasEpisodes(group)" class="subtitle-group-cell">
              {{ episodeCode(item) }}
            </span>
            <div class="subtitle-group-file">
              <span class="subtitle-group-name">{{ item.original_name }}</span>
              <VChip v-if="item.preferred" size="x-small" color="primary" variant="tonal">
                {{ t("pages.subtitles.inUse") }}
              </VChip>
            </div>
            <span class="subtitle-group-cell">{{ languageLabel(item.language) }}</span>
            <span class="subtitle-group-cell">{{ formatPart(item.part_number) }}</span>
            <span class="subtitle-group-cell">{{ formatSize(item.file_size) }}</span>
            <span class="subtitle-group-cell">{{ formatTime(item.updatetime) }}</span>
            <SubtitleRowActions
              class="subtitle-group-actions"
              :item="item"
              @edit="openEdit(item)"
              @deliver="retransfer(item)"
              @use="useThis(item)"
              @remove="remove(item)"
            />
          </div>
        </div>
      </article>
      <div v-if="groups.length" class="d-flex align-center justify-end px-2 py-3">
        <span class="text-caption text-medium-emphasis me-4">
          {{ t("pages.subtitles.totalGroups", { count: total }) }}
        </span>
        <VPagination
          :model-value="page"
          :length="pageCount"
          :total-visible="5"
          density="compact"
          @update:model-value="changePage"
        />
      </div>
    </div>

    <div v-else-if="compact" class="subtitle-attached">
      <div
        class="subtitle-drop"
        :class="{ 'is-over': dragOver, 'is-busy': uploading }"
        role="button"
        tabindex="0"
        @click="chooseFiles"
        @keydown.enter.prevent="chooseFiles"
        @keydown.space.prevent="chooseFiles"
        @dragenter.prevent="onDragEnter"
        @dragover.prevent="onDragOver"
        @dragleave="onDragLeave"
        @drop.prevent="onDrop"
      >
        <VProgressCircular v-if="uploading" indeterminate size="22" width="2" color="primary" />
        <VIcon v-else icon="bx-cloud-upload" size="28" />
        <span>{{ t("pages.subtitles.dropHint") }}</span>
        <input
          ref="fileInput"
          class="d-none"
          type="file"
          multiple
          accept=".ass,.srt,.ssa,.vtt,.sub,.idx,.sup,.ttml"
          @change="onFiles"
        />
      </div>
      <div v-if="loading && items.length === 0" class="d-flex justify-center py-6">
        <VProgressCircular indeterminate size="24" width="2" color="primary" />
      </div>
      <div v-else-if="items.length === 0" class="subtitle-attached-empty text-medium-emphasis">
        {{ t("pages.subtitles.empty") }}
      </div>
      <div v-else class="subtitle-file-list">
        <div v-for="item in items" :key="item.id" class="subtitle-file">
          <div class="subtitle-file-main">
            <div class="subtitle-file-name">
              <span>{{ item.original_name }}</span>
              <VChip v-if="item.preferred" size="x-small" color="primary" variant="tonal">
                {{ t("pages.subtitles.inUse") }}
              </VChip>
            </div>
            <div class="text-caption text-medium-emphasis">
              <template v-if="episodeCode(item)">
                {{ episodeCode(item) }}
                <span class="mx-1">·</span>
              </template>
              {{ languageLabel(item.language) }}
              <span class="mx-1">·</span>
              {{ formatPart(item.part_number) }}
              <template v-if="formatSize(item.file_size)">
                <span class="mx-1">·</span>
                {{ formatSize(item.file_size) }}
              </template>
            </div>
          </div>
          <SubtitleRowActions
            class="subtitle-file-actions"
            :item="item"
            @edit="openEdit(item)"
            @deliver="retransfer(item)"
            @use="useThis(item)"
            @remove="remove(item)"
          />
        </div>
      </div>
    </div>

    <VDialog v-model="editOpen" max-width="520">
      <VCard>
        <VCardTitle class="pt-5 px-6">{{ t("pages.subtitles.edit") }}</VCardTitle>
        <VCardText class="d-flex flex-column gap-3">
          <VAutocomplete
            v-if="!pinned"
            ref="editMediaField"
            v-model="editMediaId"
            v-model:search="editSearch"
            :items="editItems"
            item-title="label"
            item-value="id"
            no-filter
            clearable
            hide-details
            :loading="editMediaLoading"
            :label="t('pages.subtitles.mediaItem')"
            :menu-props="mediaMenuProps"
            @update:menu="onMediaMenu"
          >
            <template #item="{ props: itemProps, item }">
              <VListItem v-bind="itemProps" :subtitle="item.raw.kind">
                <template #title>
                  <span class="subtitle-media-label" :title="item.raw.label">{{ item.raw.label }}</span>
                </template>
              </VListItem>
            </template>
          </VAutocomplete>
          <VTextField
            v-if="!pinned"
            v-model="editKey"
            :label="t('pages.subtitles.number')"
            :hint="t('pages.subtitles.numberFallback')"
            persistent-hint
            :disabled="!!editMediaId"
          />
          <VSelect
            v-model="editLanguage"
            :items="languages"
            :label="t('pages.subtitles.language')"
            hide-details
          />
          <VTextField
            v-model.number="editPart"
            :label="t('pages.subtitles.part')"
            type="number"
            min="0"
            hide-details
          />
        </VCardText>
        <VCardActions class="px-6 pb-4">
          <VSpacer />
          <VBtn variant="text" @click="editOpen = false">{{ t("common.cancel") }}</VBtn>
          <VBtn color="primary" :loading="saving" @click="saveEdit">{{ t("common.save") }}</VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
  </div>
</template>

<style scoped>
.subtitle-drop {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 88px;
  padding: 16px;
  border: 1px dashed rgba(var(--v-theme-primary), 0.45);
  border-radius: 8px;
  background: rgba(var(--v-theme-primary), 0.04);
  color: rgba(var(--v-theme-on-surface), 0.75);
  cursor: pointer;
  text-align: center;
}

.subtitle-drop.is-over,
.subtitle-drop:focus-visible {
  border-color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.12);
  outline: none;
}

.subtitle-drop.is-busy {
  cursor: progress;
}

.subtitle-attached-empty {
  padding: 20px 8px 8px;
  text-align: center;
}

.subtitle-file-list {
  margin-top: 12px;
}

.subtitle-file {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 8px 0;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.subtitle-file-main {
  min-width: 0;
  flex: 1 1 auto;
}

.subtitle-file-name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.subtitle-file-name span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subtitle-file-actions {
  display: flex;
  flex: 0 0 auto;
}

.subtitle-groups {
  min-width: 0;
}

.subtitle-group {
  display: flex;
  align-items: stretch;
  min-width: 0;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.subtitle-group-poster {
  flex: 0 0 112px;
  width: 112px;
  display: flex;
  align-items: flex-start;
  padding: 8px;
  background: rgba(var(--v-theme-on-surface), 0.04);
  border-inline-end: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.subtitle-poster {
  border-radius: 4px;
}

.subtitle-group-main {
  flex: 1 1 auto;
  min-width: 0;
}

.subtitle-group-meta {
  display: flex;
  align-items: baseline;
  gap: 12px;
  min-width: 0;
  padding: 12px 16px;
  background: rgba(var(--v-theme-on-surface), 0.06);
}

.subtitle-group-number {
  flex: 0 0 auto;
  font-weight: 600;
}

.subtitle-group-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subtitle-group-count {
  flex: 0 0 auto;
  margin-inline-start: auto;
  white-space: nowrap;
}

.subtitle-group-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 88px 48px 80px 148px 172px;
  gap: 12px;
  align-items: center;
  padding: 8px 16px;
}

.subtitle-group.with-episode .subtitle-group-row {
  grid-template-columns: 72px minmax(0, 1fr) 88px 48px 80px 148px 172px;
}

.subtitle-group-row + .subtitle-group-row {
  border-top: 1px solid rgba(var(--v-border-color), calc(var(--v-border-opacity) * 0.6));
}

.subtitle-group-file {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.subtitle-group-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subtitle-group-cell {
  color: rgba(var(--v-theme-on-surface), 0.75);
  white-space: nowrap;
}

.subtitle-group-actions {
  justify-self: start;
}
</style>

<style>
.subtitle-media-menu {
  overflow: hidden;
}

.subtitle-media-menu .v-list-item__content {
  overflow: hidden;
}

.subtitle-media-menu .v-list-item-title,
.subtitle-media-label {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
