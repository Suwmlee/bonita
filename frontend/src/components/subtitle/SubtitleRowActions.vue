<script setup lang="ts">
import type { SubtitlePublic } from "@/client"
import { useI18n } from "vue-i18n"

defineProps<{
  item: SubtitlePublic
}>()

const emit = defineEmits<{
  edit: []
  deliver: []
  use: []
  remove: []
}>()

const { t } = useI18n()
</script>

<template>
  <div class="subtitle-row-actions">
    <VBtn size="small" variant="text" :title="t('common.edit')" @click="emit('edit')">
      <VIcon icon="bx-edit-alt" />
    </VBtn>
    <VBtn
      v-if="item.preferred"
      size="small"
      variant="text"
      :title="t('pages.subtitles.retransfer')"
      :disabled="!item.media_item_id"
      @click="emit('deliver')"
    >
      <VIcon icon="bx-refresh" />
    </VBtn>
    <VBtn
      v-else
      size="small"
      variant="text"
      :title="t('pages.subtitles.useThis')"
      :disabled="!item.media_item_id"
      @click="emit('use')"
    >
      <VIcon icon="bx-check-circle" />
    </VBtn>
    <VBtn size="small" variant="text" color="error" :title="t('common.delete')" @click="emit('remove')">
      <VIcon icon="bx-trash" />
    </VBtn>
  </div>
</template>

<style scoped>
.subtitle-row-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 4px;
}
</style>
