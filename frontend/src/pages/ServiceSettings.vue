<script setup lang="ts">
import { useSettingStore } from "@/stores/setting.store"
import { storeToRefs } from "pinia"
import { computed, onMounted, ref } from "vue"
import { useI18n } from "vue-i18n"

// 使用 setting store
const settingStore = useSettingStore()
const { t } = useI18n() // 导入国际化工具函数

// 通过 storeToRefs 保持响应性
const {
  proxySettings,
  embyApiSettings,
  transmissionSettings,
  qbittorrentSettings,
  loading,
  saving,
  testingEmby,
  testingTransmission,
  testingQBittorrent,
} = storeToRefs(settingStore)
const testResult = ref<{ success?: boolean; message?: string } | null>(null)
const saveResult = ref<{ success: boolean; message: string } | null>(null)
const transmissionTestResult = ref<{
  success?: boolean
  message?: string
} | null>(null)
const transmissionSaveResult = ref<{
  success: boolean
  message: string
} | null>(null)
const qbittorrentTestResult = ref<{
  success?: boolean
  message?: string
} | null>(null)
const qbittorrentSaveResult = ref<{
  success: boolean
  message: string
} | null>(null)

const embyWebhookUrl = computed(() => {
  const base = (import.meta.env.VITE_API_URL || window.location.origin).replace(/\/$/, "")
  return `${base}/api/v1/webhooks/emby`
})

const fetchProxySettings = async () => {
  await settingStore.fetchProxySettings()
}

const fetchEmbySettings = async () => {
  await settingStore.fetchEmbySettings()
}

const fetchTransmissionSettings = async () => {
  await settingStore.fetchTransmissionSettings()
}

const fetchQBittorrentSettings = async () => {
  await settingStore.fetchQBittorrentSettings()
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
  embyApiSettings.value.emby_user = embyApiSettings.value.emby_user || ""

  try {
    const response = await settingStore.saveEmbyApiSettings()
    saveResult.value = {
      success: true,
      message: t("pages.serviceSettings.emby.saveSuccess"),
    }
    return response
  } catch (error) {
    console.error("Error saving Emby settings:", error)
    saveResult.value = {
      success: false,
      message: t("pages.serviceSettings.emby.saveError"),
    }
  }

  // 3秒后自动清除保存结果提示
  setTimeout(() => {
    saveResult.value = null
  }, 3000)
}

const saveTransmissionSettings = async () => {
  // 重置之前的保存结果
  transmissionSaveResult.value = null

  // 确保字段有正确的值类型
  transmissionSettings.value.transmission_host =
    transmissionSettings.value.transmission_host || ""
  transmissionSettings.value.transmission_username =
    transmissionSettings.value.transmission_username || ""
  transmissionSettings.value.transmission_password =
    transmissionSettings.value.transmission_password || ""

  try {
    const response = await settingStore.saveTransmissionSettings()
    transmissionSaveResult.value = {
      success: true,
      message: t("pages.serviceSettings.transmission.saveSuccess"),
    }
    return response
  } catch (error) {
    console.error("Error saving Transmission settings:", error)
    transmissionSaveResult.value = {
      success: false,
      message: t("pages.serviceSettings.transmission.saveError"),
    }
  }

  // 3秒后自动清除保存结果提示
  setTimeout(() => {
    transmissionSaveResult.value = null
  }, 3000)
}

const saveQBittorrentSettings = async () => {
  qbittorrentSaveResult.value = null
  qbittorrentSettings.value.qbittorrent_host =
    qbittorrentSettings.value.qbittorrent_host || ""
  qbittorrentSettings.value.qbittorrent_username =
    qbittorrentSettings.value.qbittorrent_username || ""
  qbittorrentSettings.value.qbittorrent_password =
    qbittorrentSettings.value.qbittorrent_password || ""

  try {
    const response = await settingStore.saveQBittorrentSettings()
    qbittorrentSaveResult.value = {
      success: true,
      message: t("pages.serviceSettings.qbittorrent.saveSuccess"),
    }
    return response
  } catch (error) {
    console.error("Error saving qBittorrent settings:", error)
    qbittorrentSaveResult.value = {
      success: false,
      message: t("pages.serviceSettings.qbittorrent.saveError"),
    }
  }

  setTimeout(() => {
    qbittorrentSaveResult.value = null
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
      message: t("pages.serviceSettings.emby.testError"),
    }
  }
}

const testTransmissionConnection = async () => {
  transmissionTestResult.value = null

  try {
    const response = await settingStore.testTransmissionConnection()
    transmissionTestResult.value = {
      success: response.success,
      message: response.message ?? "", // 使用空字符串作为 null 或 undefined 的默认值
    }
  } catch (error) {
    console.error("Error testing Transmission connection:", error)
    transmissionTestResult.value = {
      success: false,
      message: t("pages.serviceSettings.transmission.testError"),
    }
  }
}

