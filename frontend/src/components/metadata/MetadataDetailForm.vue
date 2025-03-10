<script lang="ts" setup>
import { OpenAPI, ResourceService } from "@/client"
import type { MetadataPublic } from "@/client/types.gen"
import { useMetadataStore } from "@/stores/metadata.store"
import { computed, ref } from "vue"
import { useI18n } from "vue-i18n"

interface Props {
  updateMetadata?: MetadataPublic
}
const props = defineProps<Props>()

const metadataStore = useMetadataStore()
const { t } = useI18n() // 导入国际化工具函数
const isSubmitting = ref(false)
const formValid = ref(true)
const formErrors = ref<Record<string, string>>({})
const isUploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const { updateMetadata } = props as {
  updateMetadata: MetadataPublic
}
const currentMetadata = ref<any>()

// Computed property for cover image URL with proper base path
const coverImageUrl = computed(() => {
  if (!currentMetadata.value?.cover) return null

  // Add a timestamp query parameter to prevent browser caching
  const timestamp = new Date().getTime()
  return `${OpenAPI.BASE}/api/v1/resource/image?path=${encodeURIComponent(currentMetadata.value.cover)}&t=${timestamp}`
})

if (updateMetadata) {
  currentMetadata.value = { ...updateMetadata }
} else {
  const createMetadata: Partial<MetadataPublic> = {
    number: "",
    title: "",
    studio: "",
    release: "",
    year: null,
    runtime: "",
    genre: "",
    rating: "",
    language: "",
    country: "",
    outline: "",
    director: "",
    actor: "",
    actor_photo: "",
    cover: "",
    cover_small: "",
    extrafanart: "",
    trailer: "",
    tag: "",
    label: "",
    series: "",
    userrating: null,
    uservotes: null,
    detailurl: "",
    site: "",
  }
  currentMetadata.value = createMetadata
}

function validateForm() {
  formErrors.value = {}
  formValid.value = true

  // Validate required fields
  if (!currentMetadata.value.number?.trim()) {
    formErrors.value.number = t('components.metadata.form.validation.numberRequired')
    formValid.value = false
  }

  if (!currentMetadata.value.title?.trim()) {
    formErrors.value.title = t('components.metadata.form.validation.titleRequired')
    formValid.value = false
  }

  return formValid.value
}

async function handleSubmit() {
  if (!validateForm()) {
    return
  }

  isSubmitting.value = true
  try {
    if (updateMetadata) {
      await metadataStore.updateMetadata(currentMetadata.value)
    } else {
      await metadataStore.addMetadata(currentMetadata.value)
    }
  } catch (error) {
    console.error("Error submitting form:", error)
  } finally {
    isSubmitting.value = false
  }
}

// Trigger file selection dialog
function selectCoverImage() {
  if (fileInput.value) {
    fileInput.value.click()
  }
}

// Handle file upload
async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files || target.files.length === 0) {
    return
  }
  const file = target.files[0]
  // Validate file type
  if (!file.type.startsWith("image/")) {
    alert(t('components.metadata.form.imageTypeError'))
    return
  }

  isUploading.value = true
  try {
    // Create form data for upload
    const formData = {
      file: file,
    }

    // Upload image with existing path as custom URL if available
    const response = await ResourceService.uploadImage({
      formData: formData,
      customUrl: currentMetadata.value.cover || undefined,
    })

    let path = ""
    if (typeof response === "object" && response !== null) {
      if ("message" in response) {
        path = response.message as string
      }
    }

    if (path) {
      currentMetadata.value.cover = path
      // Force the coverImageUrl computed property to update by creating a new reactive dependency
      currentMetadata.value = { ...currentMetadata.value }
    } else {
      console.error("Could not determine path from upload response:", response)
      alert(t('components.metadata.form.uploadSuccess'))
    }
  } catch (error) {
    console.error("Image upload failed:", error)
    alert(t('components.metadata.form.uploadError'))
  } finally {
    isUploading.value = false
    if (fileInput.value) {
      fileInput.value.value = ""
    }
  }
}
</script>

