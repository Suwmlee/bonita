import { ScrapingSettingService } from "@/client"
import type {
  ScrapingSettingCreate,
  ScrapingSettingPublic,
} from "@/client/types.gen"
import { defineStore } from "pinia"
import { useConfirmationStore } from './confirmation.store'

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
    async deleteSetting(id: number) {
      const confirmationStore = useConfirmationStore()
      
      try {
        const confirmed = await confirmationStore.confirmDelete(
          'Delete Scraping Setting',
          'Are you sure you want to delete this scraping setting? This action cannot be undone.'
        )
        
        if (confirmed) {
          const response = await ScrapingSettingService.deleteSetting({
            id: id,
          })
          if (response.success) {
            this.allSettings = this.allSettings.filter((setting) => setting.id !== id)
          }
          return response
        }
      } catch (error) {
        console.error('Error deleting scraping setting:', error)
      }
    },
  },
})
