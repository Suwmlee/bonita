<!-- MediaItemDetailForm.vue -->
<script setup lang="ts">
import type { MediaItemWithWatches } from "@/client"
import { useMediaItemStore } from "@/stores/mediaitem.store"
import { useToastStore } from "@/stores/toast.store"
import {
  getImdbPosterUrl,
  getItemImdbId,
  getPosterUrl,
  hasPosterSource,
} from "@/composables/useMediaPoster"
import { computed, ref } from "vue"
import { useI18n } from "vue-i18n"

const props = defineProps<{
  updateMediaItem?: MediaItemWithWatches
}>()

const { t } = useI18n()
const mediaItemStore = useMediaItemStore()
const toastStore = useToastStore()

function isBlank(value?: string | null) {
  return !value || !String(value).trim()
}

type FormKind = "movie" | "number" | "tvshow" | "episode" | "video"

function kindFromItem(item?: Partial<MediaItemWithWatches> | null): FormKind {
  const mediaType = item?.media_type
  if (mediaType === "movie" && !isBlank(item?.number)) return "number"
  if (mediaType === "tvshow" || mediaType === "episode" || mediaType === "video" || mediaType === "movie") {
    return mediaType
  }
  return "movie"
}

const formData = ref<Partial<MediaItemWithWatches>>(
  props.updateMediaItem
    ? { ...props.updateMediaItem }
    : {
        title: "",
        original_title: "",
        media_type: "movie",
        number: "",
        userdata: {
          watched: false,
        },
        ...mediaItemStore.addDraft,
      },
)

const formKind = ref<FormKind>(kindFromItem(props.updateMediaItem ?? mediaItemStore.addDraft))

const isEditMode = computed(() => !!props.updateMediaItem)
const isNumbered = computed(() => formKind.value === "number")
const isEpisode = computed(() => formKind.value === "episode")
const isTvshow = computed(() => formKind.value === "tvshow")
const showExternalIds = computed(() => formKind.value === "movie" || formKind.value === "tvshow")

const hasExternalId = computed(() => {
  return (
    !isBlank(formData.value.imdb_id) ||
    !isBlank(formData.value.tmdb_id) ||
    !isBlank(formData.value.tvdb_id)
  )
})

const parentSeriesTitle = computed(
  () => (formData.value.original_title || formData.value.title || "").trim(),
)
const canOpenParent = computed(
  () => isEditMode.value && isEpisode.value && !!formData.value.series_id,
)
const canAddEpisode = computed(
  () => isEditMode.value && isTvshow.value && !!formData.value.id,
)

type SeriesOption = {
  id: number
  title: string
  imdb_id?: string | null
  tmdb_id?: string | null
  tvdb_id?: string | null
}
const seriesSearch = ref("")
const seriesItems = ref<SeriesOption[]>([])
const seriesLoading = ref(false)
const selectedSeriesId = ref<number | null>(formData.value.series_id ?? null)

function seriesOptionFromItem(item: MediaItemWithWatches): SeriesOption {
  return {
    id: item.id,
    title: (item.title || item.original_title || String(item.id)).trim(),
    imdb_id: item.imdb_id,
    tmdb_id: item.tmdb_id,
    tvdb_id: item.tvdb_id,
  }
}

function ensureSelectedSeriesOption() {
  const id = selectedSeriesId.value
  if (!id || seriesItems.value.some((item) => item.id === id)) return
  const title = parentSeriesTitle.value || String(id)
  seriesItems.value = [{ id, title }, ...seriesItems.value]
}

async function loadSeries(term: string) {
  seriesLoading.value = true
  try {
    const items = await mediaItemStore.searchSeries(term)
    seriesItems.value = items.map(seriesOptionFromItem)
    ensureSelectedSeriesOption()
  } catch (error) {
    console.error("Error searching series:", error)
  } finally {
    seriesLoading.value = false
  }
}

watchDebounced(
  seriesSearch,
  (term) => {
    if (!isEpisode.value) return
    loadSeries(term)
  },
  { debounce: 300 },
)

