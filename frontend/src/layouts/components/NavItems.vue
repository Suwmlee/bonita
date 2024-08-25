<script lang="ts" setup>
import VerticalNavSectionTitle from "@/@layouts/components/VerticalNavSectionTitle.vue"
import VerticalNavLink from "@layouts/components/VerticalNavLink.vue"
</script>

<template>
  <VerticalNavLink :item="{
    title: 'Dashboard',
    icon: 'bx-home',
    to: '/dashboard',
  }" />
  <!-- 👉 Pages -->
  <VerticalNavSectionTitle :item="{
    heading: 'Pages',
  }" />
  <VerticalNavLink :item="{
    title: 'Login',
    icon: 'bx-log-in',
    to: '/login',
  }" />

  <!-- 👉 User Interface -->
  <VerticalNavSectionTitle :item="{
    heading: 'User Interface',
  }" />
  <VerticalNavLink :item="{
    title: 'Settings',
    icon: 'bx-home',
    to: '/settings',
  }" />
</template>
