<!-- MediaItemDetailDialog.vue -->
<script setup lang="ts">
import { useMediaItemStore } from "@/stores/mediaitem.store"
import { useI18n } from "vue-i18n"

const dialog = useMediaItemStore()
const { t } = useI18n() // 导入国际化工具函数
</script>

<template>
  <VDialog v-model="dialog.showDialog" max-width="600" scrollable>
    <VCard class="dialog-mediaitem-content">
      <VCardTitle>
        <span v-if="dialog.editMediaItem" class="ms-2">{{ t('pages.mediaitem.editMediaItem') }}</span>
        <span v-else class="ms-2">{{ t('pages.mediaitem.addMediaItem') }}</span>
      </VCardTitle>
      <VCardItem>
        <MediaItemDetailForm :updateMediaItem="dialog.editMediaItem" />
      </VCardItem>
    </VCard>
  </VDialog>
</template>

<style lang="scss">
.dialog-mediaitem-content {
  padding: 1rem;
}
</style> 