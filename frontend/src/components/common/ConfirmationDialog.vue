<script setup lang="ts">
import { useConfirmationStore } from "@/stores/confirmation.store"
import { computed } from "vue"
import { useI18n } from "vue-i18n"

const confirmationStore = useConfirmationStore()
const { t } = useI18n()

const cancelText = computed(
  () =>
    confirmationStore.options.cancelText ||
    t("components.common.confirmation.cancelText"),
)

const confirmText = computed(() => {
  if (confirmationStore.options.confirmText) {
    return confirmationStore.options.confirmText
  }
  if (confirmationStore.options.type === "delete") {
    return t("components.common.confirmation.deleteText")
  }
  return t("components.common.confirmation.confirmText")
})
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
          {{ cancelText }}
        </VBtn>
        <VBtn
          :color="confirmationStore.options.confirmColor"
          variant="elevated"
          @click="confirmationStore.confirm()"
        >
          {{ confirmText }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>
