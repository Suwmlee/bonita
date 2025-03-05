<script lang="ts" setup>
import type { TransferConfigCreate, TransferConfigPublic } from "@/client/types.gen"
import { useScrapingStore } from "@/stores/scraping.store"
import { useTaskStore } from "@/stores/task.store"

interface Props {
  updateTask?: TransferConfigPublic
}
const props = defineProps<Props>()

const taskStore = useTaskStore()
const scrapingStore = useScrapingStore()

const { updateTask } = props as {
  updateTask: TransferConfigPublic
}
const currentTask = ref<any>()

if (updateTask) {
  currentTask.value = { ...updateTask }
} else {
  const createTask: TransferConfigCreate = {
    name: "name",
    description: "descrip",
    operation: 1,
    source_folder: "/volume/source",
  }
  currentTask.value = createTask
}

function formatScrapingItem(item: {
  name: string
  description: string
}) {
  if (item) {
    return `${item.name}- ${item.description}`
  }
  return ""
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
            <VTextField id="content_type" type="number" v-model.number="currentTask.content_type" />
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
            <label for="operation">Operation</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="operation" type="number" v-model.number="currentTask.operation" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="auto_watch">auto watch</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox id="auto_watch" v-model="currentTask.auto_watch" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="clean_others">clean others</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox id="clean_others" v-model="currentTask.clean_others" />
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

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="enabled">Enabled</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox id="enabled" v-model="currentTask.enabled" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="optimize_name">Optimize Name</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox id="optimize_name" v-model="currentTask.optimize_name" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="failed_folder">Failed Folder</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="failed_folder" v-model="currentTask.failed_folder" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="escape_folder">Escape Folder</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="escape_folder" v-model="currentTask.escape_folder" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="escape_literals">Escape Literals</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="escape_literals" v-model="currentTask.escape_literals" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="escape_size">Escape Size</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="escape_size" type="number" v-model.number="currentTask.escape_size" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="threads_num">Threads Number</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="threads_num" type="number" v-model.number="currentTask.threads_num" />
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
