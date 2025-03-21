import { StatusService } from "@/client/services.gen"
import { defineStore } from "pinia"

export const useAppStore = defineStore("app-store", {
  state: () => ({
    currentTheme: "light",
    version: "",
  }),
  actions: {
    getTheme() {
      this.currentTheme = localStorage.getItem("theme") ?? "light"
      return this.currentTheme
    },
    updateTheme(theme: string) {
      this.currentTheme = theme
      localStorage.setItem("theme", theme)
    },
    async fetchVersion() {
      try {
        const response = await StatusService.healthCheck()
        if (response?.version) {
          this.version = response.version
        }
      } catch (error) {
        console.error("获取版本信息失败", error)
      }
    },
  },
})
