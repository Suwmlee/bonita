import { client } from "@/client/client.gen"
import type { SyncDirection, TaskStatus } from "@/client"
import { i18n } from "@/plugins/i18n"
import { defineStore } from "pinia"
import { useConfirmationStore } from "./confirmation.store"
import { useTaskStore } from "./task.store"
import { useToastStore } from "./toast.store"

export type PlexPlaylistCandidate = {
  source: string
  external_id: string
  rating_key: string
  name: string
  leaf_count: number
  smart: boolean
  added: boolean
}

export type PlaylistPublic = {
  id: number
  source: string
  external_id: string
  rating_key?: string | null
  write_rating_key?: string | null
  name: string
  is_smart: boolean
  item_count: number
  matched_count: number
  last_sync_at?: string | null
  createtime: string
  updatetime: string
}

export type PlaylistItemPublic = {
  id: number
  playlist_id: number
  media_item_id?: number | null
  external_item_id?: string | null
  external_guid?: string | null
  playlist_item_id?: string | null
  path?: string | null
  title?: string | null
  artist?: string | null
  album?: string | null
  sort_index: number
}

export type PlaylistDetail = PlaylistPublic & {
  items: PlaylistItemPublic[]
}

type PlaylistCollection = {
  data: PlaylistPublic[]
  count: number
}

