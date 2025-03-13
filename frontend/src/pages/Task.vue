<script setup lang="ts">
import { useScrapingStore } from "@/stores/scraping.store"
import { useTaskStore } from "@/stores/task.store"
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { useI18n } from "vue-i18n"
import { VCardActions } from "vuetify/components"

const taskStore = useTaskStore()
const scrapingStore = useScrapingStore()
const { t } = useI18n() // 导入国际化工具函数

// Store directory inputs for each task
const directoryInputs = ref(new Map<number, string>())

// Get directory input for a task
function getDirectoryInput(taskId: number): string {
  return directoryInputs.value.get(taskId) || ""
}

// Set directory input for a task
function setDirectoryInput(taskId: number, value: string): void {
  directoryInputs.value.set(taskId, value)
}

// Create a computed map of running task statuses for reactivity
const runningTasksMap = computed(() => {
  const map = new Map()
  for (const task of taskStore.runningTasks) {
    if (task.transfer_config !== 0) {
      map.set(task.transfer_config, true)
    }
  }
  return map
})

// Reactive method to check if a task is running
const isTaskRunning = computed(() => {
  return (taskId: number) => runningTasksMap.value.has(taskId)
})

async function initial() {
  await taskStore.getAllTasks()
  await scrapingStore.getAllSetting()
  taskStore.startPollingTasks(3000)
}

function addNewTask() {
  console.log("add new")
  taskStore.showAddTask()
}

function runTask(id: number) {
  // Get the directory input for this task
  const directory = getDirectoryInput(id)

  // Use the appropriate method based on whether a directory is specified
  if (directory.trim()) {
    taskStore.runTaskByIdWithPath(id, directory)
  } else {
    taskStore.runTaskById(id)
  }
}

const showSelectedTask = (item: any) => {
  taskStore.showUpdateTask(item)
}

function deleteTask(id: number) {
  taskStore.deleteTaskById(id)
}

// Prevent event propagation for input field
function handleInputClick(event: Event) {
  event.stopPropagation()
}

onMounted(() => {
  initial()
})

onBeforeUnmount(() => {
  taskStore.stopPollingTasks()
})
</script>

<template>
  <div>

    <p class="text-xl mb-6">
      {{ t('pages.task.title') }}
    </p>

    <VRow>
      <VCol v-for="data in taskStore.allTasks" :key="data.id" cols="12" md="6" lg="4" @click="showSelectedTask(data)">
        <VCard>
          <VCardItem>
            <VCardTitle>
              {{ data.name }} <span class="text-caption text-grey">#{{ data.id }}</span>
            </VCardTitle>
          </VCardItem>

          <VCardText>
            <p class="clamp-text mb-0">
              {{ data.description }}
            </p>
          </VCardText>

          <VCardText class="d-flex justify-space-between align-center flex-wrap">
            <div class="text-no-wrap">
              <span class="ms-2">{{ data.source_folder }}</span>
            </div>
          </VCardText>

          <!-- Add directory input field -->
          <VCardText>
            <VTextField
              :model-value="getDirectoryInput(data.id)"
              @update:model-value="setDirectoryInput(data.id, $event)"
              @click="handleInputClick"
              :placeholder="t('pages.task.directoryHint')"
              persistent-hint
              density="compact"
              variant="outlined"
            ></VTextField>
          </VCardText>

          <VCardActions class="justify-space-between">
            <VBtn v-if="!isTaskRunning(data.id)" type="submit" class="me-4" @click.stop="runTask(data.id)">
              {{ t('pages.task.runNow') }}
            </VBtn>
            <VBtn v-else color="primary" class="me-4" :loading="true" variant="tonal">
              <template #loader>
                <span>{{ t('pages.task.running') }}</span>
              </template>
            </VBtn>
            <VBtn type="submit" class="me-4" @click.stop="deleteTask(data.id)">
              <VIcon style="color: firebrick;" icon="bx-trash" size="22" />
            </VBtn>
          </VCardActions>
        </VCard>
      </VCol>

      <VCol cols="12" md="6" lg="4" @click="addNewTask">
        <VCard style="height: 100%;">
          <VCardText class="d-flex flex-column align-center justify-center" style="height: 100%;">
            <VIcon icon="bx-plus" size="140" color="primary" />
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>

  <TransferConfigDetailDialog />
</template>
