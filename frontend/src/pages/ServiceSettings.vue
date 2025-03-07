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
  <div class="proxy-settings-container">
    <VCard class="mb-6">
      <VCardTitle>代理设置</VCardTitle>
      <VCardText>
        <VForm :loading="loading">
          <VRow>
            <VCol cols="12">
              <VTextField 
                v-model="proxySettings.http" 
                label="HTTP 代理"
                placeholder="例如: http://127.0.0.1:7890"
              />
            </VCol>
            
            <VCol cols="12">
              <VTextField 
                v-model="proxySettings.https" 
                label="HTTPS 代理"
                placeholder="例如: http://127.0.0.1:7890"
              />
            </VCol>
            
            <VCol cols="12">
              <VSwitch
                v-model="proxySettings.enabled"
                label="启用代理"
                color="primary"
                inset
              />
            </VCol>
            
            <VCol cols="12">
              <VBtn 
                color="primary" 
                :loading="saving" 
                @click="saveProxySettings"
              >
                保存设置
              </VBtn>
            </VCol>
          </VRow>
        </VForm>
      </VCardText>
    </VCard>
    
    <div class="mt-4">
      <p class="text-gray-700">
        提示: 此处配置的代理将用于应用程序的网络请求，包括爬虫和API调用。
      </p>
    </div>
  </div>
</template>

<style scoped>
.proxy-settings-container {
  max-width: 600px;
}
</style>
