<script setup lang="ts">
import { useToolStore } from "@/stores/tool.store"
import { useI18n } from "vue-i18n"

const toolStore = useToolStore()
const { t } = useI18n() // 导入国际化工具函数

const nfoFolder = ref("")
const isLoading = ref(false)
const updateOption = ref("ignore")

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
</script>

<template>
  <p class="text-xl mb-6">
    {{ t('pages.tools.title') }}
  </p>
  <VRow>
    <VCol cols="12" md="7" lg="5">
      <VCard class="mb-6">
        <VCardTitle>{{ t('pages.tools.importNfo.title') }}</VCardTitle>
        <VCardSubtitle>
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
    </VCol>
  </VRow>
</template>
