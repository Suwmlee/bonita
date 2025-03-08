<script lang="ts" setup>
import { OpenAPI, ResourceService } from "@/client"
import type { MetadataPublic } from "@/client/types.gen"
import { useMetadataStore } from "@/stores/metadata.store"
import { computed, ref } from "vue"

interface Props {
  updateMetadata?: MetadataPublic
}
const props = defineProps<Props>()

const metadataStore = useMetadataStore()
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

  // If it's already a full URL, return it as is
  if (currentMetadata.value.cover.startsWith("http")) {
    return currentMetadata.value.cover
  }

  // Otherwise, use the ResourceService to get the image URL
  return `${OpenAPI.BASE}/api/v1/resource/image?path=${encodeURIComponent(currentMetadata.value.cover)}`
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
    formErrors.value.number = "Number is required"
    formValid.value = false
  }

  if (!currentMetadata.value.title?.trim()) {
    formErrors.value.title = "Title is required"
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
    alert("Please select an image file (JPEG, PNG, etc.).")
    return
  }

  isUploading.value = true
  try {
    // Create form data for upload
    const formData = {
      file: file,
    }

    // Upload image
    const response = await ResourceService.uploadImage({
      formData: formData,
    })

    let path = ""
    if (typeof response === "object" && response !== null) {
      if ("message" in response) {
        path = response.message as string
      }
    }

    if (path) {
      currentMetadata.value.cover = path
    } else {
      console.error("Could not determine path from upload response:", response)
      alert(
        "Image uploaded successfully, but could not determine path. Check the console for details.",
      )
    }
  } catch (error) {
    console.error("Image upload failed:", error)
    alert("Failed to upload image. Please try again.")
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
            <label for="number">Number <span class="text-error">*</span></label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.number" :error-messages="formErrors.number" required />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="title">Title <span class="text-error">*</span></label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.title" :error-messages="formErrors.title" required />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="studio">Studio</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.studio" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="release">Release Date</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.release" type="date" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="year">Year</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.year" type="number" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="runtime">Runtime</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.runtime" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="genre">Genre</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.genre" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="rating">Rating</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.rating" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="language">Language</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.language" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="country">Country</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.country" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="outline">Outline</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextarea v-model="currentMetadata.outline" rows="3" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="director">Director</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.director" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="actor">Actor</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.actor" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="actor_photo">Actor Photo URL</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.actor_photo" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="cover">Cover URL</label>
          </VCol>
          <VCol cols="12" md="9">
            <div class="d-flex align-center">
              <VTextField v-model="currentMetadata.cover" class="flex-grow-1 mr-2" />
              <VBtn :loading="isUploading" :disabled="isUploading" color="primary" @click="selectCoverImage"
                variant="outlined" size="small">
                <VIcon icon="bx-upload" class="mr-1" />
                Upload
              </VBtn>
              <!-- Hidden file input for upload -->
              <input ref="fileInput" type="file" accept="image/*" class="d-none" @change="handleFileUpload" />
            </div>

            <!-- Image preview -->
            <div v-if="coverImageUrl" class="mt-2">
              <VImg :src="coverImageUrl" max-height="200" contain class="rounded" />
            </div>
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="cover_small">Cover Small URL</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.cover_small" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="extrafanart">Extra FanArt</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.extrafanart" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="trailer">Trailer URL</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.trailer" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="tag">Tags</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.tag" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="label">Label</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.label" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="series">Series</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.series" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="userrating">User Rating</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.userrating" type="number" min="0" max="10" step="0.1" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="uservotes">User Votes</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.uservotes" type="number" min="0" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="detailurl">Detail URL</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.detailurl" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="site">Site</label>
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
              Submit
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
