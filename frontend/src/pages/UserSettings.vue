<script lang="ts" setup>
import AccountSettingsSecurity from "@/views/settings/AccountSettingsSecurity.vue"
import { useI18n } from "vue-i18n"

const route = useRoute()
const { t } = useI18n() // 导入国际化工具函数

const activeTab = ref(route.params.tab)

// tabs
const tabs = [
  {
    title: t("pages.userSettings.tabs.security"),
    icon: "bx-lock-open",
    tab: "security",
  },
]
</script>

<template>
  <div>
    <p class="text-xl mb-6">
      {{ t('pages.userSettings.title') }}
    </p>
    
    <VTabs v-model="activeTab" show-arrows class="v-tabs-pill">
      <VTab v-for="item in tabs" :key="item.icon" :value="item.tab">
        <VIcon size="20" start :icon="item.icon" />
        {{ item.title }}
      </VTab>
    </VTabs>

    <VWindow v-model="activeTab" class="mt-5 disable-tab-transition">
      <!-- Security -->
      <VWindowItem value="security">
        <AccountSettingsSecurity />
      </VWindowItem>
    </VWindow>
  </div>
</template>
