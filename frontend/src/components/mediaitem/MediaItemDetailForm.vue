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

// Function to delete the media item
async function deleteItem() {
  if (isEditMode.value && formData.value.id) {
    await mediaItemStore.confirmDeleteMediaItem(formData.value.id)
    mediaItemStore.showDialog = false
  }
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

// Computed property for favorite status
const favorite = computed({
  get: () => formData.value.userdata?.favorite || false,
  set: (value) => {
    if (!formData.value.userdata) {
      formData.value.userdata = {}
    }
    formData.value.userdata.favorite = value
  },
})
</script>

<template>
  <VForm @submit.prevent="saveForm">
    <VRow>
      <!-- Title -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="title">{{ t('pages.mediaitem.title') }}</label>
          </VCol>
          <VCol cols="12" md="9">
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
          <VCol cols="12" md="3" class="row-label">
            <label for="original_title">{{ t('pages.mediaitem.originalTitle') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField
              v-model="formData.original_title"
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- Media Type -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="media_type">{{ t('pages.mediaitem.mediaType') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VSelect
              v-model="formData.media_type"
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
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="number">{{ t('pages.mediaitem.number') }}</label>
          </VCol>
          <VCol cols="12" md="9">
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
          <VCol cols="12" md="3" class="row-label">
            <label for="watched">{{ t('pages.mediaitem.watched') }}</label>
          </VCol>
          <VCol cols="12" md="9">
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
          <VCol cols="12" md="3" class="row-label">
            <label for="favorite">{{ t('pages.mediaitem.favorite') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VSwitch
              v-model="favorite"
              color="error"
              hide-details
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- IMDB ID -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="imdb_id">{{ t('pages.mediaitem.imdbId') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField
              v-model="formData.imdb_id"
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- TMDB ID -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="tmdb_id">{{ t('pages.mediaitem.tmdbId') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField
              v-model="formData.tmdb_id"
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- TVDB ID -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="tvdb_id">{{ t('pages.mediaitem.tvdbId') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField
              v-model="formData.tvdb_id"
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- Season Number (for TV shows) -->
      <VCol v-if="formData.media_type === 'tvshow'" cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="season_number">{{ t('pages.mediaitem.seasonNumber') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField
              v-model.number="formData.season_number"
              type="number"
              variant="outlined"
              density="comfortable"
            />
          </VCol>
        </VRow>
      </VCol>

      <!-- Episode Number (for TV shows) -->
      <VCol v-if="formData.media_type === 'tvshow'" cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="episode_number">{{ t('pages.mediaitem.episodeNumber') }}</label>
          </VCol>
          <VCol cols="12" md="9">
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
          <VCol cols="12" md="3" />
          <VCol cols="12" md="9" class="d-flex">
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