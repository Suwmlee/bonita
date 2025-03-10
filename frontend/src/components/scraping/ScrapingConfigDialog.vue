<script setup lang="ts">
import { useScrapingStore } from "@/stores/scraping.store"
import { useI18n } from "vue-i18n"

const dialog = useScrapingStore()
const { t } = useI18n() // 导入国际化工具函数
</script>

<template>
  <VDialog v-model="dialog.showDialog" max-width="600">
    <VCard class="dialog-setting-content">
      <VCardTitle>
        <span v-if="dialog.editSetting" class="ms-2">{{ t('components.scraping.dialog.editTitle') }}</span>
        <span v-else class="ms-2">{{ t('components.scraping.dialog.addTitle') }}</span>
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
