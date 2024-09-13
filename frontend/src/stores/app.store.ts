import { defineStore } from "pinia"

export const useAppStore = defineStore("app-store", {
  state: () => ({
    currentTheme: "light",
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
  },
})