const testQBittorrentConnection = async () => {
  qbittorrentTestResult.value = null

  try {
    const response = await settingStore.testQBittorrentConnection()
    qbittorrentTestResult.value = {
      success: response.success,
      message: response.message ?? "",
    }
  } catch (error) {
    console.error("Error testing qBittorrent connection:", error)
    qbittorrentTestResult.value = {
      success: false,
      message: t("pages.serviceSettings.qbittorrent.testError"),
    }
  }
}

onMounted(() => {
  fetchProxySettings()
  fetchEmbySettings()
  fetchTransmissionSettings()
  fetchQBittorrentSettings()
})
</script>

<template>
  <p class="text-xl mb-6">
    {{ t('pages.serviceSettings.title') }}
  </p>
  <VRow>
    <VCol cols="12" sm="8" md="6" lg="5" xl="4">
      <VCard class="mb-6">
        <VCardTitle>{{ t('pages.serviceSettings.proxy.title') }}</VCardTitle>
        <VCardSubtitle>
          {{ t('pages.serviceSettings.proxy.subtitle') }}
        </VCardSubtitle>
        <VCardText>
          <VForm :loading="loading">
            <VRow>
              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="http">{{ t('pages.serviceSettings.proxy.http') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="proxySettings.http" />
                  </VCol>
                </VRow>
              </VCol>
              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="https">{{ t('pages.serviceSettings.proxy.https') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="proxySettings.https" :placeholder="t('pages.serviceSettings.proxy.httpsPlaceholder')" />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VSwitch v-model="proxySettings.enabled" :label="t('pages.serviceSettings.proxy.enable')" color="primary" inset />
              </VCol>

              <VCol cols="12">
                <VBtn color="primary" :loading="saving" @click="saveProxySettings">
                  {{ t('pages.serviceSettings.proxy.save') }}
                </VBtn>
              </VCol>
            </VRow>
          </VForm>
        </VCardText>
      </VCard>

      <VCard class="mb-6">
        <VCardTitle>{{ t('pages.serviceSettings.emby.title') }}</VCardTitle>
        <VCardSubtitle>
          {{ t('pages.serviceSettings.emby.subtitle') }}
        </VCardSubtitle>
        <VCardText>
          <VForm :loading="loading">
            <VRow>
              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="embyUrl">{{ t('pages.serviceSettings.emby.server') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="embyApiSettings.emby_host" :placeholder="t('pages.serviceSettings.emby.serverPlaceholder')" />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="embyUser">{{ t('pages.serviceSettings.emby.user') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="embyApiSettings.emby_user" :placeholder="t('pages.serviceSettings.emby.userPlaceholder')" />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="embyApiKey">{{ t('pages.serviceSettings.emby.apiKey') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="embyApiSettings.emby_apikey" :placeholder="t('pages.serviceSettings.emby.apiKeyPlaceholder')" />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VSwitch v-model="embyApiSettings.enabled" :label="t('pages.serviceSettings.emby.enable')" color="primary" inset />
              </VCol>

              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label>{{ t('pages.serviceSettings.emby.webhookUrl') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField :model-value="embyWebhookUrl" readonly hide-details />
                    <div class="text-caption text-medium-emphasis mt-1">
                      {{ t('pages.serviceSettings.emby.webhookHint') }}
                    </div>
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow>
                  <VCol>
                    <VBtn color="primary" :loading="saving" @click="saveEmbyApiSettings" class="mr-2">
                      {{ t('pages.serviceSettings.emby.save') }}
                    </VBtn>
                    <VBtn color="secondary" :loading="testingEmby" @click="testEmbyConnection">
                      {{ t('pages.serviceSettings.emby.test') }}
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
                  {{ testResult.message || (testResult.success ? t('pages.serviceSettings.emby.connectionSuccess') : t('pages.serviceSettings.emby.connectionError')) }}
                </VAlert>
              </VCol>
            </VRow>
          </VForm>
        </VCardText>
      </VCard>

      <VCard class="mb-6">
        <VCardTitle>{{ t('pages.serviceSettings.transmission.title') }}</VCardTitle>
        <VCardSubtitle>
          {{ t('pages.serviceSettings.transmission.subtitle') }}
        </VCardSubtitle>
        <VCardText>
          <VForm :loading="loading">
            <VRow>
              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="transmissionUrl">{{ t('pages.serviceSettings.transmission.server') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="transmissionSettings.transmission_host" :placeholder="t('pages.serviceSettings.transmission.serverPlaceholder')" />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="transmissionUsername">{{ t('pages.serviceSettings.transmission.username') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="transmissionSettings.transmission_username" :placeholder="t('pages.serviceSettings.transmission.usernamePlaceholder')" />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="transmissionPassword">{{ t('pages.serviceSettings.transmission.password') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField 
                      v-model="transmissionSettings.transmission_password" 
                      :placeholder="t('pages.serviceSettings.transmission.passwordPlaceholder')"
                    />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="transmissionPathMappingFrom">{{ t('pages.serviceSettings.transmission.pathMappingFrom') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField 
                      v-model="transmissionSettings.transmission_source_path" 
                      :placeholder="t('pages.serviceSettings.transmission.pathMappingFromPlaceholder')"
                    />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="transmissionPathMappingTo">{{ t('pages.serviceSettings.transmission.pathMappingTo') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField 
                      v-model="transmissionSettings.transmission_dest_path" 
                      :placeholder="t('pages.serviceSettings.transmission.pathMappingToPlaceholder')"
                    />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VSwitch v-model="transmissionSettings.enabled" :label="t('pages.serviceSettings.transmission.enable')" color="primary" inset />
              </VCol>

              <VCol cols="12">
                <VRow>
                  <VCol>
                    <VBtn color="primary" :loading="saving" @click="saveTransmissionSettings" class="mr-2">
                      {{ t('pages.serviceSettings.transmission.save') }}
                    </VBtn>
                    <VBtn color="secondary" :loading="testingTransmission" @click="testTransmissionConnection">
                      {{ t('pages.serviceSettings.transmission.test') }}
                    </VBtn>
                  </VCol>
                </VRow>
              </VCol>
              
              <VCol cols="12" v-if="transmissionSaveResult">
                <VAlert :type="transmissionSaveResult.success ? 'success' : 'error'" variant="tonal" density="compact" class="mb-3">
                  {{ transmissionSaveResult.message }}
                </VAlert>
              </VCol>
              
              <VCol cols="12" v-if="transmissionTestResult">
                <VAlert :type="transmissionTestResult.success ? 'success' : 'error'" variant="tonal" density="compact">
                  {{ transmissionTestResult.message || (transmissionTestResult.success ? t('pages.serviceSettings.transmission.connectionSuccess') : t('pages.serviceSettings.transmission.connectionError')) }}
                </VAlert>
              </VCol>
            </VRow>
          </VForm>
        </VCardText>
      </VCard>

      <VCard class="mb-6">
        <VCardTitle>{{ t('pages.serviceSettings.qbittorrent.title') }}</VCardTitle>
        <VCardSubtitle>
          {{ t('pages.serviceSettings.qbittorrent.subtitle') }}
        </VCardSubtitle>
        <VCardText>
          <VForm :loading="loading">
            <VRow>
              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="qbittorrentUrl">{{ t('pages.serviceSettings.qbittorrent.server') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="qbittorrentSettings.qbittorrent_host" :placeholder="t('pages.serviceSettings.qbittorrent.serverPlaceholder')" />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="qbittorrentUsername">{{ t('pages.serviceSettings.qbittorrent.username') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="qbittorrentSettings.qbittorrent_username" :placeholder="t('pages.serviceSettings.qbittorrent.usernamePlaceholder')" />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="qbittorrentPassword">{{ t('pages.serviceSettings.qbittorrent.password') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField
                      v-model="qbittorrentSettings.qbittorrent_password"
                      :placeholder="t('pages.serviceSettings.qbittorrent.passwordPlaceholder')"
                      type="password"
                    />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="qbittorrentPathMappingFrom">{{ t('pages.serviceSettings.qbittorrent.pathMappingFrom') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField
                      v-model="qbittorrentSettings.qbittorrent_source_path"
                      :placeholder="t('pages.serviceSettings.qbittorrent.pathMappingFromPlaceholder')"
                    />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="qbittorrentPathMappingTo">{{ t('pages.serviceSettings.qbittorrent.pathMappingTo') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField
                      v-model="qbittorrentSettings.qbittorrent_dest_path"
                      :placeholder="t('pages.serviceSettings.qbittorrent.pathMappingToPlaceholder')"
                    />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VSwitch v-model="qbittorrentSettings.enabled" :label="t('pages.serviceSettings.qbittorrent.enable')" color="primary" inset />
              </VCol>

              <VCol cols="12">
                <VRow>
                  <VCol>
                    <VBtn color="primary" :loading="saving" @click="saveQBittorrentSettings" class="mr-2">
                      {{ t('pages.serviceSettings.qbittorrent.save') }}
                    </VBtn>
                    <VBtn color="secondary" :loading="testingQBittorrent" @click="testQBittorrentConnection">
                      {{ t('pages.serviceSettings.qbittorrent.test') }}
                    </VBtn>
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12" v-if="qbittorrentSaveResult">
                <VAlert :type="qbittorrentSaveResult.success ? 'success' : 'error'" variant="tonal" density="compact" class="mb-3">
                  {{ qbittorrentSaveResult.message }}
                </VAlert>
              </VCol>

              <VCol cols="12" v-if="qbittorrentTestResult">
                <VAlert :type="qbittorrentTestResult.success ? 'success' : 'error'" variant="tonal" density="compact">
                  {{ qbittorrentTestResult.message || (qbittorrentTestResult.success ? t('pages.serviceSettings.qbittorrent.connectionSuccess') : t('pages.serviceSettings.qbittorrent.connectionError')) }}
                </VAlert>
              </VCol>
            </VRow>
          </VForm>
        </VCardText>
      </VCard>
    </VCol>
  </VRow>
</template>
