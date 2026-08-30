<script setup lang="ts">
import {
  MetadataService,
  type MetadataBase,
  type MetadataPublic,
} from "@/client"
import { client } from "@/client/client.gen"
import { useMetadataStore } from "@/stores/metadata.store"
import { useToastStore } from "@/stores/toast.store"
import { computed, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

const COMPARE_FIELDS = [
  "number",
  "title",
  "studio",
  "release",
  "year",
  "runtime",
  "genre",
  "rating",
  "language",
  "country",
  "outline",
  "director",
  "actor",
  "actor_photo",
  "cover",
  "cover_small",
  "extrafanart",
  "trailer",
  "tag",
  "label",
  "series",
  "userrating",
  "uservotes",
  "detailurl",
  "site",
] as const

type CompareField = (typeof COMPARE_FIELDS)[number]

const FIELD_LABEL_KEYS: Record<CompareField, string> = {
  number: "number",
  title: "title",
  studio: "studio",
  release: "release",
  year: "year",
  runtime: "runtime",
  genre: "genre",
  rating: "rating",
  language: "language",
  country: "country",
  outline: "outline",
  director: "director",
  actor: "actor",
  actor_photo: "actorPhoto",
  cover: "cover",
  cover_small: "coverSmall",
  extrafanart: "extraFanart",
  trailer: "trailer",
  tag: "tag",
  label: "label",
  series: "series",
  userrating: "userRating",
  uservotes: "userVotes",
  detailurl: "detailUrl",
  site: "site",
}

interface Props {
  modelValue: boolean
  metadata?: MetadataPublic
}

const props = defineProps<Props>()
const emit = defineEmits<{
  "update:modelValue": [value: boolean]
}>()

const { t } = useI18n()
const metadataStore = useMetadataStore()
const toastStore = useToastStore()

const open = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit("update:modelValue", value),
})

const sites = ref<string[]>([])
const selectedSite = ref("")
const selectedDetailUrl = ref("")
const isFetching = ref(false)
const isApplying = ref(false)
const fetched = ref<MetadataBase | null>(null)
const selectedFields = ref<CompareField[]>([])
const onlyDiff = ref(true)

const siteOptions = computed(() => {
  const values = new Set(sites.value)
  if (selectedSite.value) values.add(selectedSite.value)
  if (props.metadata?.site) values.add(props.metadata.site)
  return Array.from(values)
})

const siteHint = computed(() => {
  if (!selectedSite.value) return t("components.metadata.refreshDialog.siteHintAll")
  if (selectedDetailUrl.value) return t("components.metadata.refreshDialog.siteHintCurrent")
  return t("components.metadata.refreshDialog.siteHintSearch")
})

function fieldLabel(field: CompareField) {
  return t(`components.metadata.form.${FIELD_LABEL_KEYS[field]}`)
}

function normalize(field: CompareField, value: unknown): string {
  if (value == null) return ""
  const text = String(value).trim()
  if (field === "release") return text.slice(0, 10)
  return text
}

function displayValue(field: CompareField, value: unknown): string {
  const text = normalize(field, value)
  return text || t("components.metadata.refreshDialog.empty")
}

function isChanged(field: CompareField): boolean {
  if (!props.metadata || !fetched.value) return false
  return (
    normalize(field, props.metadata[field]) !==
    normalize(field, fetched.value[field])
  )
}

const rows = computed(() => {
  if (!fetched.value || !props.metadata) return []
  return COMPARE_FIELDS.filter((field) => !onlyDiff.value || isChanged(field)).map(
    (field) => ({
      field,
      changed: isChanged(field),
      current: props.metadata?.[field],
      next: fetched.value?.[field],
    }),
  )
})

const diffCount = computed(
  () => COMPARE_FIELDS.filter((field) => isChanged(field)).length,
)

const selectedCount = computed(() => selectedFields.value.length)

function previewSrc(path: unknown): string {
  if (!path || typeof path !== "string") return ""
  if (path.startsWith("http://") || path.startsWith("https://")) return path
  return `${client.getConfig().baseURL}/api/v1/resource/image?path=${encodeURIComponent(path)}`
}

function onSiteChange(site: string | null) {
  const next = site || ""
  if (next !== (props.metadata?.site || "")) {
    selectedDetailUrl.value = ""
  } else {
    selectedDetailUrl.value = props.metadata?.detailurl || ""
  }
  fetched.value = null
  selectedFields.value = []
}

