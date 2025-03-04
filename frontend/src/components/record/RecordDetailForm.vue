<script lang="ts" setup>
import {
  ExtraInfoPublic,
  type RecordPublic,
  TransferRecordPublic,
} from "@/client"
import { useRecordStore } from "@/stores/record.store"

interface Props {
  updateRecord?: RecordPublic
}
const props = defineProps<Props>()

const recordStore = useRecordStore()

const { updateRecord } = props as {
  updateRecord: RecordPublic
}

const currentTransferRecord = ref<any>()
const currentExtraInfo = ref<any>()
currentTransferRecord.value = { ...updateRecord.transfer_record }
currentExtraInfo.value = { ...updateRecord.extra_info }

async function handleSubmit() {
  const data: RecordPublic = {
    transfer_record: currentTransferRecord.value,
    extra_info: currentExtraInfo.value,
  }
  recordStore.updateRecord(data)
}
</script>

<template>
  <VForm @submit.prevent="handleSubmit">
    <VRow>
      <!-- Transfer Record 部分 -->
      <VCol cols="12">
        <div class="text-h6 mb-4">Transfer Record</div>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>Source Name</label>
          </VCol>
          <VCol cols="12" md="9">
            <span>{{ currentTransferRecord.srcname }}</span>
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>Source Path</label>
          </VCol>
          <VCol cols="12" md="9">
            <span>{{ currentTransferRecord.srcpath }}</span>
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>Destination Path</label>
          </VCol>
          <VCol cols="12" md="9">
            <span>{{ currentTransferRecord.destpath }}</span>
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>Season</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentTransferRecord.season" type="number"
              :rules="[v => v >= -1 || 'Season must be -1 or greater']" />
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>Episode</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentTransferRecord.episode" type="number"
              :rules="[v => v >= -1 || 'Episode must be -1 or greater']" />
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>Status</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentTransferRecord.locked" label="Locked" class="mb-2" />
            <VCheckbox v-model="currentTransferRecord.ignored" label="Ignored" />
          </VCol>
        </VRow>
      </VCol>

      <!-- Extra Info 部分 -->
      <VCol cols="12">
        <div class="text-h6 mb-4">Extra Info</div>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>Number</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentExtraInfo.number" />
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>Tags</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentExtraInfo.tag" placeholder="用逗号分隔多个标签" hint="例如：中文字幕,破解" persistent-hint />
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>Part Number</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentExtraInfo.partNumber" type="number"
              :rules="[v => v >= 0 || 'Part number must be 0 or greater']" />
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>Specified Source</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentExtraInfo.specifiedsource" placeholder="指定的来源" />
          </VCol>
        </VRow>

        <VRow no-gutters class="mb-4">
          <VCol cols="12" md="3" class="row-label">
            <label>Specified URL</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentExtraInfo.specifiedurl" placeholder="指定的URL" />
          </VCol>
        </VRow>
      </VCol>

      <!-- Submit 按钮 -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" />
          <VCol cols="12" md="9">
            <VBtn type="submit" color="primary" class="me-4">
              保存
            </VBtn>
            <VBtn color="error" variant="outlined" @click="recordStore.showDialog = false">
              取消
            </VBtn>
          </VCol>
        </VRow>
      </VCol>
    </VRow>
  </VForm>
</template>

<style scoped>
.row-label {
  display: flex;
  align-items: center;
  font-weight: 500;
  padding-right: 1rem;
}

@media (max-width: 960px) {
  .row-label {
    margin-bottom: 0.5rem;
  }
}
</style>
