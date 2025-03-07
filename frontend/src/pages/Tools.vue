<script setup lang="ts">
import { useToolStore } from "@/stores/tool.store"

const toolStore = useToolStore()

const nfoFolder = ref("")
const isLoading = ref(false)
const updateOption = ref("ignore")

const importNfoData = async () => {
  if (!nfoFolder.value) {
    alert("请输入文件夹路径")
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
    Tools
  </p>
  <VRow>
    <VCol cols="12" md="7" lg="5">
      <VCard class="mb-6">
        <VCardTitle>从NFO导入元数据</VCardTitle>
        <VCardSubtitle>
          在此导入NFO文件中的电影元数据信息
        </VCardSubtitle>
        <VCardText>
          <VForm :loading="isLoading">
            <VRow>
              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="nfoFolder">NFO文件夹</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VTextField v-model="nfoFolder" placeholder="例如: D:\Movies\NFO" variant="outlined" />
                  </VCol>
                </VRow>
              </VCol>
              
              <VCol cols="12">
                <VRow no-gutters>
                  <VCol cols="12" md="3" class="row-label">
                    <label for="updateOption">导入方式</label>
                  </VCol>
                  <VCol cols="12" md="9">
                    <VRadioGroup v-model="updateOption" inline hide-details>
                      <VRadio value="ignore" label="忽略已有数据" />
                      <VRadio value="force" label="强制更新" />
                    </VRadioGroup>
                  </VCol>
                </VRow>
              </VCol>

              <VCol cols="12">
                <VBtn color="primary" block :loading="isLoading" @click="importNfoData">
                  开始导入
                </VBtn>
              </VCol>
            </VRow>
          </VForm>
        </VCardText>
      </VCard>
    </VCol>
  </VRow>
</template>