function onDetailUrlChange() {
  fetched.value = null
  selectedFields.value = []
}

function reset() {
  selectedSite.value = ""
  selectedDetailUrl.value = ""
  isFetching.value = false
  isApplying.value = false
  fetched.value = null
  selectedFields.value = []
  onlyDiff.value = true
}

async function loadSites() {
  try {
    const { data } = await MetadataService.listMetadataSites()
    sites.value = data || []
  } catch {
    sites.value = []
  }
}

function getErrorDetail(error: unknown, fallback: string): string {
  if (error && typeof error === "object") {
    const detail = (error as { response?: { data?: { detail?: unknown } } })
      .response?.data?.detail
    if (typeof detail === "string" && detail) return detail
  }
  return fallback
}

async function fetchMetadata() {
  if (!props.metadata) return
  isFetching.value = true
  fetched.value = null
  selectedFields.value = []
  try {
    const { data } = await MetadataService.refreshMetadata({
      id: props.metadata.id,
      metadataRefreshParam: {
        site: selectedSite.value || null,
        detailurl: selectedDetailUrl.value || null,
      },
    })
    fetched.value = data
    selectedFields.value = COMPARE_FIELDS.filter((field) => isChanged(field))
  } catch (error) {
    toastStore.error(
      getErrorDetail(error, t("components.metadata.refreshDialog.fetchFailed")),
    )
  } finally {
    isFetching.value = false
  }
}

function toggleField(field: CompareField, checked: boolean) {
  if (checked) {
    if (!selectedFields.value.includes(field)) {
      selectedFields.value = [...selectedFields.value, field]
    }
    return
  }
  selectedFields.value = selectedFields.value.filter((item) => item !== field)
}

function selectChanged() {
  selectedFields.value = COMPARE_FIELDS.filter((field) => isChanged(field))
}

async function applySelected() {
  if (!props.metadata || !fetched.value || selectedFields.value.length === 0) return
  isApplying.value = true
  try {
    const merged: MetadataPublic = { ...props.metadata }
    for (const field of selectedFields.value) {
      ;(merged as Record<string, unknown>)[field] = fetched.value[field]
    }
    await metadataStore.updateMetadata(merged)
    toastStore.success(t("components.metadata.refreshDialog.applySuccess"))
    open.value = false
  } catch (error) {
    toastStore.error(
      getErrorDetail(error, t("components.metadata.refreshDialog.applyFailed")),
    )
  } finally {
    isApplying.value = false
  }
}

watch(open, async (visible) => {
  if (!visible) {
    reset()
    return
  }
  selectedSite.value = props.metadata?.site || ""
  selectedDetailUrl.value = props.metadata?.detailurl || ""
  await loadSites()
})
</script>

