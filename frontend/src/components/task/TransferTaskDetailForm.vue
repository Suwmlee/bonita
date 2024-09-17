<script lang="ts" setup>
import type {
  TransferTaskCreate,
  TransferTaskPublic,
} from "@/client/types.gen"
import { useTaskStore } from "@/stores/task.store"

interface Props {
  updateTask?: TransferTaskPublic
}
const props = defineProps<Props>()

const taskStore = useTaskStore()

const { updateTask } = props as {
  updateTask: TransferTaskPublic
}
const currentTask = ref<any>()

if (updateTask) {
  currentTask.value = { ...updateTask }
} else {
  const createTask: TransferTaskCreate = {
    name: "name",
    description: "descrip",
    transfer_type: 0,
    source_folder: "/volume/source",
  }
  currentTask.value = createTask
}

async function handleSubmit() {
  console.log(currentTask)
  if (updateTask) {
    taskStore.updateTask(currentTask.value)
  } else {
    taskStore.createTask(currentTask.value)
  }
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
            <VTextField v-model="currentTask.name" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="mobile">description</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentTask.description" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="mobile">source_folder</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField v-model="currentTask.source_folder" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="mobile">enbale scraping</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox v-model="currentTask.sc_enabled" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12" v-if="currentTask.sc_enabled">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="mobile">scraping ID</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField type="number" v-model="currentTask.sc_id" />
          </VCol>
        </VRow>
      </VCol>

      <!-- 👉 submit and reset button -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" />
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
