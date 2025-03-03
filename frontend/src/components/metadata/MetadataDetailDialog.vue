<!-- MetadataDetailDialog.vue -->
<script setup lang="ts">
import { useMetadataStore } from "@/stores/metadata.store"

const dialog = useMetadataStore()
</script>

<template>
  <VDialog v-model="dialog.showDialog" max-width="600" scrollable>
    <VCard class="dialog-metadata-content">
      <VCardTitle>
        <span v-if="dialog.editMetadata" class="ms-2">Edit Metadata</span>
        <span v-else class="ms-2">Add Metadata</span>
      </VCardTitle>
      <VCardItem>
        <MetadataDetailForm :updateMetadata="dialog.editMetadata" />
      </VCardItem>
    </VCard>
  </VDialog>
</template>

<style lang="scss">
.dialog-metadata-content {
  padding: 1rem;
}
</style>
