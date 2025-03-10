<!-- MetadataDetailDialog.vue -->
<script setup lang="ts">
import { useMetadataStore } from "@/stores/metadata.store"
import { useI18n } from "vue-i18n"

const dialog = useMetadataStore()
const { t } = useI18n() // 导入国际化工具函数
</script>

<template>
  <VDialog v-model="dialog.showDialog" max-width="600" scrollable>
    <VCard class="dialog-metadata-content">
      <VCardTitle>
        <span v-if="dialog.editMetadata" class="ms-2">{{ t('pages.metadata.editMetadata') }}</span>
        <span v-else class="ms-2">{{ t('pages.metadata.addMetadata') }}</span>
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
