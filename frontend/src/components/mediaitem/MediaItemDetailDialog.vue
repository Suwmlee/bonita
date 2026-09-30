<!-- MediaItemDetailDialog.vue -->
<script setup lang="ts">
import { useMediaItemStore } from "@/stores/mediaitem.store"
import { useI18n } from "vue-i18n"

const dialog = useMediaItemStore()
const { t } = useI18n()

function onDialogVisible(value: boolean) {
  if (!value) {
    dialog.closeDialog()
  }
}
</script>

<template>
  <VDialog :model-value="dialog.showDialog" max-width="820" scrollable @update:model-value="onDialogVisible">
    <VCard class="dialog-mediaitem-content">
      <VCardTitle class="d-flex align-center">
        <VBtn
          v-if="dialog.dialogHistory.length"
          icon
          variant="text"
          size="small"
          class="me-1"
          :aria-label="t('common.back')"
          @click="dialog.goBackInDialog"
        >
          <VIcon icon="bx-chevron-left" />
        </VBtn>
        <span v-if="dialog.editMediaItem">{{ t('pages.mediaitem.editMediaItem') }}</span>
        <span v-else>{{ t('pages.mediaitem.addMediaItem') }}</span>
      </VCardTitle>
      <VCardItem>
        <MediaItemDetailForm
          v-if="dialog.showDialog"
          :key="`${dialog.editMediaItem?.id ?? 'new'}-${dialog.addDraft?.series_id ?? ''}-${dialog.addDraft?.media_type ?? ''}`"
          :updateMediaItem="dialog.editMediaItem"
        />
      </VCardItem>
    </VCard>
  </VDialog>
</template>

<style lang="scss">
.dialog-mediaitem-content {
  padding: 1rem;
}
</style>
