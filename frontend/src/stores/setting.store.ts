import { SettingsService } from "@/client"
import type {
  EmbySettings,
  ProxySettings,
  QBittorrentSettings,
  TransmissionSettings,
} from "@/client"
import { defineStore } from "pinia"
import { useToastStore } from "./toast.store"

interface SettingState {
  /** 代理设置 */
  proxySettings: ProxySettings
  /** Emby API设置 */
  embyApiSettings: EmbySettings
  /** Transmission设置 */
  transmissionSettings: TransmissionSettings
  /** qBittorrent设置 */
  qbittorrentSettings: QBittorrentSettings
  /** 加载状态 */
  loading: boolean
  /** 保存状态 */
  saving: boolean
  /** Emby测试状态 */
  testingEmby: boolean
  /** Transmission测试状态 */
  testingTransmission: boolean
  /** qBittorrent测试状态 */
  testingQBittorrent: boolean
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
        emby_user: "",
        enabled: false,
      },
      transmissionSettings: {
        transmission_host: "",
        transmission_username: "",
        transmission_password: "",
        transmission_source_path: "",
        transmission_dest_path: "",
        enabled: false,
      },
      qbittorrentSettings: {
        qbittorrent_host: "",
        qbittorrent_username: "",
        qbittorrent_password: "",
        qbittorrent_source_path: "",
        qbittorrent_dest_path: "",
        enabled: false,
      },
      loading: false,
      saving: false,
      testingEmby: false,
      testingTransmission: false,
      testingQBittorrent: false,
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
        const { data: response } = await SettingsService.getProxySettings()
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
        const { data: response } = await SettingsService.updateProxySettings({
          proxySettings: this.proxySettings,
        })
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
        const { data: response } = await SettingsService.getEmbySettings()
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
        const { data: response } = await SettingsService.updateEmbySettings({
          embySettings: this.embyApiSettings,
        })
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
        const { data: response } = await SettingsService.testEmbyConnection({
          embySettings: {
            emby_host: this.embyApiSettings.emby_host,
            emby_apikey: apiKey,
            emby_user: this.embyApiSettings.emby_user,
          },
        })
        return response
      } catch (error) {
        console.error("Error testing Emby connection:", error)
        throw error
      } finally {
        this.testingEmby = false
      }
    },

    /**
     * 获取Transmission设置
     */
    async fetchTransmissionSettings() {
      const toast = useToastStore()
      this.loading = true

      try {
        const { data: response } = await SettingsService.getTransmissionSettings()
        this.transmissionSettings = response
        return response
      } catch (error) {
        console.error("Error fetching Transmission settings:", error)
        toast.error("获取Transmission设置失败")
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 更新Transmission设置
     */
    async saveTransmissionSettings() {
      this.saving = true

      try {
        const { data: response } = await SettingsService.updateTransmissionSettings({
          transmissionSettings: this.transmissionSettings,
        })
        return response
      } catch (error) {
        console.error("Error updating Transmission settings:", error)
        throw error
      } finally {
        this.saving = false
      }
    },

    /**
     * 测试Transmission连接
     */
    async testTransmissionConnection() {
      this.testingTransmission = true

      try {
        const { data: response } = await SettingsService.testTransmissionConnection({
          transmissionSettings: {
            transmission_host: this.transmissionSettings.transmission_host,
            transmission_username:
              this.transmissionSettings.transmission_username,
            transmission_password:
              this.transmissionSettings.transmission_password,
            transmission_source_path:
              this.transmissionSettings.transmission_source_path,
            transmission_dest_path:
              this.transmissionSettings.transmission_dest_path,
          },
        })
        return response
      } catch (error) {
        console.error("Error testing Transmission connection:", error)
        throw error
      } finally {
        this.testingTransmission = false
      }
    },

    /**
     * 获取qBittorrent设置
     */
    async fetchQBittorrentSettings() {
      const toast = useToastStore()
      this.loading = true

      try {
        const { data: response } = await SettingsService.getQbittorrentSettings()
        this.qbittorrentSettings = response
        return response
      } catch (error) {
        console.error("Error fetching qBittorrent settings:", error)
        toast.error("获取qBittorrent设置失败")
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 更新qBittorrent设置
     */
    async saveQBittorrentSettings() {
      this.saving = true

      try {
        const { data: response } = await SettingsService.updateQbittorrentSettings({
          qBittorrentSettings: this.qbittorrentSettings,
        })
        return response
      } catch (error) {
        console.error("Error updating qBittorrent settings:", error)
        throw error
      } finally {
        this.saving = false
      }
    },

    /**
     * 测试qBittorrent连接
     */
    async testQBittorrentConnection() {
      this.testingQBittorrent = true

      try {
        const { data: response } = await SettingsService.testQbittorrentConnection({
          qBittorrentSettings: {
            qbittorrent_host: this.qbittorrentSettings.qbittorrent_host,
            qbittorrent_username: this.qbittorrentSettings.qbittorrent_username,
            qbittorrent_password: this.qbittorrentSettings.qbittorrent_password,
            qbittorrent_source_path: this.qbittorrentSettings.qbittorrent_source_path,
            qbittorrent_dest_path: this.qbittorrentSettings.qbittorrent_dest_path,
          },
        })
        return response
      } catch (error) {
        console.error("Error testing qBittorrent connection:", error)
        throw error
      } finally {
        this.testingQBittorrent = false
      }
    },
  },
})
