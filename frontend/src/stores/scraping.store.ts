import { ScrapingConfigService } from "@/client"
import type {
  ScrapingConfigCreate,
  ScrapingConfigPublic,
} from "@/client/types.gen"
import { i18n } from "@/plugins/i18n"
import { defineStore } from "pinia"
import { useConfirmationStore } from "./confirmation.store"

export const useScrapingStore = defineStore("scraping-store", {
  state: () => ({
    allSettings: [] as ScrapingConfigPublic[],
    showDialog: false,
    editSetting: undefined as ScrapingConfigPublic | undefined,
  }),
  actions: {
    async getAllSetting() {
      const all = await ScrapingConfigService.getAllConfigs()
      this.allSettings = all.data
      return this.allSettings
    },
    showAddSetting() {
      this.editSetting = undefined
      this.showDialog = true
    },
    showUpdateSetting(data: ScrapingConfigPublic) {
      this.editSetting = data
      this.showDialog = true
    },
    async addSetting(data: ScrapingConfigCreate) {
      const setting = await ScrapingConfigService.createConfig({
        requestBody: data,
      })
      if (this.showDialog) {
        this.allSettings.push(setting)
        this.showDialog = false
      }
    },
    async updateSetting(data: ScrapingConfigPublic) {
      const setting = await ScrapingConfigService.updateConfig({
        id: data.id,
        requestBody: data,
      })
      if (this.showDialog) {
        this.updateSettingById(data.id, setting)
        this.showDialog = false
      }
    },
    updateSettingById(id: number, newValue: Partial<ScrapingConfigPublic>) {
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
          i18n.global.t("pages.scraping.confirmDeleteTitle") as string,
          i18n.global.t("pages.scraping.confirmDeleteMessage") as string,
        )

        if (confirmed) {
          const response = await ScrapingConfigService.deleteConfig({
            id: id,
          })
          if (response.success) {
            this.allSettings = this.allSettings.filter(
              (setting) => setting.id !== id,
            )
          }
          return response
        }
      } catch (error) {
        console.error("Error deleting scraping setting:", error)
      }
    },
  },
})
