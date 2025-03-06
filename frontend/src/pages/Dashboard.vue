<script setup lang="ts">
import { useTaskStore } from "@/stores/task.store"

const taskStore = useTaskStore()

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
      Dashboard
    </p>

    <VRow>
      <VCol cols="12">
        <VCard title="Active Tasks">
          <VCardText>
            <div v-if="runningTasksWithDetails.length === 0" class="text-center pa-4">
              <p class="text-subtitle-1">No tasks currently running</p>
            </div>
            <VTable v-else>
              <thead>
                <tr>
                  <th>Task Name</th>
                  <th>Status</th>
                  <th>Source</th>
                  <th>Destination</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="task in runningTasksWithDetails" :key="task.id">
                  <td>{{ task.details?.name || 'Unknown Task' }}</td>
                  <td>
                    <VChip color="success" size="small" class="mr-2">
                      {{ task.status || 'Running' }}
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
