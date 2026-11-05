<!-- MediaItemDetailDialog.vue -->
<script setup lang="ts">
import SubtitleLibrary from "@/components/subtitle/SubtitleLibrary.vue"
import { useMediaItemStore } from "@/stores/mediaitem.store"
import { computed, ref, watch } from "vue"
import { useI18n } from "vue-i18n"

const dialog = useMediaItemStore()
const { t } = useI18n()
const detailTab = ref("details")
const subtitleCount = ref(0)

const subtitleMediaId = computed(() => {
  const item = dialog.editMediaItem
  if (!item?.id) return null
  if (!["movie", "video", "number", "episode"].includes(item.media_type || "")) return null
  return item.id
})

watch(
  () => dialog.editMediaItem?.id,
  () => {
    detailTab.value = "details"
    subtitleCount.value = 0
  },
)

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
      <VTabs v-if="subtitleMediaId" v-model="detailTab" density="comfortable" class="dialog-mediaitem-tabs">
        <VTab value="details">{{ t('pages.mediaitem.details') }}</VTab>
        <VTab value="subtitles">
          {{ t('pages.subtitles.section') }}
          <span v-if="subtitleCount" class="dialog-mediaitem-count">{{ subtitleCount }}</span>
        </VTab>
      </VTabs>
      <VCardText class="dialog-mediaitem-body">
        <div v-show="!subtitleMediaId || detailTab === 'details'">
          <MediaItemDetailForm
            v-if="dialog.showDialog"
            :key="`${dialog.editMediaItem?.id ?? 'new'}-${dialog.addDraft?.series_id ?? ''}-${dialog.addDraft?.media_type ?? ''}`"
            :updateMediaItem="dialog.editMediaItem"
          />
        </div>
        <SubtitleLibrary
          v-if="subtitleMediaId"
          v-show="detailTab === 'subtitles'"
          :key="subtitleMediaId"
          compact
          :fixed-media-id="subtitleMediaId"
          @count="subtitleCount = $event"
        />
      </VCardText>
    </VCard>
  </VDialog>
</template>

<style lang="scss">
.dialog-mediaitem-content {
  padding: 1rem 1rem 0;
}

.dialog-mediaitem-tabs {
  margin-top: 4px;
}

.dialog-mediaitem-body {
  padding-top: 16px;
}

.dialog-mediaitem-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  margin-inline-start: 8px;
  padding: 0 5px;
  border-radius: 9px;
  background: rgba(var(--v-theme-primary), 0.16);
  color: rgb(var(--v-theme-primary));
  font-size: 12px;
  line-height: 1;
}
</style>
