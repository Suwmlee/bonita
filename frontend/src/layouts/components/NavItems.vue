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
    title: 'Records',
    icon: 'bx-objects-horizontal-left',
    to: '/records',
  }" />
  <VerticalNavLink :item="{
    title: 'Task',
    icon: 'bx-task',
    to: '/tasks/all',
  }" />
  <VerticalNavLink :item="{
    title: 'Scraping',
    icon: 'bxs-magic-wand',
    to: '/scraping/configs',
  }" />
  <VerticalNavLink :item="{
    title: 'Metadata',
    icon: 'bxs-data',
    to: '/metadata',
  }" />
  <VerticalNavLink :item="{
    title: 'Tools',
    icon: 'bxs-wrench',
    to: '/tools',
  }" />
  <VerticalNavLink :item="{
    title: 'ServiceSettings',
    icon: 'bxs-server',
    to: '/settings/service',
  }" />
  <VerticalNavLink :item="{
    title: 'UserSettings',
    icon: 'bxs-user-detail',
    to: '/settings/user',
  }" />
</template>
