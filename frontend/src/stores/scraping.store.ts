import { ScrapingSettingService } from "@/client"
import type { ScrapingSettingPublic } from "@/client/types.gen"
import { defineStore } from "pinia"

export const useScrapingStore = defineStore("scraping", {
  state: () => ({
    allSettings: [] as ScrapingSettingPublic[],
  }),
  actions: {
    async getAllSetting() {
      const all = await ScrapingSettingService.getAllSettings()
      this.allSettings = all.data
      return this.allSettings
    },
  },
})
