<script lang="ts" setup>
import type {
  TransferConfigCreate,
  TransferConfigPublic,
} from "@/client/types.gen"
import { useScrapingStore } from "@/stores/scraping.store"
import { useTaskStore } from "@/stores/task.store"
import { useI18n } from "vue-i18n"

interface Props {
  updateTask?: TransferConfigPublic
}
const props = defineProps<Props>()

const taskStore = useTaskStore()
const scrapingStore = useScrapingStore()
const { t } = useI18n() // 导入国际化工具函数

const { updateTask } = props as {
  updateTask: TransferConfigPublic
}
const currentTask = ref<any>()

// Define content type options
const contentTypeOptions = [
  { title: t('components.task.form.movie'), value: 1 },
  { title: t('components.task.form.series'), value: 2 },
]

// Define operation method options
const operationOptions = [
  { title: t('components.task.form.hardLink'), value: 1 },
  { title: t('components.task.form.softLink'), value: 2 },
  { title: t('components.task.form.move'), value: 3 },
  { title: t('components.task.form.copy'), value: 4 },
]

if (updateTask) {
  currentTask.value = { ...updateTask }
} else {
  const createTask: TransferConfigCreate = {
    name: "name",
    description: "descrip",
    content_type: 1,
    operation: 1,
    source_folder: "/media/source",
    output_folder: "/media/output",
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
            <label for="name">{{ t('components.task.form.name') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="name" v-model="currentTask.name" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="description">{{ t('components.task.form.description') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="description" v-model="currentTask.description" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="content_type">{{ t('components.task.form.contentType') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VRadioGroup
              id="content_type"
              v-model="currentTask.content_type"
              inline
            >
              <VRadio
                v-for="option in contentTypeOptions"
                :key="option.value"
                :label="option.title"
                :value="option.value"
              />
            </VRadioGroup>
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="source_folder">{{ t('components.task.form.sourceFolder') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="source_folder" v-model="currentTask.source_folder" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="output_folder">{{ t('components.task.form.outputFolder') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="output_folder" v-model="currentTask.output_folder" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="operation">{{ t('components.task.form.operation') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VRadioGroup
              id="operation"
              v-model="currentTask.operation"
              inline
            >
              <VRadio
                v-for="option in operationOptions"
                :key="option.value"
                :label="option.title"
                :value="option.value"
              />
            </VRadioGroup>
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="auto_watch">{{ t('components.task.form.autoWatch') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox id="auto_watch" v-model="currentTask.auto_watch" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="clean_others">{{ t('components.task.form.cleanOthers') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox id="clean_others" v-model="currentTask.clean_others" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="sc_enabled">{{ t('components.task.form.enableScraping') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox id="sc_enabled" v-model="currentTask.sc_enabled" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12" v-if="currentTask.sc_enabled">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="sc_id">{{ t('components.task.form.scrapingId') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VSelect :placeholder="t('components.task.form.selectScraping')" v-model="currentTask.sc_id"
              :items="scrapingStore.allSettings" :item-title="formatScrapingItem" item-value="id"
              :menu-props="{ maxHeight: 200 }">
            </VSelect>
            <span class="text-capitalize">{{ t('components.task.form.scrapingHint') }}</span>
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="enabled">{{ t('components.task.form.enabled') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox id="enabled" v-model="currentTask.enabled" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="optimize_name">{{ t('components.task.form.optimizeName') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VCheckbox id="optimize_name" v-model="currentTask.optimize_name" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="failed_folder">{{ t('components.task.form.failedFolder') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="failed_folder" v-model="currentTask.failed_folder" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="escape_folder">{{ t('components.task.form.escapeFolder') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="escape_folder" v-model="currentTask.escape_folder" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="escape_literals">{{ t('components.task.form.escapeLiterals') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="escape_literals" v-model="currentTask.escape_literals" />
          </VCol>
        </VRow>
      </VCol>

      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="escape_size">{{ t('components.task.form.escapeSize') }}</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="escape_size" type="number" v-model.number="currentTask.escape_size" />
          </VCol>
        </VRow>
      </VCol>

      <!-- <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" class="row-label">
            <label for="threads_num">Threads Number</label>
          </VCol>
          <VCol cols="12" md="9">
            <VTextField id="threads_num" type="number" v-model.number="currentTask.threads_num" />
          </VCol>
        </VRow>
      </VCol> -->

      <!-- 👉 submit and reset button -->
      <VCol cols="12">
        <VRow no-gutters>
          <VCol cols="12" md="3" />
          <VCol cols="12" md="9">
            <VBtn type="submit" class="me-4">
              {{ t('components.task.form.submit') }}
            </VBtn>
          </VCol>
        </VRow>
      </VCol>
    </VRow>
  </VForm>
</template>
