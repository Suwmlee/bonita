<script setup lang="ts">
import {
  type SubtitleDeliverResult,
  type SubtitlePublic,
  SubtitleService,
} from "@/client"
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
const total = ref(0)
const page = ref(1)
const itemsPerPage = 20
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
      title: t("pages.subtitles.number"),
      key: "identity_key",
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
    return columns.filter((column) => column.key !== "identity_key")
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

function apiErrorMessage(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail
  if (typeof detail === "string" && detail.trim()) return detail
  return fallback
}

function deliverSummary(result: SubtitleDeliverResult) {
  if (!result.copied && !result.skipped && !result.missing) {
    return t("pages.subtitles.deliverNone")
  }
  return t("pages.subtitles.deliverResult", result)
}

async function load() {
  loading.value = true
  try {
    const { data: response } = await SubtitleService.listSubtitles({
      skip: (page.value - 1) * itemsPerPage,
      limit: props.compact ? 50 : itemsPerPage,
      filter: props.fixedNumber
        ? undefined
        : searchQuery.value.trim() || undefined,
      number: props.fixedNumber || undefined,
      unmatched: props.fixedNumber ? false : unmatchedOnly.value,
    })
    items.value = response.data || []
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
  editKey.value = props.fixedNumber || item.identity_key || ""
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
        identity_key: props.fixedNumber || editKey.value,
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
    message: t("pages.subtitles.deleteMessage", { name: item.original_name }),
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
        @click:clear="search"
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

    <VDataTable
      :headers="headers"
      :items="items"
      :loading="loading"
      item-value="id"
      :items-per-page="-1"
      density="compact"
      hide-default-footer
    >
      <template #item.identity_key="{ item }">
        <span v-if="item.identity_key">{{ item.identity_key }}</span>
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
            size="small"
            variant="text"
            :title="t('pages.subtitles.deliver')"
            :disabled="!item.identity_key && !fixedNumber"
            @click="deliver(item)"
          >
            <VIcon icon="bx-captions" />
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
