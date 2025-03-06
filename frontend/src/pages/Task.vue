<script setup lang="ts">
import { useScrapingStore } from "@/stores/scraping.store"
import { useTaskStore } from "@/stores/task.store"
import { VCardActions } from "vuetify/components"

const taskStore = useTaskStore()
const scrapingStore = useScrapingStore()

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
  taskStore.runTaskById(id)
}

const showSelectedTask = (item: any) => {
  taskStore.showUpdateTask(item)
}

function deleteTask(id: number) {
  taskStore.deleteTaskById(id)
}

onMounted(() => {
  initial()
})
</script>

<template>
  <div>

    <p class="text-xl mb-6">
      Task
    </p>

    <VRow>
      <VCol v-for="data in taskStore.allTasks" :key="data.id" cols="12" md="6" lg="4" @click="showSelectedTask(data)">
        <VCard>
          <VCardItem>
            <VCardTitle>
              {{ data.name }}
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
          <VCardActions class="justify-space-between">
            <VBtn v-if="!isTaskRunning(data.id)" type="submit" class="me-4" @click.stop="runTask(data.id)">
              立即执行
            </VBtn>
            <VBtn v-else color="primary" class="me-4" :loading="true" variant="tonal">
              <template #loader>
                <span>运行中</span>
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
          <VCardItem>
            <VCardTitle>
              Add Task
            </VCardTitle>
          </VCardItem>

          <VCardText>
            <p class="clamp-text mb-0">
              Add Task
            </p>
          </VCardText>

          <VCardText class="d-flex justify-space-between align-center flex-wrap">
            <div class="text-no-wrap">
              <span class="ms-2">+</span>
            </div>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>

  <TransferConfigDetailDialog />
</template>
