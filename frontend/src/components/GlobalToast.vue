<script setup lang="ts">
import { useToastStore } from "@/stores/toast.store"

const toast = useToastStore()
</script>

<template>
  <v-snackbar
    v-model="toast.visible"
    :color="toast.color"
    timeout="-1"
    rounded
    :style="{ bottom: `18vh` }"
    min-width="300"
  >
    {{ toast.msg }}
    <template #actions>
      <v-btn
        color="white"
        icon="bx-x"
        @click="toast.visible = false"
      />
    </template>
  </v-snackbar>
</template>

<style scoped>

</style>
