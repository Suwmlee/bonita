import { TaskConfigService, TaskService } from "@/client"
import type {
  TaskStatus,
  TaskStatusEnum,
  TransferConfigCreate,
  TransferConfigPublic,
} from "@/client/types.gen"
import { defineStore } from "pinia"
import { useConfirmationStore } from "./confirmation.store"

export const useTaskStore = defineStore("task-store", {
  state: () => ({
    allTasks: [] as TransferConfigPublic[],
    runningTasks: [] as TaskStatus[],
    historicalTasks: [] as TaskStatus[],
    showDialog: false,
    editTask: undefined as TransferConfigPublic | undefined,
    pollingInterval: null as number | null,
    pollingFrequency: 2000,
  }),
  actions: {
    async getAllTasks() {
      const all = await TaskConfigService.getAllTaskConfigs()
      this.allTasks = all.data
      return this.allTasks
    },
    showAddTask() {
      this.editTask = undefined
      this.showDialog = true
    },
    showUpdateTask(data: TransferConfigPublic) {
      this.editTask = data
      this.showDialog = true
    },
    async createTask(data: TransferConfigCreate) {
      const task = await TaskConfigService.createTaskConfig({
        requestBody: data,
      })
      if (this.showDialog) {
        this.allTasks.push(task)
        this.showDialog = false
      }
    },
    async updateTask(data: TransferConfigPublic) {
      const task = await TaskConfigService.updateTaskConfig({
        id: data.id,
        requestBody: data,
      })
      if (this.showDialog) {
        this.updateTaskById(data.id, task)
        this.showDialog = false
      }
    },
    updateTaskById(id: number, newValue: Partial<TransferConfigPublic>) {
      const index = this.allTasks.findIndex((task) => task.id === id)

      if (index !== -1) {
        this.allTasks[index] = {
          ...this.allTasks[index],
          ...newValue,
        }
      } else {
        console.error(`Task with id ${id} not found.`)
      }
    },
    async deleteTaskById(id: number) {
      const confirmationStore = useConfirmationStore()

      try {
        const confirmed = await confirmationStore.confirmDelete(
          "Delete Task",
          "Are you sure you want to delete this task? This action cannot be undone.",
        )

        if (confirmed) {
          const response = await TaskConfigService.deleteTaskConfig({
            id: id,
          })
          if (response.success) {
            this.allTasks = this.allTasks.filter((task) => task.id !== id)
          }
          return response
        }
      } catch (error) {
        console.error("Error deleting task:", error)
      }
    },
    addOrUpdateRunningTask(task: TaskStatus) {
      if (!task) return

      // Check if the task is already in the runningTasks array
      const existingTaskIndex = this.runningTasks.findIndex(
        (runningTask) => runningTask.task_id === task.task_id,
      )

      if (existingTaskIndex !== -1) {
        // Update existing task if it's already in the array
        this.runningTasks[existingTaskIndex] = task
      } else {
        // Add new task to the array
        this.runningTasks.push(task)
      }

      console.log("Task added to running tasks:", task)
    },
    async runTaskById(id: number) {
      const task = await TaskService.runTransferTask({
        id: id,
        requestBody: {},
      })
      // Add the newly run task to the runningTasks array
      if (task) {
        this.addOrUpdateRunningTask(task)
      }
      return task
    },
    async runTaskByIdWithPath(id: number, path: string) {
      const task = await TaskService.runTransferTask({
        id: id,
        requestBody: {
          path: path,
        },
      })
      // Add the newly run task to the runningTasks array
      if (task) {
        this.addOrUpdateRunningTask(task)
      }
      return task
    },
    // 为TransferAll类型的任务添加name属性
    addTaskNames(tasks: TaskStatus[]): TaskStatus[] {
      return tasks.map(task => {
        if (task.task_type === "TransferAll" && task.detail) {
          const taskConfigId = parseInt(task.detail)
          const taskConfig = this.allTasks.find(config => config.id === taskConfigId)
          if (taskConfig) {
            return {
              ...task,
              name: taskConfig.name
            }
          }
        }
        return task
      })
    },
    async getRunningTasks() {
      try {
        const response = await TaskService.getAllTasksStatus()
        if (response && Array.isArray(response)) {
          // Filter running tasks (PENDING and PROGRESS status)
          const runningTasksOnly = response.filter((task) => 
            task.status === 'PENDING' || task.status === 'PROGRESS'
          )

          // Filter completed tasks (SUCCESS, FAILURE, REVOKED status)
          const completedTasksOnly = response.filter((task) => 
            task.status === 'SUCCESS' || task.status === 'FAILURE' || task.status === 'REVOKED'
          )

          // Create a map for deduplication of running tasks
          const uniqueRunningTasks = Array.from(
            runningTasksOnly
              .reduce((map, task) => {
                let uniqueKey: string
                
                if (task.task_type === "TransferAll" && task.detail) {
                  // For TransferAll, use the detail (task config ID) as unique key
                  uniqueKey = `TransferAll_${task.detail}`
                } else {
                  // For other types, use the task ID
                  uniqueKey = task.task_id
                }
                
                if (!map.has(uniqueKey)) {
                  map.set(uniqueKey, task)
                }
                return map
              }, new Map())
              .values(),
          )

          // Sort completed tasks by update time (newest first) and keep only top 10
          const sortedCompletedTasks = completedTasksOnly
            .sort((a, b) => {
              const timeA = new Date(a.updatetime || a.created_at || 0).getTime()
              const timeB = new Date(b.updatetime || b.created_at || 0).getTime()
              return timeB - timeA // Newest first
            })
            .slice(0, 10) // Keep only top 10

          // 使用通用函数为任务添加name属性
          this.runningTasks = this.addTaskNames(uniqueRunningTasks)
          this.historicalTasks = this.addTaskNames(sortedCompletedTasks)
        }
        return this.runningTasks
      } catch (error) {
        console.error("Error getting running tasks:", error)
        return []
      }
    },
    startPollingTasks(frequency?: number) {
      // Clear any existing interval
      this.stopPollingTasks()

      // Set polling frequency if provided
      if (frequency) {
        this.pollingFrequency = frequency
      }

      // Start polling
      this.pollingInterval = window.setInterval(async () => {
        await this.getRunningTasks()
      }, this.pollingFrequency)
    },
    stopPollingTasks() {
      if (this.pollingInterval !== null) {
        window.clearInterval(this.pollingInterval)
        this.pollingInterval = null
      }
    },
    isTaskRunning(taskId: number): boolean {
      return this.runningTasks.some((task) => {
        // Only TransferAll type tasks match with task config
        return task.task_type === "TransferAll" && 
               task.detail && 
               parseInt(task.detail) === taskId
      })
    },
    // Helper method to get status color
    getStatusColor(status: TaskStatusEnum | null | undefined): string {
      switch (status) {
        case 'PENDING':
          return 'warning'
        case 'PROGRESS':
          return 'info'
        case 'SUCCESS':
          return 'success'
        case 'FAILURE':
          return 'error'
        case 'REVOKED':
          return 'secondary'
        default:
          return 'primary'
      }
    },
    // Helper method to get status text
    getStatusText(status: TaskStatusEnum | null | undefined): string {
      switch (status) {
        case 'PENDING':
          return '等待中'
        case 'PROGRESS':
          return '进行中'
        case 'SUCCESS':
          return '成功'
        case 'FAILURE':
          return '失败'
        case 'REVOKED':
          return '已取消'
        default:
          return '未知'
      }
    },
  },
})
