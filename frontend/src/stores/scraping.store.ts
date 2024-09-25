import { ScrapingSettingService } from "@/client"
import type {
  ScrapingSettingCreate,
  ScrapingSettingPublic,
} from "@/client/types.gen"
import { defineStore } from "pinia"

export const useScrapingStore = defineStore("scraping-store", {
  state: () => ({
    allSettings: [] as ScrapingSettingPublic[],
    showDialog: false,
    editSetting: undefined as ScrapingSettingPublic | undefined,
  }),
  actions: {
    async getAllSetting() {
      const all = await ScrapingSettingService.getAllSettings()
      this.allSettings = all.data
      return this.allSettings
    },
    showAddSetting() {
      this.editSetting = undefined
      this.showDialog = true
    },
    showUpdateSetting(data: ScrapingSettingPublic) {
      this.editSetting = data
      this.showDialog = true
    },
    async addSetting(data: ScrapingSettingCreate) {
      const setting = await ScrapingSettingService.createSetting({
        requestBody: data,
      })
      if (this.showDialog) {
        this.allSettings.push(setting)
        this.showDialog = false
      }
    },
    async updateSetting(data: ScrapingSettingPublic) {
      const setting = await ScrapingSettingService.updateSetting({
        id: data.id,
        requestBody: data,
      })
      if (this.showDialog) {
        this.updateSettingById(data.id, setting)
        this.showDialog = false
      }
    },
    updateSettingById(id: number, newValue: Partial<ScrapingSettingPublic>) {
      const index = this.allSettings.findIndex((setting) => setting.id === id)

      if (index !== -1) {
        this.allSettings[index] = {
          ...this.allSettings[index],
          ...newValue,
        }
      } else {
        console.error(`Setting with id ${id} not found.`)
      }
    },
    async deleteSetting(idToRemove: number){
      const response = await ScrapingSettingService.deleteSetting({
        id: idToRemove,
      })
      if (response.success) {
        this.allSettings = this.allSettings.filter(setting => setting.id !== idToRemove);
      }
    }
  },
})
