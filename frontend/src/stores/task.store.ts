import { TaskConfigService, TaskService } from "@/client"
import type {
  TaskStatus,
  TransferConfigCreate,
  TransferConfigPublic,
} from "@/client/types.gen"
import { defineStore } from "pinia"
import { useConfirmationStore } from "./confirmation.store"

export const useTaskStore = defineStore("task-store", {
  state: () => ({
    allTasks: [] as TransferConfigPublic[],
    runningTasks: [] as TaskStatus[],
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
        (runningTask) => runningTask.transfer_config === task.transfer_config,
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
    async getRunningTasks() {
      try {
        const response = await TaskService.getAllTasksStatus()
        if (response && Array.isArray(response)) {
          // Filter to only include tasks where transfer_config is not 0
          // Then remove duplicates by keeping only the first occurrence of each transfer_config
          const filteredTasks = response.filter(
            (task) => task.transfer_config !== 0,
          )

          // Use a Map to track unique transfer_config values and keep only the first occurrence
          const uniqueTasks = Array.from(
            filteredTasks
              .reduce((map, task) => {
                if (task.transfer_config && !map.has(task.transfer_config)) {
                  map.set(task.transfer_config, task)
                }
                return map
              }, new Map())
              .values(),
          )

          this.runningTasks = uniqueTasks
        }
        console.log("Current running tasks:", this.runningTasks)
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
      return this.runningTasks.some((task) => task.transfer_config === taskId)
    },
  },
})
