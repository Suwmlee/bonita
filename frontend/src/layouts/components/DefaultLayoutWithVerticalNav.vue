<script setup lang="ts">
import NavItems from "@/layouts/components/NavItems.vue"
import logo from "@images/logo.png"
import LanguageSwitcher from "./LanguageSwitcher.vue"
import VerticalNavLayout from "./VerticalNavLayout.vue"

// Components
import NavbarThemeSwitcher from "@/layouts/components/NavbarThemeSwitcher.vue"
import UserProfile from "@/layouts/components/UserProfile.vue"
import { useAppStore } from "@/stores/app.store"
import { onMounted } from "vue"

const appStore = useAppStore()

onMounted(async () => {
  await appStore.fetchVersion()
})
</script>

<template>
  <VerticalNavLayout>
    <!-- 👉 navbar -->
    <template #navbar="{ toggleVerticalOverlayNavActive }">
      <div class="d-flex h-100 align-center">
        <!-- 👉 Vertical nav toggle in overlay mode -->
        <IconBtn class="ms-n3 d-lg-none" @click="toggleVerticalOverlayNavActive(true)">
          <VIcon icon="bx-menu" />
        </IconBtn>

        <VSpacer />

        <LanguageSwitcher class="me-1" />
        <NavbarThemeSwitcher class="me-1" />

        <UserProfile />
      </div>
    </template>

    <template #vertical-nav-header="{ toggleIsOverlayNavActive }">
      <RouterLink to="/" class="app-logo app-title-wrapper">
        <div class="d-flex">
          <VImg style="width: 38px;" :src="logo"></VImg>
        </div>

        <h1 class="logo-title">
          Bonita
        </h1>
      </RouterLink>

      <IconBtn class="d-block d-lg-none" @click="toggleIsOverlayNavActive(false)">
        <VIcon icon="bx-x" />
      </IconBtn>
    </template>

    <template #vertical-nav-content>
      <NavItems />
    </template>

    <template #after-vertical-nav-items>
      <div class="d-flex justify-center version-info">{{ appStore.version ? 'v' + appStore.version : '...' }}</div>
    </template>

    <!-- 👉 Pages -->
    <slot />

  </VerticalNavLayout>
</template>

<style lang="scss" scoped>
.meta-key {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 6px;
  block-size: 1.5625rem;
  line-height: 1.3125rem;
  padding-block: 0.125rem;
  padding-inline: 0.25rem;
}

.version-info {
  margin-top: 1rem;
  margin-bottom: 3rem;
  font-size: 1rem;
  opacity: 0.8;
}

.app-logo {
  display: flex;
  align-items: center;
  column-gap: 0.75rem;
}

.logo-title {
  font-size: 1.25rem;
  font-weight: 500;
  line-height: 1.75rem;
}
</style>