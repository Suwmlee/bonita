import {
  CollectionService,
  type CollectionDetail,
  type CollectionPublic,
  type EmbyCollectionCandidate,
  type MediaItemWithWatches,
  type SyncDirection,
} from "@/client"
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
        const { data: response } = await CollectionService.listCollections()
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
        const { data } = await CollectionService.searchEmbyCollections({ search })
        this.embyCandidates = data
      } catch (error) {
        console.error("Error searching Emby collections:", error)
        useToastStore().error(i18n.global.t("pages.collection.searchFailed") as string)
        this.embyCandidates = []
      } finally {
        this.isSearching = false
      }
    },

    async addCollection(externalId: string, name?: string) {
      this.isLoading = true
      try {
        const { data: created } = await CollectionService.addCollection({
          collectionCreate: { external_id: externalId, name },
        })
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
        const { data } = await CollectionService.getCollection({
          collection_id: collectionId,
        })
        this.detail = data
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

    async syncOne(collectionId: number, direction: SyncDirection = "from_server") {
      this.isSyncing = true
      try {
        const { data: updated } = await CollectionService.syncOneCollection({
          collection_id: collectionId,
          direction,
        })
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

    async syncAll(direction: SyncDirection = "from_server") {
      this.isSyncing = true
      try {
        await CollectionService.syncAllCollections({ direction })
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
        const { data } = await CollectionService.searchCollectionCandidates({
          collection_id: collectionId,
          search,
        })
        this.memberCandidates = data
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
        const { data: updated } = await CollectionService.addItemsToCollection({
          collection_id: collectionId,
          collectionAddItems: { media_item_ids: mediaItemIds },
        })
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
        const { data: updated } = await CollectionService.removeItemFromCollection({
          collection_id: collection.id,
          media_item_id: item.id,
        })
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
        await CollectionService.removeCollection({ collection_id: collection.id })
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
