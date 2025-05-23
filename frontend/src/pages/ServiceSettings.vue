<script setup lang="ts">
import { useSettingStore } from "@/stores/setting.store"
import { storeToRefs } from "pinia"
import { onMounted, ref } from "vue"
import { useI18n } from "vue-i18n"

// 使用 setting store
const settingStore = useSettingStore()
const { t } = useI18n() // 导入国际化工具函数

// 通过 storeToRefs 保持响应性
const {
  proxySettings,
  embyApiSettings,
  jellyfinApiSettings,
  transmissionSettings,
  loading,
  saving,
  testingEmby,
  testingJellyfin,
  testingTransmission,
} = storeToRefs(settingStore)
const testResult = ref<{ success?: boolean; message?: string } | null>(null)
const saveResult = ref<{ success: boolean; message: string } | null>(null)
const jellyfinTestResult = ref<{ success?: boolean; message?: string } | null>(
  null,
)
const jellyfinSaveResult = ref<{ success: boolean; message: string } | null>(
  null,
)
const transmissionTestResult = ref<{
  success?: boolean
  message?: string
} | null>(null)
const transmissionSaveResult = ref<{
  success: boolean
  message: string
} | null>(null)

const fetchProxySettings = async () => {
  await settingStore.fetchProxySettings()
}

const fetchEmbySettings = async () => {
  await settingStore.fetchEmbySettings()
}

const fetchJellyfinSettings = async () => {
  await settingStore.fetchJellyfinSettings()
}

const fetchTransmissionSettings = async () => {
  await settingStore.fetchTransmissionSettings()
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

const saveJellyfinApiSettings = async () => {
  // 重置之前的保存结果
  jellyfinSaveResult.value = null

  // 确保字段有正确的值类型
  jellyfinApiSettings.value.jellyfin_host =
    jellyfinApiSettings.value.jellyfin_host || ""
  jellyfinApiSettings.value.jellyfin_apikey =
    jellyfinApiSettings.value.jellyfin_apikey || ""

  try {
    const response = await settingStore.saveJellyfinApiSettings()
    jellyfinSaveResult.value = {
      success: true,
      message: t("pages.serviceSettings.jellyfin.saveSuccess"),
    }
    return response
  } catch (error) {
    console.error("Error saving Jellyfin settings:", error)
    jellyfinSaveResult.value = {
      success: false,
      message: t("pages.serviceSettings.jellyfin.saveError"),
    }
  }

  // 3秒后自动清除保存结果提示
  setTimeout(() => {
    jellyfinSaveResult.value = null
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

const testJellyfinConnection = async () => {
  jellyfinTestResult.value = null

  try {
    // 确保 API Key 有值
    const apiKey = jellyfinApiSettings.value.jellyfin_apikey || ""

    const response = await settingStore.testJellyfinConnection(apiKey)
    jellyfinTestResult.value = {
      success: response.success,
      message: response.message ?? "", // 使用空字符串作为 null 或 undefined 的默认值
    }
  } catch (error) {
    console.error("Error testing Jellyfin connection:", error)
    jellyfinTestResult.value = {
      success: false,
      message: t("pages.serviceSettings.jellyfin.testError"),
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

onMounted(() => {
  fetchProxySettings()
  fetchEmbySettings()
  fetchJellyfinSettings()
  fetchTransmissionSettings()
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
        <VCardTitle>{{ t('pages.serviceSettings.jellyfin.title') }}</VCardTitle>
        <VCardSubtitle>
          {{ t('pages.serviceSettings.jellyfin.subtitle') }}
        </VCardSubtitle>
        <VCardText>
          <VForm :loading="loading">
            <VRow>
              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="jellyfinUrl">{{ t('pages.serviceSettings.jellyfin.server') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="jellyfinApiSettings.jellyfin_host" :placeholder="t('pages.serviceSettings.jellyfin.serverPlaceholder')" />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="jellyfinApiKey">{{ t('pages.serviceSettings.jellyfin.apiKey') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="jellyfinApiSettings.jellyfin_apikey" :placeholder="t('pages.serviceSettings.jellyfin.apiKeyPlaceholder')" />
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VSwitch v-model="jellyfinApiSettings.enabled" :label="t('pages.serviceSettings.jellyfin.enable')" color="primary" inset />
              </VCol>

              <VCol cols="12">
                <VRow>
                  <VCol>
                    <VBtn color="primary" :loading="saving" @click="saveJellyfinApiSettings" class="mr-2">
                      {{ t('pages.serviceSettings.jellyfin.save') }}
                    </VBtn>
                    <VBtn color="secondary" :loading="testingJellyfin" @click="testJellyfinConnection">
                      {{ t('pages.serviceSettings.jellyfin.test') }}
                    </VBtn>
                  </VCol>
                </VRow>
              </VCol>
              
              <VCol cols="12" v-if="jellyfinSaveResult">
                <VAlert :type="jellyfinSaveResult.success ? 'success' : 'error'" variant="tonal" density="compact" class="mb-3">
                  {{ jellyfinSaveResult.message }}
                </VAlert>
              </VCol>
              
              <VCol cols="12" v-if="jellyfinTestResult">
                <VAlert :type="jellyfinTestResult.success ? 'success' : 'error'" variant="tonal" density="compact">
                  {{ jellyfinTestResult.message || (jellyfinTestResult.success ? t('pages.serviceSettings.jellyfin.connectionSuccess') : t('pages.serviceSettings.jellyfin.connectionError')) }}
                </VAlert>
              </VCol>
            </VRow>
          </VForm>
        </VCardText>
      </VCard>

      <VCard>
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
    </VCol>
  </VRow>
</template>