<template>
  <VDialog v-model="open" max-width="960" scrollable>
    <VCard style="max-height: 90vh; display: flex; flex-direction: column;">
      <VCardTitle class="px-6 pt-5 d-flex align-center justify-space-between">
        <span>
          {{ t('components.metadata.refreshDialog.title') }}
          <span v-if="metadata" class="text-medium-emphasis text-body-1 ml-2">
            {{ metadata.number }}
          </span>
        </span>
        <VBtn icon variant="text" size="small" @click="open = false">
          <VIcon icon="bx-x" />
        </VBtn>
      </VCardTitle>

      <VCardText style="flex: 1; overflow-y: auto;">
        <VRow dense>
          <VCol cols="12" md="4">
            <VCombobox
              v-model="selectedSite"
              :items="siteOptions"
              :label="t('components.metadata.refreshDialog.site')"
              :placeholder="t('components.metadata.refreshDialog.sitePlaceholder')"
              variant="outlined"
              density="comfortable"
              clearable
              hide-details
              :disabled="isFetching"
              @update:model-value="onSiteChange"
            />
          </VCol>
          <VCol cols="12" md="8">
            <VTextField
              v-model="selectedDetailUrl"
              :label="t('components.metadata.refreshDialog.detailUrl')"
              :placeholder="t('components.metadata.refreshDialog.detailUrlPlaceholder')"
              variant="outlined"
              density="comfortable"
              clearable
              hide-details
              :disabled="isFetching"
              @update:model-value="onDetailUrlChange"
            />
          </VCol>
        </VRow>
        <p class="text-caption text-medium-emphasis mt-2 mb-3">{{ siteHint }}</p>
        <VBtn
          color="primary"
          prepend-icon="bx-download"
          :loading="isFetching"
          :disabled="isFetching || !metadata"
          @click="fetchMetadata"
        >
          {{ isFetching
            ? t('components.metadata.refreshDialog.fetching')
            : t('components.metadata.refreshDialog.fetch') }}
        </VBtn>

        <template v-if="fetched">
          <VDivider class="my-4" />
          <div class="d-flex flex-wrap align-center gap-3 mb-3">
            <span v-if="diffCount > 0" class="text-body-2">
              {{ t('components.metadata.refreshDialog.diffCount', { count: diffCount }) }}
            </span>
            <span v-else class="text-body-2 text-success">
              {{ t('components.metadata.refreshDialog.noChanges') }}
            </span>
            <VSpacer />
            <VCheckbox
              v-model="onlyDiff"
              :label="t('components.metadata.refreshDialog.onlyDiff')"
              density="compact"
              hide-details
              class="flex-grow-0"
            />
            <VBtn
              variant="text"
              size="small"
              :disabled="diffCount === 0"
              @click="selectChanged"
            >
              {{ t('components.metadata.refreshDialog.selectChanged') }}
            </VBtn>
          </div>

          <div v-if="rows.length" class="compare-table">
            <div class="compare-head">
              <span class="col-check" />
              <span>{{ t('components.metadata.refreshDialog.field') }}</span>
              <span>{{ t('components.metadata.refreshDialog.current') }}</span>
              <span>{{ t('components.metadata.refreshDialog.fetched') }}</span>
            </div>
            <div
              v-for="row in rows"
              :key="row.field"
              class="compare-row"
              :class="{ changed: row.changed }"
            >
              <div class="col-check">
                <VCheckbox
                  :model-value="selectedFields.includes(row.field)"
                  :disabled="!row.changed"
                  hide-details
                  density="compact"
                  @update:model-value="toggleField(row.field, Boolean($event))"
                />
              </div>
              <div class="col-label">{{ fieldLabel(row.field) }}</div>
              <div class="col-value">
                <img
                  v-if="row.field === 'cover' && previewSrc(row.current)"
                  class="cover-thumb"
                  :src="previewSrc(row.current)"
                  alt=""
                />
                <span v-else>{{ displayValue(row.field, row.current) }}</span>
              </div>
              <div class="col-value next">
                <img
                  v-if="row.field === 'cover' && previewSrc(row.next)"
                  class="cover-thumb"
                  :src="previewSrc(row.next)"
                  alt=""
                />
                <span v-else>{{ displayValue(row.field, row.next) }}</span>
              </div>
            </div>
          </div>
        </template>
      </VCardText>

      <VCardActions class="px-6 pb-4">
        <VSpacer />
        <VBtn variant="tonal" color="secondary" @click="open = false">
          {{ t('common.cancel') }}
        </VBtn>
        <VBtn
          color="primary"
          :loading="isApplying"
          :disabled="isApplying || selectedCount === 0"
          @click="applySelected"
        >
          {{ t('components.metadata.refreshDialog.apply', { count: selectedCount }) }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped>
.compare-table {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  overflow: hidden;
}

.compare-head,
.compare-row {
  display: grid;
  grid-template-columns: 48px 120px 1fr 1fr;
  gap: 8px;
  align-items: start;
}

.compare-head {
  padding: 8px 12px;
  font-size: 0.75rem;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.compare-row {
  padding: 10px 12px;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.compare-row.changed .next {
  color: rgb(var(--v-theme-success));
}

.col-check {
  display: flex;
  align-items: center;
  min-height: 32px;
}

.col-label {
  padding-top: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
}

.col-value {
  min-width: 0;
  padding-top: 6px;
  font-size: 0.8125rem;
  line-height: 1.4;
  word-break: break-word;
  white-space: pre-wrap;
}

.cover-thumb {
  display: block;
  max-width: 160px;
  max-height: 100px;
  object-fit: contain;
  border-radius: 4px;
  background: #1a1a1a;
}

@media (max-width: 768px) {
  .compare-head,
  .compare-row {
    grid-template-columns: 40px 1fr;
  }

  .compare-head span:nth-child(n + 3),
  .compare-row .col-value {
    grid-column: 1 / -1;
  }
}
</style>
