<script setup lang="ts">
import { useConfirmationStore } from "@/stores/confirmation.store"

const confirmationStore = useConfirmationStore()
</script>

<template>
  <VDialog
    v-model="confirmationStore.show"
    max-width="500"
    persistent
  >
    <VCard>
      <VCardTitle class="text-h5">
        {{ confirmationStore.options.title }}
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
          {{ confirmationStore.options.cancelText }}
        </VBtn>
        <VBtn
          :color="confirmationStore.options.confirmColor"
          variant="elevated"
          @click="confirmationStore.confirm()"
        >
          {{ confirmationStore.options.confirmText }}
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template> 