watch(isEpisode, (episode) => {
  if (!episode) return
  if (formData.value.season_number == null || formData.value.season_number < 0) {
    formData.value.season_number = 1
  }
  if (formData.value.episode_number == null || formData.value.episode_number < 0) {
    formData.value.episode_number = 1
  }
  if (!seriesItems.value.length) {
    loadSeries("")
  }
}, { immediate: true })

watch(selectedSeriesId, (id) => {
  formData.value.series_id = id ?? undefined
  const found = seriesItems.value.find((item) => item.id === id)
  if (found) {
    formData.value.series_imdb_id = found.imdb_id
    formData.value.series_tmdb_id = found.tmdb_id
    formData.value.series_tvdb_id = found.tvdb_id
    if (isBlank(formData.value.original_title)) {
      formData.value.original_title = found.title
    }
  }
})

watch(formKind, (kind, previous) => {
  if (kind === "number") {
    formData.value.media_type = "movie"
    return
  }
  formData.value.media_type = kind
  if (previous === "number") {
    formData.value.number = ""
  }
})

async function saveForm() {
  if (isBlank(formData.value.title)) {
    toastStore.error(t("pages.mediaitem.titleRequired"))
    return
  }
  if (isNumbered.value && isBlank(formData.value.number)) {
    toastStore.error(t("pages.mediaitem.numberRequired"))
    return
  }
  if (showExternalIds.value && !hasExternalId.value) {
    toastStore.error(t("pages.mediaitem.externalIdRequired"))
    return
  }
  if (isEpisode.value && !formData.value.series_id) {
    toastStore.error(t("pages.mediaitem.parentSeriesRequired"))
    return
  }
  if (
    isEpisode.value &&
    (formData.value.season_number == null ||
      formData.value.season_number < 0 ||
      formData.value.episode_number == null ||
      formData.value.episode_number < 0)
  ) {
    toastStore.error(t("pages.mediaitem.seasonEpisodeRequired"))
    return
  }
  if (isEditMode.value) {
    await mediaItemStore.updateMediaItem(formData.value as MediaItemWithWatches)
  } else {
    await mediaItemStore.addMediaItem(formData.value)
  }
}

function cancel() {
  mediaItemStore.closeDialog()
}

async function openParentSeries() {
  const seriesId = formData.value.series_id
  if (!seriesId) return
  await mediaItemStore.openParentMediaItem(seriesId)
}

function addEpisode() {
  if (!props.updateMediaItem) return
  mediaItemStore.showAddEpisode(props.updateMediaItem)
}

async function deleteItem() {
  if (isEditMode.value && formData.value.id) {
    await mediaItemStore.confirmDeleteMediaItem(formData.value.id)
    mediaItemStore.closeDialog()
  }
}

const mediaTypes = [
  { value: "movie", title: t("pages.mediaitem.movie") },
  { value: "number", title: t("pages.mediaitem.hasNumber") },
  { value: "tvshow", title: t("pages.mediaitem.tvshow") },
  { value: "episode", title: t("pages.mediaitem.episode") },
  { value: "video", title: t("pages.mediaitem.video") },
]

const watched = computed({
  get: () => formData.value.userdata?.watched || false,
  set: (value) => {
    if (!formData.value.userdata) {
      formData.value.userdata = {}
    }
    formData.value.userdata.watched = value
  },
})

const favorite = computed({
  get: () => formData.value.userdata?.favorite || false,
  set: (value) => {
    if (!formData.value.userdata) {
      formData.value.userdata = {}
    }
    formData.value.userdata.favorite = value
  },
})

const posterQuery = computed(() => ({
  title: formData.value.title,
  original_title: formData.value.original_title,
  media_type: formData.value.media_type,
  imdb_id: formData.value.imdb_id,
  tmdb_id: formData.value.tmdb_id,
  number: formData.value.number,
  series_imdb_id: formData.value.series_imdb_id,
  series_tmdb_id: formData.value.series_tmdb_id,
  external_item_id: formData.value.external_item_id,
}))

