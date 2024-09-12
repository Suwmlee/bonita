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
    title: 'Task',
    icon: 'bx-task',
    to: '/tasks/transfer',
  }" />
  <VerticalNavLink :item="{
    title: 'Scraping',
    icon: 'bx-detail',
    to: '/scraping/settings',
  }" />
  <VerticalNavLink :item="{
    title: 'UserSettings',
    icon: 'bxs-user-detail',
    to: '/settings/user',
  }" />
</template>
