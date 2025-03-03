import { TaskService, TransferTaskService } from "@/client"
import type { TransferTaskCreate, TransferTaskPublic } from "@/client/types.gen"
import { defineStore } from "pinia"
import { useConfirmationStore } from "./confirmation.store"

export const useTaskStore = defineStore("task-store", {
  state: () => ({
    allTasks: [] as TransferTaskPublic[],
    showDialog: false,
    editTask: undefined as TransferTaskPublic | undefined,
  }),
  actions: {
    async getAllTasks() {
      const all = await TransferTaskService.getAllTasks()
      this.allTasks = all.data
      return this.allTasks
    },
    showAddTask() {
      this.editTask = undefined
      this.showDialog = true
    },
    showUpdateTask(data: TransferTaskPublic) {
      this.editTask = data
      this.showDialog = true
    },
    async createTask(data: TransferTaskCreate) {
      const task = await TransferTaskService.createTask({
        requestBody: data,
      })
      if (this.showDialog) {
        this.allTasks.push(task)
        this.showDialog = false
      }
    },
    async updateTask(data: TransferTaskPublic) {
      const task = await TransferTaskService.updateTask({
        id: data.id,
        requestBody: data,
      })
      if (this.showDialog) {
        this.updateTaskById(data.id, task)
        this.showDialog = false
      }
    },
    updateTaskById(id: number, newValue: Partial<TransferTaskPublic>) {
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
          const response = await TransferTaskService.deleteTask({
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
