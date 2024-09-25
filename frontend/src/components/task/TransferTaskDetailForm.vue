<script lang="ts" setup>
import type { TransferTaskCreate, TransferTaskPublic } from "@/client/types.gen"
import { useScrapingStore } from "@/stores/scraping.store"
import { useTaskStore } from "@/stores/task.store"

interface Props {
  updateTask?: TransferTaskPublic
}
const props = defineProps<Props>()

const taskStore = useTaskStore()
const scrapingStore = useScrapingStore()

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

function formatScrapingItem(item: {
  id: number
  name: string
  description: string
}) {
  return `${item.id}: ${item.name}- ${item.description}`
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
            <VTextField id="name" v-model="currentTask.name" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="description">description</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="description" v-model="currentTask.description" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="content_type">content type</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="content_type" type="number" v-model="currentTask.content_type" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="source_folder">source folder</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="source_folder" v-model="currentTask.source_folder" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="output_folder">output folder</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="output_folder" v-model="currentTask.output_folder" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="sc_enabled">enbale scraping</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox id="sc_enabled" v-model="currentTask.sc_enabled" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12" v-if="currentTask.sc_enabled">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="sc_id">scraping ID</label>
          </VCol>
          <VCol cols="12" md="9">
            <VSelect placeholder="Select scraping setting" v-model="currentTask.sc_id"
              :items="scrapingStore.allSettings" :item-title="formatScrapingItem" item-value="id"
              :menu-props="{ maxHeight: 200 }">
            </VSelect>
            <span class="text-capitalize">若此处没有您想要的配置, 请在 "刮削配置" 内新增</span>
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
