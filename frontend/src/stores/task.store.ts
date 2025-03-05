import { TaskService, TaskConfigService } from "@/client"
import type { TransferConfigCreate, TransferConfigPublic } from "@/client/types.gen"
import { defineStore } from "pinia"
import { useConfirmationStore } from "./confirmation.store"

export const useTaskStore = defineStore("task-store", {
  state: () => ({
    allTasks: [] as TransferConfigPublic[],
    showDialog: false,
    editTask: undefined as TransferConfigPublic | undefined,
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
    runTaskById(id: number) {
      const task = TaskService.runTransferTask({
        id: id,
      })
    },
  },
})
