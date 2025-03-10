<script setup lang="ts">
import { useTaskStore } from "@/stores/task.store"
import { useI18n } from "vue-i18n"

const dialog = useTaskStore()
const { t } = useI18n() // 导入国际化工具函数
</script>

<template>
  <VDialog v-model="dialog.showDialog" max-width="600">
    <VCard class="dialog-setting-content">
      <VCardTitle>
        <span v-if="dialog.editTask" class="ms-2">{{ t('components.task.dialog.editTitle') }}</span>
        <span v-else class="ms-2">{{ t('components.task.dialog.addTitle') }}</span>
      </VCardTitle>
      <VCardItem>
        <TransferConfigDetailForm :updateTask="dialog.editTask" />
      </VCardItem>
    </VCard>
  </VDialog>
</template>

<style lang="scss">
.dialog-setting-content {
  padding: 1rem;
}
</style>
