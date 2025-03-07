<script setup lang="ts">
import { useSettingStore } from "@/stores/setting.store"
import { storeToRefs } from "pinia"
import { onMounted } from "vue"

// 使用 setting store
const settingStore = useSettingStore()
// 通过 storeToRefs 保持响应性
const { proxySettings, loading, saving } = storeToRefs(settingStore)

const fetchProxySettings = async () => {
  await settingStore.fetchProxySettings()
}

const saveProxySettings = async () => {
  await settingStore.updateProxySettings()
}

onMounted(() => {
  fetchProxySettings()
})
</script>

<template>
  <p class="text-xl mb-6">
    服务配置
  </p>
  <VRow>
    <VCol cols="12" md="7" lg="5">
      <VCard class="mb-6">
        <VCardTitle>代理设置</VCardTitle>
        <VCardSubtitle>
          此处配置的代理将用于应用程序的网络请求
        </VCardSubtitle>
        <VCardText>
          <VForm :loading="loading">
            <VRow>
              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="http">HTTP 代理</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="proxySettings.http" />
                  </VCol>
                </VRow>
              </VCol>
              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="https">HTTPS 代理</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="proxySettings.https" placeholder="例如: http://127.0.0.1:7890" />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VSwitch v-model="proxySettings.enabled" label="启用代理" color="primary" inset />
              </VCol>

              <VCol cols="12">
                <VBtn color="primary" :loading="saving" @click="saveProxySettings">
                  保存设置
                </VBtn>
              </VCol>
            </VRow>
          </VForm>
        </VCardText>
      </VCard>
    </VCol>
  </VRow>
</template>
