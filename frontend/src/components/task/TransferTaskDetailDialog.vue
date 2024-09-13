<script setup lang="ts">
import { useTaskStore } from "@/stores/task.store"

const dialog = useTaskStore()
</script>

<template>
  <VDialog v-model="dialog.showDialog" max-width="600">
    <VCard class="dialog-setting-content">
      <VCardTitle>
        <span v-if="dialog.editTask" class="ms-2">Edit</span>
        <span v-else class="ms-2">Add</span>
      </VCardTitle>
      <VCardItem>
        <TransferTaskDetailForm :updateTask="dialog.editTask" />
      </VCardItem>
    </VCard>
  </VDialog>
</template>

<style lang="scss">
.dialog-setting-content {
  padding: 1rem;
}
</style>
