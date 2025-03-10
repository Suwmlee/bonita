<script setup lang="ts">
import { useConfirmationStore } from "@/stores/confirmation.store"
import { useI18n } from "vue-i18n"

const confirmationStore = useConfirmationStore()
const { t } = useI18n() // 导入国际化工具函数
</script>

<template>
  <VDialog
    v-model="confirmationStore.show"
    max-width="500"
    persistent
  >
    <VCard>
      <VCardTitle class="text-h5">
        {{ confirmationStore.options.title || t('components.common.confirmation.title') }}
      </VCardTitle>

      <VCardText>
        {{ confirmationStore.options.message }}
      </VCardText>

      <VCardActions>
        <VSpacer></VSpacer>
        <VBtn
          variant="text"
          @click="confirmationStore.cancel()"
        >
          {{ confirmationStore.options.cancelText || t('components.common.confirmation.cancelText') }}
        </VBtn>
        <VBtn
          :color="confirmationStore.options.confirmColor"
          variant="elevated"
          @click="confirmationStore.confirm()"
        >
          {{ confirmationStore.options.confirmText || t('components.common.confirmation.confirmText') }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template> 