<template>
  <VForm @submit.prevent="handleSubmit">
    <VRow>
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="number">{{ t('components.metadata.form.number') }} <span class="text-error">*</span></label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.number" :error-messages="formErrors.number" required />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="title">{{ t('components.metadata.form.title') }} <span class="text-error">*</span></label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.title" :error-messages="formErrors.title" required />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="studio">{{ t('components.metadata.form.studio') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.studio" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="release">{{ t('components.metadata.form.release') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.release" type="date" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="year">{{ t('components.metadata.form.year') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.year" type="number" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="runtime">{{ t('components.metadata.form.runtime') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.runtime" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="genre">{{ t('components.metadata.form.genre') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.genre" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="rating">{{ t('components.metadata.form.rating') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.rating" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="language">{{ t('components.metadata.form.language') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.language" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="country">{{ t('components.metadata.form.country') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.country" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="outline">{{ t('components.metadata.form.outline') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextarea v-model="currentMetadata.outline" rows="3" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="director">{{ t('components.metadata.form.director') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.director" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="actor">{{ t('components.metadata.form.actor') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.actor" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="actor_photo">{{ t('components.metadata.form.actorPhoto') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.actor_photo" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="cover">{{ t('components.metadata.form.cover') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <div class="d-flex align-center">
              <VTextField v-model="currentMetadata.cover" class="flex-grow-1 mr-2" />
              <VBtn :loading="isUploading" :disabled="isUploading" color="primary" @click="selectCoverImage"
                variant="outlined" size="small">
                <VIcon icon="bx-upload" class="mr-1" />
                {{ t('components.metadata.form.uploadCover') }}
              </VBtn>
              <!-- Hidden file input for upload -->
              <input ref="fileInput" type="file" accept="image/*" class="d-none" @change="handleFileUpload" />
            </div>

            <!-- Image preview -->
            <div v-if="coverImageUrl" class="mt-2">
              <VImg :src="coverImageUrl" max-height="200" contain class="rounded" />
            </div>
            
            <!-- Hint text about cover value behavior -->
            <div v-if="currentMetadata.cover" class="text-caption text-grey mt-1">
              <VIcon icon="bx-info-circle" size="small" class="mr-1" />
              Note: Uploading a new image will update the image content while keeping the same URL.
            </div>
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="cover_small">{{ t('components.metadata.form.coverSmall') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.cover_small" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="extrafanart">{{ t('components.metadata.form.extraFanart') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.extrafanart" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="trailer">{{ t('components.metadata.form.trailer') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.trailer" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="tag">{{ t('components.metadata.form.tag') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.tag" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="label">{{ t('components.metadata.form.label') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.label" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="series">{{ t('components.metadata.form.series') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.series" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="userrating">{{ t('components.metadata.form.userRating') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.userrating" type="number" min="0" max="10" step="0.1" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="uservotes">{{ t('components.metadata.form.userVotes') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.uservotes" type="number" min="0" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="detailurl">{{ t('components.metadata.form.detailUrl') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.detailurl" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="site">{{ t('components.metadata.form.site') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.site" />
          </VCol>
        </VRow>
      </VCol>

      <!-- 👉 submit and reset button -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" />
          <VCol cols="12" md="9">
            <VBtn type="submit" class="me-4" :loading="isSubmitting" :disabled="isSubmitting">
              {{ t('components.metadata.form.save') }}
            </VBtn>
            <VBtn type="button" color="secondary" variant="tonal" @click="metadataStore.showDialog = false">
              {{ t('components.metadata.form.cancel') }}
            </VBtn>
          </VCol>
        </VRow>
      </VCol>
    </VRow>
  </VForm>
</template>

<style>
.text-error {
  color: rgb(244, 67, 54);
}
</style>
