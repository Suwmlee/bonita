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

const defaultOptions: ConfirmationOptions = {
  title: "",
  message: "",
  confirmColor: "primary",
  type: "warning",
}

export const useConfirmationStore = defineStore("confirmation-store", {
  state: () => ({
    show: false,
    options: { ...defaultOptions } as ConfirmationOptions,
    resolvePromise: null as ((value: boolean) => void) | null,
  }),

  actions: {
    openConfirmation(options: ConfirmationOptions) {
      this.show = true
      this.options = {
        ...defaultOptions,
        ...options,
        confirmColor:
          options.confirmColor ??
          (options.type === "delete" ? "error" : "primary"),
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
        data,
      })
    },
  },
})
