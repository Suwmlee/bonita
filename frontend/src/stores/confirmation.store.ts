import { defineStore } from "pinia"

export type ConfirmationOptions = {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  confirmColor?: string
  type?: "delete" | "warning" | "info"
  data?: any
}

export const useConfirmationStore = defineStore("confirmation-store", {
  state: () => ({
    show: false,
    options: {
      title: "Confirm Action",
      message: "Are you sure you want to proceed?",
      confirmText: "Confirm",
      cancelText: "Cancel",
      confirmColor: "primary",
      type: "warning",
    } as ConfirmationOptions,
    resolvePromise: null as ((value: boolean) => void) | null,
  }),

  actions: {
    openConfirmation(options: ConfirmationOptions) {
      this.show = true
      this.options = { ...this.options, ...options }

      // Set default styles based on type
      if (options.type === "delete" && !options.confirmColor) {
        this.options.confirmColor = "error"
        this.options.confirmText = options.confirmText || "Delete"
      }

      // Return a promise that will be resolved when the user confirms or cancels
      return new Promise<boolean>((resolve) => {
        this.resolvePromise = resolve
      })
    },

    confirm() {
      if (this.resolvePromise) {
        this.resolvePromise(true)
        this.resolvePromise = null
      }
      this.show = false
    },

    cancel() {
      if (this.resolvePromise) {
        this.resolvePromise(false)
        this.resolvePromise = null
      }
      this.show = false
    },

    // Specialized confirmation helpers
    async confirmDelete(title: string, message: string, data?: any) {
      return await this.openConfirmation({
        title,
        message,
        type: "delete",
        confirmText: "Delete",
        data,
      })
    },
  },
})
