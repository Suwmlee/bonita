<script setup lang="ts">
import { UsersService } from "@/client/services.gen"

async function getUser() {
  const currentUser = await UsersService.readUserMe()
  console.log(currentUser)
}

onMounted(() => {
  getUser()
})
</script>

<template>
  <div>
    Settings
  </div>
</template>