export const usePlaylistStore = defineStore("playlist-store", {
  state: () => ({
    playlists: [] as PlaylistPublic[],
    detail: undefined as PlaylistDetail | undefined,
    plexCandidates: [] as PlexPlaylistCandidate[],
    isLoading: false,
    isSearching: false,
    isSyncing: false,
  }),
  actions: {
    async listPlaylists() {
      this.isLoading = true
      try {
        const { data: response } = await client.get<PlaylistCollection>({
          responseType: "json",
          security: [{ scheme: "bearer", type: "http" }],
          url: "/api/v1/playlists/",
        })
        this.playlists = response?.data ?? []
      } catch (error) {
        console.error("Error listing playlists:", error)
        useToastStore().error(i18n.global.t("pages.playlist.loadFailed") as string)
      } finally {
        this.isLoading = false
      }
    },

    async searchPlex(search: string) {
      this.isSearching = true
      try {
        const { data } = await client.get<PlexPlaylistCandidate[]>({
          responseType: "json",
          security: [{ scheme: "bearer", type: "http" }],
          url: "/api/v1/playlists/plex",
          query: { search },
        })
        this.plexCandidates = data ?? []
      } catch (error) {
        console.error("Error searching Plex playlists:", error)
        useToastStore().error(i18n.global.t("pages.playlist.searchFailed") as string)
        this.plexCandidates = []
      } finally {
        this.isSearching = false
      }
    },

    async addPlaylist(externalId: string, ratingKey: string, name?: string) {
      this.isLoading = true
      try {
        const { data: created } = await client.post<PlaylistPublic>({
          responseType: "json",
          security: [{ scheme: "bearer", type: "http" }],
          url: "/api/v1/playlists/",
          body: {
            source: "plex",
            external_id: externalId,
            rating_key: ratingKey,
            name,
          },
          headers: { "Content-Type": "application/json" },
        })
        await this.listPlaylists()
        useToastStore().success(i18n.global.t("pages.playlist.addSuccess") as string)
        return created
      } catch (error) {
        console.error("Error adding playlist:", error)
        useToastStore().error(i18n.global.t("pages.playlist.addFailed") as string)
        return undefined
      } finally {
        this.isLoading = false
      }
    },

    async rebindPlaylist(
      playlistId: number,
      externalId: string,
      ratingKey: string,
      name?: string,
      push = true,
    ) {
      this.isLoading = true
      try {
        const { data: updated } = await client.post<PlaylistPublic>({
          responseType: "json",
          security: [{ scheme: "bearer", type: "http" }],
          url: `/api/v1/playlists/${playlistId}/rebind`,
          query: { push: false },
          body: {
            source: "plex",
            external_id: externalId,
            rating_key: ratingKey,
            name,
          },
          headers: { "Content-Type": "application/json" },
        })
        await this.loadDetail(playlistId)
        if (!push) {
          useToastStore().success(i18n.global.t("pages.playlist.rebindSuccess") as string)
          return updated
        }
      } catch (error) {
        console.error("Error rebinding playlist:", error)
        useToastStore().error(i18n.global.t("pages.playlist.rebindFailed") as string)
        return undefined
      } finally {
        this.isLoading = false
      }
      this.isSyncing = true
      try {
        const { data: task } = await client.post<TaskStatus>({
          responseType: "json",
          security: [{ scheme: "bearer", type: "http" }],
          url: `/api/v1/playlists/${playlistId}/sync`,
          query: { direction: "to_server" },
        })
        if (!task?.task_id) {
          useToastStore().error(i18n.global.t("pages.playlist.syncFailed") as string)
          return this.detail
        }
        const finished = await useTaskStore().waitForTask(task.task_id)
        if (finished?.status === "FAILURE" || finished?.status === "REVOKED") {
          useToastStore().error(i18n.global.t("pages.playlist.syncFailed") as string)
          return this.detail
        }
        await this.listPlaylists()
        await this.loadDetail(playlistId)
        useToastStore().success(i18n.global.t("pages.playlist.rebindAndPushSuccess") as string)
        return this.detail
      } catch (error) {
        console.error("Error pushing rebound playlist:", error)
        useToastStore().error(i18n.global.t("pages.playlist.syncFailed") as string)
        return this.detail
      } finally {
        this.isSyncing = false
      }
    },

    async loadDetail(playlistId: number) {
      this.isLoading = true
      try {
        const { data } = await client.get<PlaylistDetail>({
          responseType: "json",
          security: [{ scheme: "bearer", type: "http" }],
          url: `/api/v1/playlists/${playlistId}`,
        })
        this.detail = data
      } catch (error) {
        console.error("Error loading playlist:", error)
        useToastStore().error(i18n.global.t("pages.playlist.loadFailed") as string)
        this.detail = undefined
      } finally {
        this.isLoading = false
      }
    },

    clearDetail() {
      this.detail = undefined
    },

    async syncOne(playlistId: number, direction: SyncDirection = "from_server") {
      await this._runSync(direction, playlistId)
    },

    async syncAll(direction: SyncDirection = "from_server") {
      await this._runSync(direction)
    },

    async _runSync(direction: SyncDirection, playlistId?: number) {
      this.isSyncing = true
      try {
        const { data: task } = playlistId == null
          ? await client.post<TaskStatus>({
              responseType: "json",
              security: [{ scheme: "bearer", type: "http" }],
              url: "/api/v1/playlists/sync",
              query: { direction },
            })
          : await client.post<TaskStatus>({
              responseType: "json",
              security: [{ scheme: "bearer", type: "http" }],
              url: `/api/v1/playlists/${playlistId}/sync`,
              query: { direction },
            })
        if (!task?.task_id) {
          useToastStore().error(i18n.global.t("pages.playlist.syncFailed") as string)
          return
        }
        const finished = await useTaskStore().waitForTask(task.task_id)
        if (finished?.status === "FAILURE" || finished?.status === "REVOKED") {
          useToastStore().error(i18n.global.t("pages.playlist.syncFailed") as string)
          return
        }
        await this.listPlaylists()
        if (this.detail && (playlistId == null || this.detail.id === playlistId)) {
          await this.loadDetail(this.detail.id)
        }
        const key =
          direction === "to_server"
            ? "pages.playlist.pushSuccess"
            : "pages.playlist.pullSuccess"
        useToastStore().success(i18n.global.t(key) as string)
      } catch (error) {
        console.error("Error syncing playlist:", error)
        useToastStore().error(i18n.global.t("pages.playlist.syncFailed") as string)
      } finally {
        this.isSyncing = false
      }
    },

    async removePlaylist(playlist: PlaylistPublic) {
      const confirmed = await useConfirmationStore().openConfirmation({
        title: i18n.global.t("pages.playlist.confirmRemoveTitle") as string,
        message: i18n.global.t("pages.playlist.confirmRemoveMessage", {
          name: playlist.name,
        }) as string,
        type: "delete",
      })
      if (!confirmed) return
      try {
        await client.delete({
          responseType: "json",
          security: [{ scheme: "bearer", type: "http" }],
          url: `/api/v1/playlists/${playlist.id}`,
        })
        if (this.detail?.id === playlist.id) this.clearDetail()
        await this.listPlaylists()
        useToastStore().success(i18n.global.t("pages.playlist.removeSuccess") as string)
      } catch (error) {
        console.error("Error removing playlist:", error)
        useToastStore().error(i18n.global.t("pages.playlist.removeFailed") as string)
      }
    },
  },
})
