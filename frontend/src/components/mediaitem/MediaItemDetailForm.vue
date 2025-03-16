<!-- MediaItemDetailForm.vue -->
<script setup lang="ts">
import type { MediaItemWithWatches } from "@/client"
import { useMediaItemStore } from "@/stores/mediaitem.store"
import { computed, ref } from "vue"
import { useI18n } from "vue-i18n"

const props = defineProps<{
  updateMediaItem?: MediaItemWithWatches
}>()

const { t } = useI18n()
const mediaItemStore = useMediaItemStore()

// Create a form data object
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
      },
)

// Determine if we're in edit mode
const isEditMode = computed(() => !!props.updateMediaItem)

// Function to save the form
async function saveForm() {
  if (isEditMode.value) {
    await mediaItemStore.updateMediaItem(formData.value as MediaItemWithWatches)
  } else {
    await mediaItemStore.addMediaItem(formData.value)
  }
}

// Function to cancel and close the dialog
function cancel() {
  mediaItemStore.showDialog = false
}

// Media types for dropdown
const mediaTypes = [
  { value: "movie", title: t("pages.mediaitem.movie") },
  { value: "tvshow", title: t("pages.mediaitem.tvshow") },
]

// Computed property for watched status
const watched = computed({
  get: () => formData.value.userdata?.watched || false,
  set: (value) => {
    if (!formData.value.userdata) {
      formData.value.userdata = {}
    }
    formData.value.userdata.watched = value
  },
})
</script>

<template>
  <VForm @submit.prevent="saveForm">
    <VRow>
      <!-- Title -->
      <VCol cols="12" md="6">
        <VTextField
          v-model="formData.title"
          :label="t('pages.mediaitem.title')"
          required
          variant="outlined"
          density="comfortable"
        />
      </VCol>

      <!-- Original Title -->
      <VCol cols="12" md="6">
        <VTextField
          v-model="formData.original_title"
          :label="t('pages.mediaitem.originalTitle')"
          variant="outlined"
          density="comfortable"
        />
      </VCol>

      <!-- Media Type -->
      <VCol cols="12" md="6">
        <VSelect
          v-model="formData.media_type"
          :items="mediaTypes"
          item-title="title"
          item-value="value"
          :label="t('pages.mediaitem.mediaType')"
          variant="outlined"
          density="comfortable"
        />
      </VCol>

      <!-- Number -->
      <VCol cols="12" md="6">
        <VTextField
          v-model="formData.number"
          :label="t('pages.mediaitem.number')"
          variant="outlined"
          density="comfortable"
        />
      </VCol>

      <!-- Watched Status -->
      <VCol cols="12" md="6">
        <VSwitch
          v-model="watched"
          :label="t('pages.mediaitem.watched')"
          color="primary"
          hide-details
        />
      </VCol>

      <!-- IMDB ID -->
      <VCol cols="12" md="6">
        <VTextField
          v-model="formData.imdb_id"
          :label="t('pages.mediaitem.imdbId')"
          variant="outlined"
          density="comfortable"
        />
      </VCol>

      <!-- TMDB ID -->
      <VCol cols="12" md="6">
        <VTextField
          v-model="formData.tmdb_id"
          :label="t('pages.mediaitem.tmdbId')"
          variant="outlined"
          density="comfortable"
        />
      </VCol>

      <!-- TVDB ID -->
      <VCol cols="12" md="6">
        <VTextField
          v-model="formData.tvdb_id"
          :label="t('pages.mediaitem.tvdbId')"
          variant="outlined"
          density="comfortable"
        />
      </VCol>

      <!-- Season Number (for TV shows) -->
      <VCol v-if="formData.media_type === 'tvshow'" cols="12" md="6">
        <VTextField
          v-model.number="formData.season_number"
          type="number"
          :label="t('pages.mediaitem.seasonNumber')"
          variant="outlined"
          density="comfortable"
        />
      </VCol>

      <!-- Episode Number (for TV shows) -->
      <VCol v-if="formData.media_type === 'tvshow'" cols="12" md="6">
        <VTextField
          v-model.number="formData.episode_number"
          type="number"
          :label="t('pages.mediaitem.episodeNumber')"
          variant="outlined"
          density="comfortable"
        />
      </VCol>

      <!-- Action Buttons -->
      <VCol cols="12" class="d-flex justify-end">
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
  </VForm>
</template> 