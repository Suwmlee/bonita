<script setup lang="ts">
import { useAppStore } from "@/stores/app.store"
import type { ThemeSwitcherTheme } from "@layouts/types"
import { useTheme } from "vuetify"

const { name: themeName, global: globalTheme } = useTheme()
const themes: ThemeSwitcherTheme[] = [
  {
    name: "light",
    icon: "bx-sun",
  },
  {
    name: "dark",
    icon: "bx-moon",
  },
]
const appStore = useAppStore()
// Update appStore if theme is changed from other sources
watch(
  () => globalTheme.name.value,
  (val) => {
    appStore.updateTheme(val)
  },
)

const savedTheme = appStore.getTheme()
globalTheme.name.value = savedTheme
</script>

<template>
  <ThemeSwitcher :themes="themes" />
</template>
