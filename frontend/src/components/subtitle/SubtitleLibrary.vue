<script setup lang="ts">
import {
  type SubtitleDeliverResult,
  type SubtitlePublic,
  SubtitleService,
} from "@/client"
import type { SubtitleGroupPublic } from "@/client/types.gen"
import { getPosterUrl } from "@/composables/useMediaPoster"
import { useConfirmationStore } from "@/stores/confirmation.store"
import { useToastStore } from "@/stores/toast.store"
import { computed, onMounted, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

const props = defineProps<{
  fixedNumber?: string
  compact?: boolean
}>()

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
const forcedNumber = ref("")
const unmatchedOnly = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const editOpen = ref(false)
const saving = ref(false)
const editing = ref<SubtitlePublic | null>(null)
const editKey = ref("")
const editLanguage = ref("zh-Hans")
const editPart = ref(0)

const languages = computed(() => [
  { title: t("pages.subtitles.lang.zhHans"), value: "zh-Hans" },
  { title: t("pages.subtitles.lang.zhHant"), value: "zh-Hant" },
  { title: t("pages.subtitles.lang.ja"), value: "ja" },
  { title: t("pages.subtitles.lang.en"), value: "en" },
])

const headers = computed(() => {
  const columns = [
    { title: t("pages.subtitles.file"), key: "original_name", sortable: false },
    {
      title: t("pages.subtitles.mediaItem"),
      key: "media_item_id",
      sortable: false,
    },
    {
      title: t("pages.subtitles.language"),
      key: "language",
      sortable: false,
      width: "120px",
    },
    {
      title: t("pages.subtitles.part"),
      key: "part_number",
      sortable: false,
      width: "88px",
    },
    {
      title: t("common.actions"),
      key: "actions",
      sortable: false,
      width: "148px",
    },
  ]
  if (props.fixedNumber) {
    return columns.filter((column) => column.key !== "media_item_id")
  }
  return columns
})

const pageCount = computed(() =>
  Math.max(1, Math.ceil(total.value / itemsPerPage)),
)

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

function mediaLabel(item: SubtitlePublic) {
  return item.number || item.title || item.imdb_id || ""
}

function compareLabel(item: SubtitlePublic) {
  const parts: string[] = []
  const size = formatSize(item.file_size)
  const time = formatTime(item.updatetime)
  if (size) parts.push(size)
  if (time) parts.push(time)
  return parts.join(" · ")
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
  return getPosterUrl({
    media_type: group.number ? "number" : "movie",
    number: group.number || "",
    title: group.title || group.number || "",
    imdb_id: group.imdb_id || "",
    tmdb_id: group.tmdb_id || "",
  })
}

function markPosterBroken(key: string) {
  posterBroken.value = { ...posterBroken.value, [key]: true }
}

async function load() {
  loading.value = true
  try {
    const keyword = searchKeyword()
    if (props.compact || props.fixedNumber) {
      const { data: response } = await SubtitleService.listSubtitles({
        skip: (page.value - 1) * itemsPerPage,
        limit: props.compact ? 50 : itemsPerPage,
        filter: props.fixedNumber ? undefined : keyword || undefined,
        number: props.fixedNumber || undefined,
        unmatched: props.fixedNumber ? false : unmatchedOnly.value,
      })
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
    groups.value = response.data || []
    total.value = response.count || 0
  } catch (error) {
    toastStore.error(apiErrorMessage(error, t("pages.subtitles.loadFailed")))
  } finally {
    loading.value = false
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

function chooseFiles() {
  fileInput.value?.click()
}

async function onFiles(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ""
  if (!files.length) return
  uploading.value = true
  try {
    const number = (props.fixedNumber || forcedNumber.value).trim()
    const { data: result } = await SubtitleService.uploadSubtitles({
      bodySubtitleUploadSubtitles: {
        files,
        number: number || null,
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
  editKey.value = props.fixedNumber || item.number || ""
  editLanguage.value = item.language || "zh-Hans"
  editPart.value = item.part_number || 0
  editOpen.value = true
}

async function saveEdit() {
  if (!editing.value) return
  saving.value = true
  try {
    await SubtitleService.updateSubtitle({
      subtitle_id: editing.value.id,
      subtitleUpdate: {
        number: props.fixedNumber || editKey.value,
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
    message: t(item.preferred ? "pages.subtitles.deleteMessageInUse" : "pages.subtitles.deleteMessage", {
      name: item.original_name,
    }),
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

async function deliver(item: SubtitlePublic) {
  try {
    const { data: result } = await SubtitleService.deliverOneSubtitle({
      subtitle_id: item.id,
    })
    toastStore.success(deliverSummary(result))
  } catch (error) {
    toastStore.error(apiErrorMessage(error, t("pages.subtitles.deliverFailed")))
  }
}

async function useThis(item: SubtitlePublic) {
  try {
    const { data: result } = await SubtitleService.useSubtitle({
      subtitle_id: item.id,
    })
    toastStore.success(deliverSummary(result))
    await load()
  } catch (error) {
    toastStore.error(apiErrorMessage(error, t("pages.subtitles.deliverFailed")))
  }
}

watch(
  () => props.fixedNumber,
  () => {
    page.value = 1
    load()
  },
)

onMounted(load)
</script>

<template>
  <div>
    <div v-if="!compact" class="d-flex align-center justify-space-between mb-4 flex-wrap gap-3">
      <div>
        <h1 class="text-h5">{{ t("pages.subtitles.title") }}</h1>
        <p class="text-body-2 text-medium-emphasis mb-0 mt-1">{{ t("pages.subtitles.hint") }}</p>
      </div>
    </div>

    <div class="d-flex align-center flex-wrap gap-3 mb-3">
      <VTextField
        v-if="!compact && !fixedNumber"
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
      <VTextField
        v-if="!fixedNumber"
        v-model="forcedNumber"
        :placeholder="t('pages.subtitles.forceNumber')"
        density="compact"
        hide-details
        clearable
        style="max-width: 220px"
      />
      <VBtn color="primary" prepend-icon="bx-upload" :loading="uploading" @click="chooseFiles">
        {{ t("pages.subtitles.upload") }}
      </VBtn>
      <VBtn v-if="!compact" variant="tonal" prepend-icon="bx-refresh" :loading="loading" @click="load">
        {{ t("common.refresh") }}
      </VBtn>
      <VCheckbox
        v-if="!fixedNumber"
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

    <div v-if="!compact && !fixedNumber" class="subtitle-groups">
      <div v-if="loading && groups.length === 0" class="d-flex justify-center pa-8">
        <VProgressCircular indeterminate color="primary" />
      </div>
      <div v-else-if="groups.length === 0" class="text-medium-emphasis text-center pa-8">
        {{ t("pages.subtitles.empty") }}
      </div>
      <article v-for="group in groups" :key="group.key" class="subtitle-group">
        <aside class="subtitle-group-poster">
          <div
            v-if="group.media_item_id"
            class="subtitle-poster"
            :class="{ 'show-full': group.crop === false }"
          >
            <img
              v-if="group.crop === false && !posterBroken[group.key]"
              class="subtitle-poster-fill"
              :src="groupPosterUrl(group)"
              alt=""
              aria-hidden="true"
              @error="markPosterBroken(group.key)"
            />
            <img
              v-show="!posterBroken[group.key]"
              class="subtitle-poster-image"
              :src="groupPosterUrl(group)"
              :alt="group.number || group.title || ''"
              @error="markPosterBroken(group.key)"
            />
            <div v-if="posterBroken[group.key]" class="subtitle-poster-empty">
              <VIcon icon="bx-image" size="small" />
            </div>
          </div>
        </aside>
        <div class="subtitle-group-main">
          <div class="subtitle-group-meta">
            <div class="subtitle-group-number">
              {{ group.media_item_id ? (group.number || group.title || group.imdb_id) : t("pages.subtitles.unmatched") }}
            </div>
            <div v-if="group.media_item_id && group.title && group.title !== group.number" class="subtitle-group-title">
              {{ group.title }}
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
            <div class="subtitle-group-actions">
              <VBtn size="small" variant="text" :title="t('common.edit')" @click="openEdit(item)">
                <VIcon icon="bx-edit-alt" />
              </VBtn>
              <VBtn
                v-if="item.preferred"
                size="small"
                variant="text"
                :title="t('pages.subtitles.deliver')"
                :disabled="!item.media_item_id"
                @click="deliver(item)"
              >
                <VIcon icon="bx-captions" />
              </VBtn>
              <VBtn
                v-else
                size="small"
                variant="text"
                :title="t('pages.subtitles.useThis')"
                :disabled="!item.media_item_id"
                @click="useThis(item)"
              >
                <VIcon icon="bx-check-circle" />
              </VBtn>
              <VBtn size="small" variant="text" color="error" :title="t('common.delete')" @click="remove(item)">
                <VIcon icon="bx-trash" />
              </VBtn>
            </div>
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

    <VDataTable
      v-else
      :headers="headers"
      :items="items"
      :loading="loading"
      item-value="id"
      :items-per-page="-1"
      density="compact"
      hide-default-footer
    >
      <template #item.original_name="{ item }">
        <div class="d-flex align-center flex-wrap gap-2">
          <span>{{ item.original_name }}</span>
          <VChip v-if="item.preferred" size="x-small" color="primary" variant="tonal">
            {{ t("pages.subtitles.inUse") }}
          </VChip>
        </div>
        <div v-if="compareLabel(item)" class="text-caption text-medium-emphasis">
          {{ compareLabel(item) }}
        </div>
      </template>
      <template #item.media_item_id="{ item }">
        <div v-if="item.media_item_id">
          <div>{{ mediaLabel(item) }}</div>
          <div
            v-if="item.number && item.title && item.title !== item.number"
            class="text-caption text-medium-emphasis"
          >
            {{ item.title }}
          </div>
        </div>
        <VChip v-else size="small" color="warning" variant="tonal">{{ t("pages.subtitles.unmatched") }}</VChip>
      </template>
      <template #item.language="{ item }">
        {{ languageLabel(item.language) }}
      </template>
      <template #item.part_number="{ item }">
        {{ formatPart(item.part_number) }}
      </template>
      <template #item.actions="{ item }">
        <div class="d-flex gap-1">
          <VBtn size="small" variant="text" :title="t('common.edit')" @click="openEdit(item)">
            <VIcon icon="bx-edit-alt" />
          </VBtn>
          <VBtn
            v-if="item.preferred"
            size="small"
            variant="text"
            :title="t('pages.subtitles.deliver')"
            :disabled="!item.media_item_id && !fixedNumber"
            @click="deliver(item)"
          >
            <VIcon icon="bx-captions" />
          </VBtn>
          <VBtn
            v-else
            size="small"
            variant="text"
            :title="t('pages.subtitles.useThis')"
            :disabled="!item.media_item_id && !fixedNumber"
            @click="useThis(item)"
          >
            <VIcon icon="bx-check-circle" />
          </VBtn>
          <VBtn size="small" variant="text" color="error" :title="t('common.delete')" @click="remove(item)">
            <VIcon icon="bx-trash" />
          </VBtn>
        </div>
      </template>
      <template #no-data>
        <div class="text-medium-emphasis py-6">{{ t("pages.subtitles.empty") }}</div>
      </template>
      <template v-if="!compact" #bottom>
        <div class="d-flex align-center justify-end px-2 py-3">
          <span class="text-caption text-medium-emphasis me-4">
            {{ t("pages.subtitles.total", { count: total }) }}
          </span>
          <VPagination
            :model-value="page"
            :length="pageCount"
            :total-visible="5"
            density="compact"
            @update:model-value="changePage"
          />
        </div>
      </template>
    </VDataTable>

    <VDialog v-model="editOpen" max-width="420">
      <VCard>
        <VCardTitle class="pt-5 px-6">{{ t("pages.subtitles.edit") }}</VCardTitle>
        <VCardText class="d-flex flex-column gap-3">
          <VTextField
            v-model="editKey"
            :label="t('pages.subtitles.number')"
            :readonly="!!fixedNumber"
            hide-details="auto"
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
  position: relative;
  display: block;
  width: 100%;
  aspect-ratio: 2 / 3;
  overflow: hidden;
  border-radius: 4px;
  background-color: #1a1a1a;
}

.subtitle-poster-fill,
.subtitle-poster-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.subtitle-poster-fill {
  object-fit: cover;
  filter: blur(18px) brightness(0.65);
  transform: scale(1.15);
}

.subtitle-poster-image {
  object-fit: cover;
  object-position: right center;
  z-index: 1;
}

.subtitle-poster.show-full .subtitle-poster-image {
  object-fit: contain;
  object-position: center;
}

.subtitle-poster-empty {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
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
  display: flex;
  gap: 4px;
  justify-self: start;
}
</style>