const posterUrl = ref("")
const posterFailed = ref(false)
const showFullPoster = computed(() => formData.value.crop === false)

watchDebounced(
  posterQuery,
  () => {
    posterFailed.value = false
    if (!hasPosterSource(formData.value)) {
      posterUrl.value = ""
      return
    }
    posterUrl.value = getPosterUrl(formData.value)
  },
  { debounce: 400, immediate: true },
)

function onPosterError(event: Event) {
  const failedSrc = (event.target as HTMLImageElement | null)?.src || ""
  const imdbId = getItemImdbId(formData.value)
  const fallback = imdbId ? getImdbPosterUrl(imdbId) : null
  if (fallback && failedSrc !== fallback) {
    posterUrl.value = fallback
    return
  }
  posterFailed.value = true
}
</script>

<template>
  <VForm class="mediaitem-form" @submit.prevent="saveForm">
    <div
      class="form-poster"
      :class="{
        'show-full': showFullPoster,
        'is-numbered': isNumbered,
      }"
    >
      <img
        v-if="posterUrl && !posterFailed"
        class="form-poster-image"
        :src="posterUrl"
        :alt="formData.title || t('pages.mediaitem.poster')"
        @error="onPosterError"
      />
      <div v-else class="form-poster-empty">
        <VIcon icon="bx-image" size="32" />
        <span>{{ t('pages.mediaitem.noPoster') }}</span>
      </div>
    </div>
    <VRow class="form-fields">
      <!-- Title -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label">
            <label for="title">{{ t('pages.mediaitem.title') }}</label>
          </VCol>
          <VCol cols="12" md>
            <VTextField
              v-model="formData.title"
              required
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- Original Title -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label">
            <label for="original_title">{{ t('pages.mediaitem.originalTitle') }}</label>
          </VCol>
          <VCol cols="12" md>
            <VTextField
              v-model="formData.original_title"
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- Parent series -->
      <VCol v-if="isEpisode" cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label">
            <label>{{ t('pages.mediaitem.parentSeries') }}</label>
          </VCol>
          <VCol cols="12" md class="d-flex align-center">
            <VAutocomplete
              v-model="selectedSeriesId"
              v-model:search="seriesSearch"
              :items="seriesItems"
              item-title="title"
              item-value="id"
              no-filter
              clearable
              hide-no-data
              :loading="seriesLoading"
              :placeholder="t('pages.mediaitem.parentSeriesSearch')"
              variant="outlined"
              density="comfortable"
              class="flex-grow-1"
            />
            <VBtn
              v-if="canOpenParent"
              variant="text"
              color="primary"
              class="flex-shrink-0 ms-2"
              :loading="mediaItemStore.isLoading"
              @click="openParentSeries"
            >
              {{ t('pages.mediaitem.viewParent') }}
            </VBtn>
          </VCol>
        </VRow>
      </VCol>

      <!-- Media Type -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label">
            <label for="media_type">{{ t('pages.mediaitem.mediaType') }}</label>
          </VCol>
          <VCol cols="12" md>
            <VSelect
              v-model="formKind"
              :items="mediaTypes"
              item-title="title"
              item-value="value"
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- Number -->
      <VCol v-if="isNumbered" cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label">
            <label for="number">{{ t('pages.mediaitem.number') }}</label>
          </VCol>
          <VCol cols="12" md>
            <VTextField
              v-model="formData.number"
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- Watched Status -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label">
            <label for="watched">{{ t('pages.mediaitem.watched') }}</label>
          </VCol>
          <VCol cols="12" md>
            <VSwitch
              v-model="watched"
              color="primary"
              hide-details
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- Favorite Status -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label">
            <label for="favorite">{{ t('pages.mediaitem.favorite') }}</label>
          </VCol>
          <VCol cols="12" md>
            <VSwitch
              v-model="favorite"
              color="error"
              hide-details
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- IMDB ID -->
      <VCol v-if="showExternalIds" cols="12">
        <VAlert type="info" variant="tonal" density="compact">
          {{ t('pages.mediaitem.externalIdHint') }}
        </VAlert>
      </VCol>
      <VCol v-if="showExternalIds" cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label">
            <label for="imdb_id">{{ t('pages.mediaitem.imdbId') }}</label>
          </VCol>
          <VCol cols="12" md>
            <VTextField
              v-model="formData.imdb_id"
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- TMDB ID -->
      <VCol v-if="showExternalIds" cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label">
            <label for="tmdb_id">{{ t('pages.mediaitem.tmdbId') }}</label>
          </VCol>
          <VCol cols="12" md>
            <VTextField
              v-model="formData.tmdb_id"
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- TVDB ID -->
      <VCol v-if="showExternalIds" cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label">
            <label for="tvdb_id">{{ t('pages.mediaitem.tvdbId') }}</label>
          </VCol>
          <VCol cols="12" md>
            <VTextField
              v-model="formData.tvdb_id"
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- Add episode -->
      <VCol v-if="canAddEpisode" cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label">
            <label>{{ t('pages.mediaitem.episode') }}</label>
          </VCol>
          <VCol cols="12" md>
            <VBtn
              variant="outlined"
              color="primary"
              @click="addEpisode"
            >
              {{ t('pages.mediaitem.addEpisode') }}
            </VBtn>
          </VCol>
        </VRow>
      </VCol>

      <!-- Season Number -->
      <VCol v-if="isEpisode" cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label">
            <label for="season_number">{{ t('pages.mediaitem.seasonNumber') }}</label>
          </VCol>
          <VCol cols="12" md>
            <VTextField
              v-model.number="formData.season_number"
              type="number"
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- Episode Number -->
      <VCol v-if="isEpisode" cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label">
            <label for="episode_number">{{ t('pages.mediaitem.episodeNumber') }}</label>
          </VCol>
          <VCol cols="12" md>
            <VTextField
              v-model.number="formData.episode_number"
              type="number"
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- Action Buttons -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="auto" class="row-label" />
          <VCol cols="12" md class="d-flex">
            <VBtn
              v-if="isEditMode"
              color="error"
              class="me-auto"
              @click="deleteItem"
              :loading="mediaItemStore.isLoading"
            >
              {{ t('common.delete') }}
            </VBtn>
            <VBtn
              color="primary"
              class="me-4"
              type="submit"
              :loading="mediaItemStore.isLoading"
            >
              {{ isEditMode ? t('common.save') : t('common.add') }}
            </VBtn>
            <VBtn @click="cancel">
              {{ t('common.cancel') }}
            </VBtn>
          </VCol>
        </VRow>
      </VCol>
    </VRow>
  </VForm>
