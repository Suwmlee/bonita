<script lang="ts" setup>
import VerticalNavLink from "@layouts/components/VerticalNavLink.vue"
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <VerticalNavLink :item="{
    title: t('navitems.dashboard'),
    icon: 'bx-home',
    to: '/dashboard',
  }" />
  <VerticalNavLink :item="{
    title: t('navitems.records'),
    icon: 'bx-objects-horizontal-left',
    to: '/records',
  }" />
  <VerticalNavLink :item="{
    title: t('navitems.tasks'),
    icon: 'bx-task',
    to: '/tasks/all',
  }" />
  <VerticalNavLink :item="{
    title: t('navitems.scraping'),
    icon: 'bxs-magic-wand',
    to: '/scraping/configs',
  }" />
  <VerticalNavLink :item="{
    title: t('navitems.metadata'),
    icon: 'bxs-data',
    to: '/metadata',
  }" />
  <VerticalNavLink :item="{
    title: t('navitems.tools'),
    icon: 'bxs-wrench',
    to: '/tools',
  }" />
  <VerticalNavLink :item="{
    title: t('navitems.serviceSettings'),
    icon: 'bxs-server',
    to: '/settings/service',
  }" />
  <VerticalNavLink :item="{
    title: t('navitems.userSettings'),
    icon: 'bxs-user-detail',
    to: '/settings/user',
  }" />
</template>
