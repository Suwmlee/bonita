<script setup lang="ts">
import { useRecordStore } from "@/stores/record.store"
import { useI18n } from "vue-i18n"

const dialog = useRecordStore()
const { t } = useI18n() // 导入国际化工具函数
</script>

<template>
  <VDialog v-model="dialog.showDialog" max-width="600">
    <VCard class="dialog-setting-content">
      <VCardTitle>
        <span class="ms-2">{{ t('components.record.dialog.editTitle') }}</span>
      </VCardTitle>
      <VCardItem>
        <RecordDetailForm :updateRecord="dialog.editRecord" />
      </VCardItem>
    </VCard>
  </VDialog>
</template>

<style lang="scss">
.dialog-setting-content {
  padding: 1rem;
}
</style>
