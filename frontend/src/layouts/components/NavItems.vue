<script lang="ts" setup>
import VerticalNavLink from "@layouts/components/VerticalNavLink.vue"
</script>

<template>
  <VerticalNavLink :item="{
    title: 'Dashboard',
    icon: 'bx-home',
    to: '/dashboard',
  }" />
  <VerticalNavLink :item="{
    title: 'Settings',
    icon: 'bx-cog',
    to: '/settings',
  }" />
</template>
