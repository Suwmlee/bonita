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
    icon: 'bx-task',
    to: '/records',
  }" />
  <VerticalNavLink :item="{
    title: 'Task',
    icon: 'bx-task',
    to: '/tasks/all',
  }" />
  <VerticalNavLink :item="{
    title: 'Scraping',
    icon: 'bx-detail',
    to: '/scraping/configs',
  }" />
  <VerticalNavLink :item="{
    title: 'Metadata',
    icon: 'bxs-user-detail',
    to: '/metadata',
  }" />
  <VerticalNavLink :item="{
    title: 'Tools',
    icon: 'bxs-user-detail',
    to: '/tools',
  }" />
  <VerticalNavLink :item="{
    title: 'ServiceSettings',
    icon: 'bxs-user-detail',
    to: '/settings/service',
  }" />
  <VerticalNavLink :item="{
    title: 'UserSettings',
    icon: 'bxs-user-detail',
    to: '/settings/user',
  }" />
</template>
