<!-- MetadataDetailDialog.vue -->
<script setup lang="ts">
import { MetadataPublic } from '@/client'
import { computed } from 'vue'

const props = defineProps<{
  modelValue: boolean
  metadata: MetadataPublic | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const dialogModel = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

function closeDialog() {
  emit('update:modelValue', false)
}
</script>

<template>
  <VDialog v-model="dialogModel" max-width="600px">
    <VCard>
      <VCardTitle>
        Edit Metadata
        <VSpacer></VSpacer>
        <VBtn icon @click="closeDialog">
          <VIcon>mdi-close</VIcon>
        </VBtn>
      </VCardTitle>
      
      <VCardText v-if="metadata">
        <VForm @submit.prevent>
          <VTextField
            v-model="metadata.number"
            label="Number"
            class="mb-4"
          />
          <VTextField
            v-model="metadata.title"
            label="Title"
            class="mb-4"
          />
          <VTextField
            v-model="metadata.actor"
            label="Actor"
            class="mb-4"
          />
          <VTextField
            v-model="metadata.site"
            label="Site"
            class="mb-4"
          />
          <VTextField
            v-model="metadata.detailurl"
            label="URL"
            class="mb-4"
          />
          <VTextField
            v-model="metadata.cover"
            label="Cover URL"
            class="mb-4"
          />
        </VForm>
      </VCardText>

      <VCardActions>
        <VSpacer />
        <VBtn color="primary" @click="closeDialog">
          Close
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>
