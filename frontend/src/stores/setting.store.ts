import { SettingsService } from "@/client/services.gen"
import type {
  EmbySettings,
  JellyfinSettings,
  ProxySettings,
  TestEmbyConnectionData,
  TestJellyfinConnectionData,
  UpdateEmbySettingsData,
  UpdateJellyfinSettingsData,
  UpdateProxySettingsData,
} from "@/client/types.gen"
import { defineStore } from "pinia"
import { useToastStore } from "./toast.store"

interface SettingState {
  /** 代理设置 */
  proxySettings: ProxySettings
  /** Emby API设置 */
  embyApiSettings: EmbySettings
  /** Jellyfin API设置 */
  jellyfinApiSettings: JellyfinSettings
  /** 加载状态 */
  loading: boolean
  /** 保存状态 */
  saving: boolean
  /** Emby测试状态 */
  testingEmby: boolean
  /** Jellyfin测试状态 */
  testingJellyfin: boolean
}

export const useSettingStore = defineStore("setting-store", {
  state: (): SettingState => {
    return {
      proxySettings: {
        http: null,
        https: null,
        enabled: false,
      },
      embyApiSettings: {
        emby_host: "",
        emby_apikey: "",
        enabled: false,
      },
      jellyfinApiSettings: {
        jellyfin_host: "",
        jellyfin_apikey: "",
        enabled: false,
      },
      loading: false,
      saving: false,
      testingEmby: false,
      testingJellyfin: false,
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

    /**
     * 获取Emby设置
     */
    async fetchEmbySettings() {
      const toast = useToastStore()
      this.loading = true

      try {
        const response = await SettingsService.getEmbySettings()
        this.embyApiSettings = response
        return response
      } catch (error) {
        console.error("Error fetching Emby settings:", error)
        toast.error("获取Emby设置失败")
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 更新Emby设置
     */
    async saveEmbyApiSettings() {
      this.saving = true

      try {
        const data: UpdateEmbySettingsData = {
          requestBody: this.embyApiSettings,
        }

        const response = await SettingsService.updateEmbySettings(data)
        return response
      } catch (error) {
        console.error("Error updating Emby settings:", error)
        throw error
      } finally {
        this.saving = false
      }
    },

    /**
     * 测试Emby连接
     * @param apiKey 用于测试的API Key
     */
    async testEmbyConnection(apiKey: string) {
      this.testingEmby = true

      try {
        const data: TestEmbyConnectionData = {
          requestBody: {
            emby_host: this.embyApiSettings.emby_host,
            emby_apikey: apiKey,
          },
        }

        const response = await SettingsService.testEmbyConnection(data)
        return response
      } catch (error) {
        console.error("Error testing Emby connection:", error)
        throw error
      } finally {
        this.testingEmby = false
      }
    },

    /**
     * 获取Jellyfin设置
     */
    async fetchJellyfinSettings() {
      const toast = useToastStore()
      this.loading = true

      try {
        const response = await SettingsService.getJellyfinSettings()
        this.jellyfinApiSettings = response
        return response
      } catch (error) {
        console.error("Error fetching Jellyfin settings:", error)
        toast.error("获取Jellyfin设置失败")
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 更新Jellyfin设置
     */
    async saveJellyfinApiSettings() {
      this.saving = true

      try {
        const data: UpdateJellyfinSettingsData = {
          requestBody: this.jellyfinApiSettings,
        }

        const response = await SettingsService.updateJellyfinSettings(data)
        return response
      } catch (error) {
        console.error("Error updating Jellyfin settings:", error)
        throw error
      } finally {
        this.saving = false
      }
    },

    /**
     * 测试Jellyfin连接
     * @param apiKey 用于测试的API Key
     */
    async testJellyfinConnection(apiKey: string) {
      this.testingJellyfin = true

      try {
        const data: TestJellyfinConnectionData = {
          requestBody: {
            jellyfin_host: this.jellyfinApiSettings.jellyfin_host,
            jellyfin_apikey: apiKey,
          },
        }

        const response = await SettingsService.testJellyfinConnection(data)
        return response
      } catch (error) {
        console.error("Error testing Jellyfin connection:", error)
        throw error
      } finally {
        this.testingJellyfin = false
      }
    },
  },
})