</template>

<style lang="scss" scoped>
.mediaitem-form {
  display: flex;
  align-items: flex-start;
  gap: 1.25rem;
}

.form-poster {
  flex: 0 0 180px;
  width: 180px;
  aspect-ratio: 2 / 3;
  position: sticky;
  top: 0;
  overflow: hidden;
  border-radius: 8px;
  background: #1a1a1a;
}

.form-poster.is-numbered {
  flex-basis: 260px;
  width: 260px;
  aspect-ratio: 3 / 2;
}

.form-poster-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  display: block;
}

.form-poster.is-numbered .form-poster-image,
.form-poster.show-full .form-poster-image {
  object-fit: contain;
  object-position: center;
}

.form-poster-empty {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  color: rgba(255, 255, 255, 0.55);
  font-size: 0.7rem;
  text-align: center;
  padding: 0.5rem;
  line-height: 1.2;
}

.form-poster-empty span {
  white-space: nowrap;
}

.form-fields {
  flex: 1;
  min-width: 0;
}

@media (min-width: 960px) {
  .row-label {
    flex: 0 0 5.5rem;
    max-width: 5.5rem;
    width: 5.5rem;
    padding-right: 0.5rem;
  }
}

@media (max-width: 600px) {
  .mediaitem-form {
    flex-direction: column;
    align-items: center;
  }

  .form-poster {
    position: static;
  }
}
</style>