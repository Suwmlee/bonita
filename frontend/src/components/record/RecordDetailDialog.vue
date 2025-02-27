<script setup lang="ts">
import { useRecordStore } from "@/stores/record.store"

const dialog = useRecordStore()
</script>

<template>
  <VDialog v-model="dialog.showDialog" max-width="600">
    <VCard class="dialog-setting-content">
      <VCardTitle>
        <span class="ms-2">Edit</span>
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
