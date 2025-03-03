<script lang="ts" setup>
import type { MetadataPublic } from "@/client/types.gen"
import { useMetadataStore } from "@/stores/metadata.store"

interface Props {
  updateMetadata?: MetadataPublic
}
const props = defineProps<Props>()

const metadataStore = useMetadataStore()

const { updateMetadata } = props as {
  updateMetadata: MetadataPublic
}
const currentMetadata = ref<any>()

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

async function handleSubmit() {
  console.log(currentMetadata)
  if (updateMetadata) {
    metadataStore.updateMetadata(currentMetadata.value)
  } else {
    // Assume there would be an addMetadata method in the store
    // metadataStore.addMetadata(currentMetadata.value)
  }
}
</script>

<template>
  <VForm @submit.prevent="handleSubmit">
    <VRow>
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="number">Number</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.number" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="title">Title</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentMetadata.title" />
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
            <VTextField v-model="currentMetadata.cover" />
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
            <VBtn type="submit" class="me-4">
              Submit
            </VBtn>
          </VCol>
        </VRow>
      </VCol>
    </VRow>
  </VForm>
</template>
