import { SettingsService } from "@/client/services.gen"
import type { ProxySettings, UpdateProxySettingsData } from "@/client/types.gen"
import { defineStore } from "pinia"
import { useToastStore } from "./toast.store"

interface SettingState {
  /** 代理设置 */
  proxySettings: ProxySettings
  /** 加载状态 */
  loading: boolean
  /** 保存状态 */
  saving: boolean
}

export const useSettingStore = defineStore("setting-store", {
  state: (): SettingState => {
    return {
      proxySettings: {
        http: null,
        https: null,
        enabled: false,
      },
      loading: false,
      saving: false,
    }
  },
  actions: {
    /**
     * 获取代理设置
     */
    async fetchProxySettings() {
      const toast = useToastStore()
      this.loading = true

      try {
        const response = await SettingsService.getProxySettings()
        this.proxySettings = response
        return response
      } catch (error) {
        console.error("Error fetching proxy settings:", error)
        toast.error("获取代理设置失败")
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 更新代理设置
     */
    async updateProxySettings() {
      const toast = useToastStore()
      this.saving = true

      try {
        const data: UpdateProxySettingsData = {
          requestBody: this.proxySettings,
        }

        const response = await SettingsService.updateProxySettings(data)
        toast.success("代理设置已更新")
        return response
      } catch (error) {
        console.error("Error updating proxy settings:", error)
        toast.error("更新代理设置失败")
        throw error
      } finally {
        this.saving = false
      }
    },
  },
})
