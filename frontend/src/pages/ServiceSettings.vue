<script setup lang="ts">
import { useSettingStore } from "@/stores/setting.store"
import { storeToRefs } from "pinia"
import { onMounted, ref } from "vue"

// 使用 setting store
const settingStore = useSettingStore()
// 通过 storeToRefs 保持响应性
const { proxySettings, embyApiSettings, loading, saving, testingEmby } =
  storeToRefs(settingStore)
const testResult = ref<{ success?: boolean; message?: string } | null>(null)
const saveResult = ref<{ success: boolean; message: string } | null>(null)

const fetchProxySettings = async () => {
  await settingStore.fetchProxySettings()
}

const fetchEmbySettings = async () => {
  await settingStore.fetchEmbySettings()
}

const saveProxySettings = async () => {
  await settingStore.updateProxySettings()
}

const saveEmbyApiSettings = async () => {
  // 重置之前的保存结果
  saveResult.value = null
  
  // 确保字段有正确的值类型
  embyApiSettings.value.emby_host = embyApiSettings.value.emby_host || ""
  embyApiSettings.value.emby_apikey = embyApiSettings.value.emby_apikey || ""

  try {
    const response = await settingStore.saveEmbyApiSettings()
    saveResult.value = {
      success: true,
      message: "Emby设置已成功保存"
    }
    return response
  } catch (error) {
    console.error("Error saving Emby settings:", error)
    saveResult.value = {
      success: false,
      message: "保存Emby设置失败，请稍后重试"
    }
  }
  
  // 3秒后自动清除保存结果提示
  setTimeout(() => {
    saveResult.value = null
  }, 3000)
}

const testEmbyConnection = async () => {
  testResult.value = null

  try {
    // 确保 API Key 有值
    const apiKey = embyApiSettings.value.emby_apikey || ""

    const response = await settingStore.testEmbyConnection(apiKey)
    testResult.value = {
      success: response.success,
      message: response.message ?? "", // 使用空字符串作为 null 或 undefined 的默认值
    }
  } catch (error) {
    console.error("Error testing Emby connection:", error)
    testResult.value = {
      success: false,
      message: "测试连接失败，请检查您的设置和网络",
    }
  }
}

onMounted(() => {
  fetchProxySettings()
  fetchEmbySettings()
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

      <VCard>
        <VCardTitle>Emby API 设置</VCardTitle>
        <VCardSubtitle>
          配置Emby服务器API连接参数
        </VCardSubtitle>
        <VCardText>
          <VForm :loading="loading">
            <VRow>
              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="embyUrl">Emby 服务器</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="embyApiSettings.emby_host" placeholder="例如: http://emby.example.com:8096" />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="embyApiKey">API Key</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="embyApiSettings.emby_apikey" type="password" placeholder="Emby API Key" />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow>
                  <VCol>
                    <VBtn color="primary" :loading="saving" @click="saveEmbyApiSettings" class="mr-2">
                      保存设置
                    </VBtn>
                    <VBtn color="secondary" :loading="testingEmby" @click="testEmbyConnection">
                      测试连接
                    </VBtn>
                  </VCol>
                </VRow>
              </VCol>
              
              <VCol cols="12" v-if="saveResult">
                <VAlert :type="saveResult.success ? 'success' : 'error'" variant="tonal" density="compact" class="mb-3">
                  {{ saveResult.message }}
                </VAlert>
              </VCol>
              
              <VCol cols="12" v-if="testResult">
                <VAlert :type="testResult.success ? 'success' : 'error'" variant="tonal" density="compact">
                  {{ testResult.message || (testResult.success ? '连接成功！' : '连接失败！') }}
                </VAlert>
              </VCol>
            </VRow>
          </VForm>
        </VCardText>
      </VCard>
    </VCol>
  </VRow>
</template>
