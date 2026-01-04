<script setup lang="ts">
import { useMediaItemStore } from "@/stores/mediaitem.store"
import { useToolStore } from "@/stores/tool.store"
import { useI18n } from "vue-i18n"

const toolStore = useToolStore()
const mediaItemStore = useMediaItemStore()
const { t } = useI18n() // 导入国际化工具函数

const nfoFolder = ref("")
const isLoading = ref(false)
const isSyncingEmby = ref(false)
const isCleaningMediaItems = ref(false)
const isCleaningData = ref(false)
const updateOption = ref("ignore")
const forceCleanupOption = ref(false)
const syncDirection = ref<"from_emby" | "to_emby">("from_emby")
const forceUpdateEmby = ref(false)

const importNfoData = async () => {
  if (!nfoFolder.value) {
    alert(t("pages.tools.importNfo.folderRequired"))
    return
  }
  isLoading.value = true
  try {
    await toolStore.runImportNfo({
      arg1: nfoFolder.value,
      arg2: updateOption.value,
    })
  } finally {
    isLoading.value = false
  }
}

const syncEmbyWatchHistory = async () => {
  isSyncingEmby.value = true
  try {
    await toolStore.syncEmbyWatchHistory(syncDirection.value, forceUpdateEmby.value)
  } finally {
    isSyncingEmby.value = false
  }
}

const cleanMediaItems = async () => {
  isCleaningMediaItems.value = true
  try {
    await mediaItemStore.cleanMediaItems()
  } finally {
    isCleaningMediaItems.value = false
  }
}

const cleanupData = async () => {
  isCleaningData.value = true
  try {
    await toolStore.cleanupData(forceCleanupOption.value)
  } finally {
    isCleaningData.value = false
  }
}
</script>

<template>
  <p class="text-xl mb-6">
    {{ t('pages.tools.title') }}
  </p>
  <VRow>
    <VCol cols="12" sm="8" md="6" lg="5" xl="4">
      <VCard class="mb-6">
        <VCardTitle>{{ t('pages.tools.importNfo.title') }}</VCardTitle>
        <VCardSubtitle class="text-wrap">
          {{ t('pages.tools.importNfo.subtitle') }}
        </VCardSubtitle>
        <VCardText>
          <VForm :loading="isLoading">
            <VRow>
              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="nfoFolder">{{ t('pages.tools.importNfo.folder') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="nfoFolder" :placeholder="t('pages.tools.importNfo.folderPlaceholder')" variant="outlined" />
                  </VCol>
                </VRow>
              </VCol>
              
              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="updateOption">{{ t('pages.tools.importNfo.importMethod') }}</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VRadioGroup v-model="updateOption" inline hide-details>
                      <VRadio value="ignore" :label="t('pages.tools.importNfo.ignoreExisting')" />
                      <VRadio value="force" :label="t('pages.tools.importNfo.forceUpdate')" />
                    </VRadioGroup>
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VBtn color="primary" block :loading="isLoading" @click="importNfoData">
                  {{ t('pages.tools.importNfo.startImport') }}
                </VBtn>
              </VCol>
            </VRow>
          </VForm>
        </VCardText>
      </VCard>
      
      <VCard class="mb-6">
        <VCardTitle>{{ t('pages.tools.syncEmby.title') }}</VCardTitle>
        <VCardSubtitle class="text-wrap">
          {{ t('pages.tools.syncEmby.subtitle') }}
        </VCardSubtitle>
        <VCardText>
          <VRow>
            <VCol cols="12">
              <VRow no-gutters>
                <VCol cols="12" md="3" class="row-label">
                  <label for="syncDirection">{{ t('pages.tools.syncEmby.direction') }}</label>
                </VCol>
                <VCol cols="12" md="9">
                  <VRadioGroup v-model="syncDirection" inline hide-details>
                    <VRadio value="from_emby" :label="t('pages.tools.syncEmby.fromEmby')" />
                    <VRadio value="to_emby" :label="t('pages.tools.syncEmby.toEmby')" />
                  </VRadioGroup>
                </VCol>
              </VRow>
            </VCol>

            <VCol cols="12">
              <VRow no-gutters>
                <VCol cols="12" md="3" class="row-label">
                  <label for="forceUpdateEmby">{{ t('pages.tools.syncEmby.forceUpdate') }}</label>
                </VCol>
                <VCol cols="12" md="9">
                  <VCheckbox v-model="forceUpdateEmby" hide-details />
                </VCol>
              </VRow>
            </VCol>
            <VCol cols="12" class="mb-3">
              <VBtn color="primary" block :loading="isSyncingEmby" @click="syncEmbyWatchHistory">
                {{ t('pages.tools.syncEmby.startSync') }}
              </VBtn>
            </VCol>
            <VCol cols="12">
              <VBtn color="secondary" block :loading="isCleaningMediaItems" @click="cleanMediaItems">
                {{ t('pages.mediaitem.clean') }}
              </VBtn>
            </VCol>
          </VRow>
        </VCardText>
      </VCard>

      <VCard class="mb-6">
        <VCardTitle>{{ t('pages.tools.cleanup.title') }}</VCardTitle>
        <VCardSubtitle class="text-wrap">
          {{ t('pages.tools.cleanup.subtitle') }}
        </VCardSubtitle>
        <VCardText>
          <VRow>
            <VCol cols="12">
              <VRow no-gutters>
                <VCol cols="12" md="3" class="row-label">
                  <label for="forceCleanupOption">{{ t('pages.tools.cleanup.forceOption') }}</label>
                </VCol>
                <VCol cols="12" md="9">
                  <VCheckbox v-model="forceCleanupOption" hide-details />
                </VCol>
              </VRow>
            </VCol>
            <VCol cols="12">
              <VBtn color="error" block :loading="isCleaningData" @click="cleanupData">
                {{ t('pages.tools.cleanup.startCleanup') }}
              </VBtn>
            </VCol>
          </VRow>
        </VCardText>
      </VCard>
    </VCol>
  </VRow>
</template>
