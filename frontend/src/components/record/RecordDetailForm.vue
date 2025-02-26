<script lang="ts" setup>
import { ExtraInfoPublic, RecordPublic, TransferRecordPublic } from '@/client';
import { useRecordStore } from '@/stores/record.store';


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
    extra_info: currentExtraInfo.value
  }
  recordStore.updateRecord(data)
}
</script>

<template>
  <VForm @submit.prevent="handleSubmit">
    <VRow>
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="name">Name</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="name" v-model="currentExtraInfo.number" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="name">Tag</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="tag" v-model="currentExtraInfo.tag" />
          </VCol>
        </VRow>
      </VCol>

      <!-- 👉 submit and reset button -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3"/>
          <VCol cols="12" md="9">
            <VBtn type="submit" class="me-4">
              Submit
            </VBtn>
          </VCol>
        </VRow>
      </VCol>
    </VRow>
  </VForm>
</template>
