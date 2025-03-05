<script setup lang="ts">
import { useScrapingStore } from "@/stores/scraping.store"

const dialog = useScrapingStore()
</script>

<template>
  <VDialog v-model="dialog.showDialog" max-width="600">
    <VCard class="dialog-setting-content">
      <VCardTitle>
        <span v-if="dialog.editSetting" class="ms-2">Edit</span>
        <span v-else class="ms-2">Add</span>
      </VCardTitle>
      <VCardItem>
        <ScrapingConfigForm :updateSetting="dialog.editSetting" />
      </VCardItem>
    </VCard>
  </VDialog>
</template>

<style lang="scss">
.dialog-setting-content {
  padding: 1rem;
}
</style>
