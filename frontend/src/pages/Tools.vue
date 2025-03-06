<script setup lang="ts">
import { ref } from 'vue';

const nfoFolder = ref('');
const isLoading = ref(false);
const updateOption = ref('ignore');

const importNfoData = async () => {
  if (!nfoFolder.value) {
    alert('请输入文件夹路径');
    return;
  }

  isLoading.value = true;
  try {
    // TODO: Implement actual NFO import logic here
    console.log('Importing NFO data from:', nfoFolder.value);
    console.log('Update option:', updateOption.value);

    setTimeout(() => {
      alert('导入成功！');
      isLoading.value = false;
    }, 1000);
  } catch (error) {
    console.error('Import failed:', error);
    alert('导入失败，请检查控制台日志');
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <p class="text-xl mb-6">
    Tools
  </p>
  <VRow>
    <VCol cols="12" md="6" lg="4">
      <VCard style="height: 320px;">
        <VCardItem>
          <VCardTitle>
            从NFO导入元数据
          </VCardTitle>
        </VCardItem>

        <VCardText>
          <VTextField v-model="nfoFolder" placeholder="例如: D:\Movies\NFO" variant="outlined" class="mb-4" />

          <div class="mb-4">
            <p class="text-body-2 mb-1">导入方式:</p>
            <VRadioGroup v-model="updateOption" inline hide-details>
              <VRadio value="ignore" label="忽略已有数据" />
              <VRadio value="force" label="强制更新" />
            </VRadioGroup>
          </div>

          <VBtn color="primary" block :loading="isLoading" @click="importNfoData">
            开始导入
          </VBtn>
        </VCardText>
      </VCard>
    </VCol>
  </VRow>
</template>
