<script setup lang="ts">
import { useTaskStore } from "@/stores/task.store"
import { useI18n } from "vue-i18n"

const taskStore = useTaskStore()
const { t } = useI18n() // 导入国际化工具函数

// Get all task configurations and running tasks on component mount
async function initialLoad() {
  await taskStore.getAllTasks()
  taskStore.startPollingTasks(3000) // Poll every 3 seconds
}

// Computed property to get running tasks with their complete information
const runningTasksWithDetails = computed(() => {
  if (!taskStore.runningTasks.length || !taskStore.allTasks.length) return []

  return taskStore.runningTasks
    .map((runningTask) => {
      // Find the complete task details from allTasks
      const taskDetails = taskStore.allTasks.find(
        (task) =>
          runningTask.transfer_config &&
          task.id === runningTask.transfer_config,
      )
      return {
        ...runningTask,
        details: taskDetails || null,
      }
    })
    .filter((task) => task.details !== null) // Only include tasks with details
})

onMounted(() => {
  initialLoad()
})

onBeforeUnmount(() => {
  taskStore.stopPollingTasks() // Clean up polling when component is unmounted
})
</script>

<template>
  <div>
    <p class="text-xl mb-6">
      {{ t('pages.dashboard.title') }}
    </p>

    <VRow>
      <VCol cols="12">
        <VCard :title="t('pages.dashboard.activeTasks')">
          <VCardText>
            <div v-if="runningTasksWithDetails.length === 0" class="text-center pa-4">
              <p class="text-subtitle-1">{{ t('pages.dashboard.noRunningTasks') }}</p>
            </div>
            <VTable v-else>
              <thead>
                <tr>
                  <th>{{ t('pages.dashboard.taskName') }}</th>
                  <th>{{ t('pages.dashboard.status') }}</th>
                  <th>{{ t('pages.dashboard.source') }}</th>
                  <th>{{ t('pages.dashboard.destination') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="task in runningTasksWithDetails" :key="task.id">
                  <td>{{ task.details?.name || t('pages.dashboard.unknownTask') }}</td>
                  <td>
                    <VChip color="success" size="small" class="mr-2">
                      {{ task.status || t('pages.dashboard.running') }}
                    </VChip>
                  </td>
                  <td>{{ task.details?.source_folder || '-' }}</td>
                  <td>{{ task.details?.output_folder || '-' }}</td>
                </tr>
              </tbody>
            </VTable>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>
  </div>
</template>

<style scoped>
.v-table {
  border-radius: 4px;
}
</style>
