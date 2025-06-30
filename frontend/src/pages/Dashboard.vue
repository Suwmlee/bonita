<script setup lang="ts">
import { useTaskStore } from "@/stores/task.store"
import { useI18n } from "vue-i18n"

const taskStore = useTaskStore()
const { t } = useI18n() // 导入国际化工具函数

// Get all task configurations and running tasks on component mount
async function initialLoad() {
  await taskStore.getAllTasks()
  await taskStore.getRunningTasks() // 立即获取一次任务状态
  taskStore.startPollingTasks(3000) // Poll every 3 seconds
}

// Computed property to get running tasks with their complete information
const runningTasksWithDetails = computed(() => {
  if (!taskStore.runningTasks.length) return []

  return taskStore.runningTasks
    .map((runningTask) => {
      let taskDetails = null
      
      // 尝试匹配TransferAll类型任务的配置详情
      if (runningTask.task_type === "TransferAll" && runningTask.detail) {
        const taskConfigId = parseInt(runningTask.detail)
        taskDetails = taskStore.allTasks.find((task) => task.id === taskConfigId)
      }
      
      return {
        ...runningTask,
        details: taskDetails,
      }
    })
    // 显示所有正在运行的任务，不过滤类型
})

// Computed property to get historical tasks with their complete information
const historicalTasksWithDetails = computed(() => {
  if (!taskStore.historicalTasks.length) return []

  return taskStore.historicalTasks
    .map((historicalTask) => {
      let taskDetails = null
      
      // 尝试匹配TransferAll类型任务的配置详情
      if (historicalTask.task_type === "TransferAll" && historicalTask.detail) {
        const taskConfigId = parseInt(historicalTask.detail)
        taskDetails = taskStore.allTasks.find((task) => task.id === taskConfigId)
      }
      
      return {
        ...historicalTask,
        details: taskDetails,
      }
    })
    // 显示所有历史任务，不过滤类型
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
                <tr v-for="task in runningTasksWithDetails" :key="task.task_id">
                  <td>{{ task.name || task.details?.name || task.task_type || t('pages.dashboard.unknownTask') }}</td>
                  <td>
                    <VChip 
                      :color="taskStore.getStatusColor(task.status)" 
                      size="small" 
                      class="mr-2"
                    >
                      {{ taskStore.getStatusText(task.status) }}
                    </VChip>
                  </td>
                  <td>{{ task.details?.source_folder || task.detail || '-' }}</td>
                  <td>{{ task.details?.output_folder || '-' }}</td>
                </tr>
              </tbody>
            </VTable>
          </VCardText>
        </VCard>
      </VCol>

      <VCol cols="12">
        <VCard :title="t('pages.dashboard.historicalTasks')">
          <VCardText>
            <div v-if="historicalTasksWithDetails.length === 0" class="text-center pa-4">
              <p class="text-subtitle-1">{{ t('pages.dashboard.noHistoricalTasks') }}</p>
            </div>
            <VTable v-else>
              <thead>
                <tr>
                  <th>{{ t('pages.dashboard.taskName') }}</th>
                  <th>{{ t('pages.dashboard.status') }}</th>
                  <th>{{ t('pages.dashboard.source') }}</th>
                  <th>{{ t('pages.dashboard.errorMessage') }}</th>
                  <th>{{ t('pages.dashboard.completedTime') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="task in historicalTasksWithDetails" :key="task.task_id">
                  <td>{{ task.name || task.details?.name || task.task_type || t('pages.dashboard.unknownTask') }}</td>
                  <td>
                    <VChip 
                      :color="taskStore.getStatusColor(task.status)" 
                      size="small" 
                      class="mr-2"
                    >
                      {{ taskStore.getStatusText(task.status) }}
                    </VChip>
                  </td>
                  <td>{{ task.details?.source_folder || task.detail || '-' }}</td>
                  <td>
                    <span v-if="task.error_message" class="text-error text-caption">
                      {{ task.error_message }}
                    </span>
                    <span v-else class="text-caption">-</span>
                  </td>
                  <td>
                    <span class="text-caption">
                      {{ new Date(task.updatetime || task.created_at || '').toLocaleString() }}
                    </span>
                  </td>
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
