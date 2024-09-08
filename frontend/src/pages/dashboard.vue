<script setup lang="ts">
import { UserService } from "@/client/services.gen"

async function getUser() {
  const currentUser = await UserService.readUserMe()
  console.log(currentUser)
}

onMounted(() => {
  getUser()
})
</script>

<template>
  <div>
    Dashboard
  </div>
</template>
