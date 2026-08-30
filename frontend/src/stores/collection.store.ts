import { CollectionService, type CollectionDetail, type CollectionPublic, type CollectionSyncDirection, type EmbyCollectionCandidate } from "@/client/collection"
import type { MediaItemWithWatches } from "@/client"
import { i18n } from "@/plugins/i18n"
import { defineStore } from "pinia"
import { useConfirmationStore } from "./confirmation.store"
import { useToastStore } from "./toast.store"

export const useCollectionStore = defineStore("collection-store", {
  state: () => ({
    collections: [] as CollectionPublic[],
    detail: undefined as CollectionDetail | undefined,
    embyCandidates: [] as EmbyCollectionCandidate[],
    memberCandidates: [] as MediaItemWithWatches[],
    isLoading: false,
    isSearching: false,
    isSearchingMembers: false,
    isSyncing: false,
  }),
  actions: {
    async listCollections() {
      this.isLoading = true
      try {
        const response = await CollectionService.list()
        this.collections = response.data
      } catch (error) {
        console.error("Error listing collections:", error)
        useToastStore().error(i18n.global.t("pages.collection.loadFailed") as string)
      } finally {
        this.isLoading = false
      }
    },

    async searchEmby(search: string) {
      this.isSearching = true
      try {
        this.embyCandidates = await CollectionService.searchEmby(search)
      } catch (error) {
        console.error("Error searching Emby collections:", error)
        useToastStore().error(i18n.global.t("pages.collection.searchFailed") as string)
        this.embyCandidates = []
      } finally {
        this.isSearching = false
      }
    },

    async addCollection(embyId: string, name?: string) {
      this.isLoading = true
      try {
        const created = await CollectionService.add(embyId, name)
        await this.listCollections()
        useToastStore().success(i18n.global.t("pages.collection.addSuccess") as string)
        return created
      } catch (error) {
        console.error("Error adding collection:", error)
        useToastStore().error(i18n.global.t("pages.collection.addFailed") as string)
        return undefined
      } finally {
        this.isLoading = false
      }
    },

    async loadDetail(collectionId: number) {
      this.isLoading = true
      try {
        this.detail = await CollectionService.get(collectionId)
      } catch (error) {
        console.error("Error loading collection:", error)
        useToastStore().error(i18n.global.t("pages.collection.loadFailed") as string)
        this.detail = undefined
      } finally {
        this.isLoading = false
      }
    },

    clearDetail() {
      this.detail = undefined
      this.memberCandidates = []
    },

    _applySynced(updated: CollectionPublic) {
      const index = this.collections.findIndex((item) => item.id === updated.id)
      if (index >= 0) {
        this.collections[index] = updated
      }
    },

    async syncOne(collectionId: number, direction: CollectionSyncDirection = "from_server") {
      this.isSyncing = true
      try {
        const updated = await CollectionService.syncOne(collectionId, direction)
        this._applySynced(updated)
        if (this.detail?.id === collectionId) {
          await this.loadDetail(collectionId)
        }
        const key = direction === "to_server" ? "pages.collection.pushSuccess" : "pages.collection.pullSuccess"
        useToastStore().success(i18n.global.t(key) as string)
      } catch (error) {
        console.error("Error syncing collection:", error)
        useToastStore().error(i18n.global.t("pages.collection.syncFailed") as string)
      } finally {
        this.isSyncing = false
      }
    },

    async syncAll(direction: CollectionSyncDirection = "from_server") {
      this.isSyncing = true
      try {
        await CollectionService.syncAll(direction)
        await this.listCollections()
        if (this.detail) {
          await this.loadDetail(this.detail.id)
        }
        const key = direction === "to_server" ? "pages.collection.pushSuccess" : "pages.collection.pullSuccess"
        useToastStore().success(i18n.global.t(key) as string)
      } catch (error) {
        console.error("Error syncing collections:", error)
        useToastStore().error(i18n.global.t("pages.collection.syncFailed") as string)
      } finally {
        this.isSyncing = false
      }
    },

    async searchMembers(collectionId: number, search: string) {
      this.isSearchingMembers = true
      try {
        this.memberCandidates = await CollectionService.searchCandidates(collectionId, search)
      } catch (error) {
        console.error("Error searching collection members:", error)
        useToastStore().error(i18n.global.t("pages.collection.searchMembersFailed") as string)
        this.memberCandidates = []
      } finally {
        this.isSearchingMembers = false
      }
    },

    async addMembers(collectionId: number, mediaItemIds: number[], search = "") {
      try {
        const updated = await CollectionService.addItems(collectionId, mediaItemIds)
        this._applySynced(updated)
        await this.loadDetail(collectionId)
        await this.searchMembers(collectionId, search)
        useToastStore().success(i18n.global.t("pages.collection.addMemberSuccess") as string)
      } catch (error) {
        console.error("Error adding collection members:", error)
        useToastStore().error(i18n.global.t("pages.collection.addMemberFailed") as string)
      }
    },

    async removeMember(collection: CollectionPublic, item: MediaItemWithWatches) {
      const confirmationStore = useConfirmationStore()
      const confirmed = await confirmationStore.openConfirmation({
        title: i18n.global.t("pages.collection.confirmRemoveMemberTitle") as string,
        message: i18n.global.t("pages.collection.confirmRemoveMemberMessage", {
          title: item.title,
        }) as string,
        type: "delete",
      })
      if (!confirmed) return
      try {
        const updated = await CollectionService.removeItem(collection.id, item.id)
        this._applySynced(updated)
        if (this.detail?.id === collection.id) {
          await this.loadDetail(collection.id)
        }
        useToastStore().success(i18n.global.t("pages.collection.removeMemberSuccess") as string)
      } catch (error) {
        console.error("Error removing collection member:", error)
        useToastStore().error(i18n.global.t("pages.collection.removeMemberFailed") as string)
      }
    },

    async removeCollection(collection: CollectionPublic) {
      const confirmationStore = useConfirmationStore()
      const confirmed = await confirmationStore.openConfirmation({
        title: i18n.global.t("pages.collection.confirmRemoveTitle") as string,
        message: i18n.global.t("pages.collection.confirmRemoveMessage", { name: collection.name }) as string,
        type: "delete",
      })
      if (!confirmed) return
      try {
        await CollectionService.remove(collection.id)
        this.collections = this.collections.filter((item) => item.id !== collection.id)
        if (this.detail?.id === collection.id) {
          this.detail = undefined
        }
        useToastStore().success(i18n.global.t("pages.collection.removeSuccess") as string)
      } catch (error) {
        console.error("Error removing collection:", error)
        useToastStore().error(i18n.global.t("pages.collection.removeFailed") as string)
      }
    },
  },
})
