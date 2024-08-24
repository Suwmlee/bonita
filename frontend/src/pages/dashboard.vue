<template>
  <div>
  </div>
</template>

<script lang="ts" setup>
import { UsersService } from "@/client/services.gen"

const currentUser = await UsersService.readUserMe()
console.log(currentUser)
</script>
